import logging
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from database import get_db
from Models.question import Question
from Models.interview_answer import InterviewAnswer
from Models.interview import Interview
from schemas.interview_answer import EvaluateAnswerRequest, EvaluateAnswerResponse
from services.ai_service import evaluate_answer
from Models.user import User
from utils.dependency import get_current_user
logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/interview-answers",
    tags=["Interview Answers"]
)
@router.post("/evaluate",response_model=EvaluateAnswerResponse,status_code=status.HTTP_201_CREATED,)
def evaluate_user_answer(
    data: EvaluateAnswerRequest,
    db: Session = Depends(get_db),
):
    
    question = (
        db.query(Question)
        .filter(Question.id == data.question_id)
        .first()
    )
    if not question:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Question with id={data.question_id} not found.",
        )

    
    try:
        result = evaluate_answer(
        question.question_text,
        data.answer
    )

    except Exception as exc:
        result = {
        "score": 5,
        "feedback": "Gemini quota exceeded. Demo response.",
        "strengths": "Unable",
        "improvements": "Unable"
    }

    except ValueError as exc:
        logger.error("AI evaluation failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"AI evaluation returned an unexpected response: {exc}",
        )
    except Exception as exc:
        logger.exception("Unexpected error calling Gemini API.")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="AI service is temporarily unavailable. Please try again.",
        )

    
    try:
        saved_answer = InterviewAnswer(
            session_id=data.session_id,
            question_id=data.question_id,
            answer=data.answer,
            score=result["score"],
            feedback=result["feedback"],
            strengths=result["strengths"],
            improvements=result["improvements"],
        )
        db.add(saved_answer)
        db.commit()
        db.refresh(saved_answer)
        logger.info(
            "Saved InterviewAnswer id=%s for session=%s",
            saved_answer.id,
            data.session_id,
        )
    except Exception as exc:
        db.rollback()
        logger.exception("Failed to save InterviewAnswer to database.")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to save evaluation result.",
        )

    return result

@router.get("/session/{session_id}")
def get_session_answers(
    session_id: int,
    db: Session = Depends(get_db),
):
    answers = (
        db.query(InterviewAnswer)
        .filter(InterviewAnswer.session_id == session_id)
        .all()
    )
    if not answers:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No answers found for session_id={session_id}.",
        )
    return answers

@router.get("/session/{session_id}/summary")
def interview_summary(
    session_id: int,
    db: Session = Depends(get_db),
):
    answers = (
        db.query(InterviewAnswer)
        .filter(InterviewAnswer.session_id == session_id)
        .all()
    )
    if not answers:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No answers found for session_id={session_id}.",
        )

    total_questions = len(answers)
    average_score = round(
        sum(a.score for a in answers) / total_questions, 2
    )

    return {
        "session_id": session_id,
        "total_questions": total_questions,
        "average_score": average_score,
    }

@router.post("/session/{session_id}/complete")
def complete_interview(
    session_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    answers = (
        db.query(InterviewAnswer)
        .filter(InterviewAnswer.session_id == session_id)
        .all()
    )
    if not answers:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No answers found for session_id={session_id}.",
        )

    avg_score = round(
        sum(a.score for a in answers) / len(answers), 2
    )

    try:
        interview = Interview(
            user_id=current_user.id,       
            role="Practice",
            score=avg_score,
            questions_count=len(answers),
            duration=0,
            feedback="Interview Completed",
        )
        db.add(interview)
        db.commit()
        db.refresh(interview)
    except Exception as exc:
        db.rollback()
        logger.exception("Failed to save completed Interview record.")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to complete interview.",
        )

    return {
        "message": "Interview completed",
        "interview_id": interview.id,
        "score": avg_score,
    }