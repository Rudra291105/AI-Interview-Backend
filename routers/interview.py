import logging
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from database import get_db
from Models.interview import Interview, InterviewMessage
from Models.user import User
from schemas.interview import (
    StartInterviewRequest,
    StartInterviewResponse,
    SubmitAnswerRequest,
    SubmitAnswerResponse,
    EndInterviewRequest,
    FinalReportResponse,
)
from services.ai_service import (
    generate_greeting,
    generate_first_question,
    generate_next_question,
    evaluate_answer,
    generate_final_report,
)
from services.resume_service import extract_resume_text, summarise_resume  # ← NEW
from utils.dependency import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/virtual-interview",
    tags=["Virtual Interview"],
)

MAX_QUESTIONS = 8


def _build_profile(user: User) -> dict:
    """
    Builds the AI profile dict for a user, including resume text if available.
    Centralised here so every endpoint uses the same profile structure.
    """
    raw_resume = extract_resume_text(user.resume_filename or "")
    resume_summary = summarise_resume(raw_resume)

    return {
        "name": user.name or "there",
        "company": None,          # overridden per-interview
        "role": None,             # overridden per-interview
        "skill": user.primary_skill or "Software Engineering",
        "resume": resume_summary,
        "has_resume": bool(raw_resume),
    }


# ─────────────────────────────────────────────────────
# POST /virtual-interview/start
# ─────────────────────────────────────────────────────
@router.post("/start", response_model=StartInterviewResponse, status_code=status.HTTP_201_CREATED)
def start_interview(
    data: StartInterviewRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    # Build full profile including resume
    profile = _build_profile(current_user)
    profile["company"] = data.company or "a leading tech company"
    profile["role"] = data.role

    # 1. Generate greeting
    try:
        greeting = generate_greeting(profile)
    except Exception as exc:
        logger.error("Greeting generation failed: %s", exc)
        first_name = (current_user.name or "there").split()[0]
        greeting = (
            f"Welcome, {first_name}! I'll be your interviewer today for the {data.role} position. "
            f"Let's get started — I'm looking forward to learning more about you!"
        )

    # 2. Generate first question
    try:
        first_q = generate_first_question(profile)
    except Exception as exc:
        logger.error("First question generation failed: %s", exc)
        first_q = {
            "question": "Tell me about yourself and your background.",
            "question_type": "Introduction",
            "difficulty": "Easy",
        }

    # 3. Create Interview record
    interview = Interview(
        user_id=current_user.id,
        company=data.company,
        role=data.role,
        status="in_progress",
    )
    db.add(interview)
    db.commit()
    db.refresh(interview)

    # 4. Save first question as pending message
    msg = InterviewMessage(
        interview_id=interview.id,
        question=first_q["question"],
        question_type=first_q.get("question_type", "Introduction"),
        difficulty=first_q.get("difficulty", "Easy"),
        is_followup=False,
    )
    db.add(msg)
    db.commit()

    return StartInterviewResponse(
        interview_id=interview.id,
        greeting=greeting,
        question=first_q["question"],
        question_type=first_q.get("question_type", "Introduction"),
        difficulty=first_q.get("difficulty", "Easy"),
        is_followup=False,
    )


# ─────────────────────────────────────────────────────
# POST /virtual-interview/submit-answer
# ─────────────────────────────────────────────────────
@router.post("/submit-answer", response_model=SubmitAnswerResponse)
def submit_answer(
    data: SubmitAnswerRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    interview = (
        db.query(Interview)
        .filter(Interview.id == data.interview_id, Interview.user_id == current_user.id)
        .first()
    )
    if not interview:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Interview not found.")
    if interview.status == "completed":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Interview already completed.")

    current_msg = (
        db.query(InterviewMessage)
        .filter(InterviewMessage.interview_id == interview.id, InterviewMessage.answer == None)  # noqa: E711
        .order_by(InterviewMessage.id.asc())
        .first()
    )
    if not current_msg:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No pending question found.")

    # Evaluate answer
    try:
        evaluation = evaluate_answer(current_msg.question, data.answer)
    except Exception as exc:
        logger.error("Evaluation failed: %s", exc)
        evaluation = {
            "score": 5,
            "feedback": "Your answer was recorded. AI evaluation temporarily unavailable.",
            "strengths": "Answer submitted.",
            "improvements": "Review this topic again.",
        }

    current_msg.answer = data.answer
    current_msg.score = float(evaluation.get("score", 5))
    current_msg.feedback = evaluation.get("feedback", "")
    current_msg.strengths = evaluation.get("strengths", "")
    current_msg.improvements = evaluation.get("improvements", "")
    db.commit()

    answered_count = (
        db.query(InterviewMessage)
        .filter(InterviewMessage.interview_id == interview.id, InterviewMessage.answer != None)  # noqa: E711
        .count()
    )

    if answered_count >= MAX_QUESTIONS:
        return SubmitAnswerResponse(
            score=current_msg.score,
            feedback=current_msg.feedback,
            strengths=current_msg.strengths,
            improvements=current_msg.improvements,
            next_question=None,
            question_type=None,
            difficulty=None,
            is_followup=False,
            questions_asked=answered_count,
            interview_complete=True,
        )

    # Build history
    all_msgs = (
        db.query(InterviewMessage)
        .filter(InterviewMessage.interview_id == interview.id, InterviewMessage.answer != None)  # noqa: E711
        .order_by(InterviewMessage.id.asc())
        .all()
    )
    history = [
        {
            "question": m.question,
            "answer": m.answer,
            "score": m.score,
            "feedback": m.feedback,
            "question_type": m.question_type,
            "is_followup": m.is_followup,
        }
        for m in all_msgs
    ]

    # Build full profile with resume for next question generation
    profile = _build_profile(current_user)
    profile["company"] = interview.company or "a leading tech company"
    profile["role"] = interview.role

    try:
        next_q = generate_next_question(profile, history)
    except Exception as exc:
        logger.error("Next question generation failed: %s", exc)
        next_q = {
            "question": "Describe a challenging project you've worked on and the obstacles you overcame.",
            "question_type": "Behavioral",
            "difficulty": "Medium",
            "is_followup": False,
        }

    next_msg = InterviewMessage(
        interview_id=interview.id,
        question=next_q["question"],
        question_type=next_q.get("question_type", "Technical"),
        difficulty=next_q.get("difficulty", "Medium"),
        is_followup=bool(next_q.get("is_followup", False)),
    )
    db.add(next_msg)
    db.commit()

    return SubmitAnswerResponse(
        score=current_msg.score,
        feedback=current_msg.feedback,
        strengths=current_msg.strengths,
        improvements=current_msg.improvements,
        next_question=next_q["question"],
        question_type=next_q.get("question_type", "Technical"),
        difficulty=next_q.get("difficulty", "Medium"),
        is_followup=bool(next_q.get("is_followup", False)),
        questions_asked=answered_count,
        interview_complete=False,
    )


# ─────────────────────────────────────────────────────
# POST /virtual-interview/end
# ─────────────────────────────────────────────────────
@router.post("/end", response_model=FinalReportResponse)
def end_interview(
    data: EndInterviewRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    interview = (
        db.query(Interview)
        .filter(Interview.id == data.interview_id, Interview.user_id == current_user.id)
        .first()
    )
    if not interview:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Interview not found.")

    messages = (
        db.query(InterviewMessage)
        .filter(InterviewMessage.interview_id == interview.id, InterviewMessage.answer != None)  # noqa: E711
        .order_by(InterviewMessage.id.asc())
        .all()
    )

    if not messages:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No answered questions found. Answer at least one question before ending.",
        )

    history = [
        {
            "question": m.question,
            "answer": m.answer,
            "score": m.score,
            "feedback": m.feedback,
            "question_type": m.question_type,
        }
        for m in messages
    ]

    # Full profile with resume for final report
    profile = _build_profile(current_user)
    profile["company"] = interview.company or "a leading tech company"
    profile["role"] = interview.role

    try:
        report = generate_final_report(profile, history)
    except Exception as exc:
        logger.error("Final report generation failed: %s", exc)
        scores = [m.score or 0 for m in messages]
        avg = round(sum(scores) / len(scores) * 10) if scores else 50
        report = {
            "overall_score": avg,
            "technical_knowledge": avg,
            "communication": avg,
            "confidence": avg,
            "problem_solving": avg,
            "strengths": ["Completed the interview session"],
            "weaknesses": ["Report generation temporarily unavailable"],
            "suggested_improvements": ["Review core concepts for your role"],
            "topics_to_study": ["Data Structures", "System Design", "Behavioral Questions"],
            "final_feedback": "You completed the interview. Review individual question feedback for more detail.",
        }

    duration = 0
    if messages:
        duration = int((datetime.utcnow() - messages[0].created_at).total_seconds())

    interview.status = "completed"
    interview.score = float(report.get("overall_score", 0))
    interview.questions_count = len(messages)
    interview.duration = duration
    interview.feedback = report.get("final_feedback", "")
    interview.detailed_report = report
    interview.completed_at = datetime.utcnow()
    db.commit()

    return FinalReportResponse(
        interview_id=interview.id,
        overall_score=report.get("overall_score", 0),
        technical_knowledge=report.get("technical_knowledge", 0),
        communication=report.get("communication", 0),
        confidence=report.get("confidence", 0),
        problem_solving=report.get("problem_solving", 0),
        strengths=report.get("strengths", []),
        weaknesses=report.get("weaknesses", []),
        suggested_improvements=report.get("suggested_improvements", []),
        topics_to_study=report.get("topics_to_study", []),
        final_feedback=report.get("final_feedback", ""),
        total_questions=len(messages),
        company=interview.company,
        role=interview.role,
    )


# ─────────────────────────────────────────────────────
# GET /virtual-interview/{interview_id}/report
# ─────────────────────────────────────────────────────
@router.get("/{interview_id}/report", response_model=FinalReportResponse)
def get_interview_report(
    interview_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    interview = (
        db.query(Interview)
        .filter(Interview.id == interview_id, Interview.user_id == current_user.id, Interview.status == "completed")
        .first()
    )
    if not interview:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Completed interview not found.")

    report = interview.detailed_report or {}
    return FinalReportResponse(
        interview_id=interview.id,
        overall_score=report.get("overall_score", interview.score),
        technical_knowledge=report.get("technical_knowledge", 0),
        communication=report.get("communication", 0),
        confidence=report.get("confidence", 0),
        problem_solving=report.get("problem_solving", 0),
        strengths=report.get("strengths", []),
        weaknesses=report.get("weaknesses", []),
        suggested_improvements=report.get("suggested_improvements", []),
        topics_to_study=report.get("topics_to_study", []),
        final_feedback=report.get("final_feedback", interview.feedback or ""),
        total_questions=interview.questions_count,
        company=interview.company,
        role=interview.role,
    )


# ─────────────────────────────────────────────────────
# GET /virtual-interview/history
# ─────────────────────────────────────────────────────
@router.get("/history")
def get_interview_history(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    interviews = (
        db.query(Interview)
        .filter(Interview.user_id == current_user.id, Interview.status == "completed")
        .order_by(Interview.completed_at.desc())
        .all()
    )
    return [
        {
            "interview_id": iv.id,
            "company": iv.company,
            "role": iv.role,
            "score": iv.score,
            "questions_count": iv.questions_count,
            "duration": iv.duration,
            "feedback": iv.feedback,
            "completed_at": iv.completed_at,
        }
        for iv in interviews
    ]