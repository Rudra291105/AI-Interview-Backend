from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy.sql.expression import func
from database import get_db
from Models.question import Question
from schemas.question import QuestionResponse
from Models.company import Company
from Models.difficulty import DifficultyLevel
from Models.question_type import QuestionType
from Models.bookmark import Bookmark
from utils.dependency import get_current_user
from Models.user import User
from Models.user_question_progress import UserQuestionProgress
from datetime import datetime
from schemas.question import QuestionCreate
from sqlalchemy import exists
router = APIRouter(
    prefix="/questions",
    tags=["Questions"]
)

# Get all + filters
from Models.company import Company
from Models.difficulty import DifficultyLevel

@router.get("/", response_model=list[QuestionResponse])
@router.get("/", response_model=list[QuestionResponse])
def get_questions(
    question_type: str = None,
    difficulty: str = None,
    company: str = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    query = db.query(Question)

    if question_type:
        query = (
            query.join(QuestionType)
            .filter(
                QuestionType.name.ilike(
                    f"%{question_type}%"
                )
            )
        )

    if difficulty:
        query = (
            query.join(DifficultyLevel)
            .filter(
                DifficultyLevel.name.ilike(
                    f"%{difficulty}%"
                )
            )
        )

    if company:
        query = (
            query.join(Company)
            .filter(
                Company.name.ilike(
                    f"%{company}%"
                )
            )
        )

    questions = query.all()

    result = []

    for question in questions:

        bookmarked = (
            db.query(Bookmark)
            .filter(
                Bookmark.user_id == current_user.id,
                Bookmark.question_id == question.id
            )
            .first()
            is not None
        )

        completed = (
            db.query(UserQuestionProgress)
            .filter(
                UserQuestionProgress.user_id == current_user.id,
                UserQuestionProgress.question_id == question.id,
                UserQuestionProgress.is_completed == True
            )
            .first()
            is not None
        )

        result.append(
            QuestionResponse(
                id=question.id,
                question_text=question.question_text,
                company_id=question.company_id,
                topic_id=question.topic_id,
                difficulty_id=question.difficulty_id,
                question_type_id=question.question_type_id,
                is_bookmarked=bookmarked,
                is_completed=completed
            )
        )

    return result   
# Search
@router.get("/search", response_model=list[QuestionResponse])
def search_questions(
    q: str,
    db: Session = Depends(get_db)
):
    return (
        db.query(Question)
        .filter(Question.question_text.ilike(f"%{q}%"))
        .all()
    )


# Random
@router.get("/random", response_model=list[QuestionResponse])
def random_questions(
    count: int = 1,
    db: Session = Depends(get_db)
):
    return (
        db.query(Question)
        .order_by(func.random())
        .limit(count)
        .all()
    )
# By ID
@router.get("/{question_id}", response_model=QuestionResponse)
def get_question(
    question_id: int,
    db: Session = Depends(get_db)
):
    question = (
        db.query(Question)
        .filter(Question.id == question_id)
        .first()
    )

    if not question:
        raise HTTPException(
            status_code=404,
            detail="Question not found"
        )

    return question
@router.post("/{question_id}/bookmark")
def toggle_bookmark(
    question_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    
    question = (
        db.query(Question)
        .filter(Question.id == question_id)
        .first()
    )

    if not question:
        raise HTTPException(
            status_code=404,
            detail="Question not found"
        )

    bookmark = (
        db.query(Bookmark)
        .filter(
            Bookmark.user_id == current_user.id,
            Bookmark.question_id == question_id
        )
        .first()
    )

    if bookmark:
        db.delete(bookmark)
        db.commit()

        return {
            "message": "Bookmark removed",
            "is_bookmarked": False
        }

    new_bookmark = Bookmark(
        user_id=current_user.id,
        question_id=question_id
    )

    db.add(new_bookmark)
    db.commit()

    return {
        "message": "Question bookmarked",
        "is_bookmarked": True
    }
@router.get("/bookmarks/all")
def get_bookmarked_questions(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):

    questions = (
        db.query(Question)
        .join(
            Bookmark,
            Bookmark.question_id == Question.id
        )
        .filter(
            Bookmark.user_id == current_user.id
        )
        .all()
    )

    return questions
@router.post("/{question_id}/complete")
def toggle_complete(
    question_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    
    question = (
        db.query(Question)
        .filter(Question.id == question_id)
        .first()
    )

    if not question:
        raise HTTPException(
            status_code=404,
            detail="Question not found"
        )

    progress = (
        db.query(UserQuestionProgress)
        .filter(
            UserQuestionProgress.user_id == current_user.id,
            UserQuestionProgress.question_id == question_id
        )
        .first()
    )

    if not progress:
        progress = UserQuestionProgress(
            user_id=current_user.id,
            question_id=question_id,
            is_completed=True,
            completed_at=datetime.utcnow()
        )

        db.add(progress)

        message = "Question completed"

    else:
        progress.is_completed = not progress.is_completed

        if progress.is_completed:
            progress.completed_at = datetime.utcnow()
            message = "Question completed"
        else:
            progress.completed_at = None
            message = "Completion removed"

    db.commit()

    return {
        "message": message,
        "is_completed": progress.is_completed
    }
@router.get("/completed/all")
def get_completed_questions(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):

    questions = (
        db.query(Question)
        .join(
            UserQuestionProgress,
            UserQuestionProgress.question_id == Question.id
        )
        .filter(
            UserQuestionProgress.user_id == current_user.id,
            UserQuestionProgress.is_completed == True
        )
        .all()
    )

    return questions
@router.delete("/{question_id}")
def delete_question(
    question_id: int,
    db: Session = Depends(get_db)
):
    question = (
        db.query(Question)
        .filter(Question.id == question_id)
        .first()
    )

    if not question:
        raise HTTPException(
            status_code=404,
            detail="Question not found"
        )

    db.delete(question)
    db.commit()

    return {
        "message": "Question deleted successfully"
    }
@router.post("/questions")
def create_question(
    question: QuestionCreate,
    db: Session = Depends(get_db)
):
    new_question = Question(
        question_text=question.question_text,
        company_id=question.company_id,
        topic_id=question.topic_id,
        difficulty_id=question.difficulty_id,
        question_type_id=question.question_type_id
    )

    db.add(new_question)
    db.commit()
    db.refresh(new_question)

    return {
        "message": "Question added successfully",
        "question_id": new_question.id
    }



@router.get("/topic/{topic_id}")
def get_questions_by_topic(
    topic_id: int,
    db: Session = Depends(get_db)
):
    questions = (
        db.query(Question)
        .filter(Question.topic_id == topic_id)
        .all()
    )

    return questions
@router.get("/company/{company_id}/progress")
def get_company_progress(
    company_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    total_questions = (
        db.query(Question)
        .filter(Question.company_id == company_id)
        .count()
    )

    completed_questions = (
        db.query(UserQuestionProgress)
        .join(
            Question,
            Question.id == UserQuestionProgress.question_id
        )
        .filter(
            UserQuestionProgress.user_id == current_user.id,
            UserQuestionProgress.is_completed == True,
            Question.company_id == company_id,
        )
        .count()
    )

    remaining_questions = (
        total_questions - completed_questions
    )

    progress = (
        round((completed_questions / total_questions) * 100, 2)
        if total_questions > 0
        else 0
    )

    company = (
        db.query(Company)
        .filter(Company.id == company_id)
        .first()
    )

    return {
        "company": company.name if company else "",
        "total_questions": total_questions,
        "completed_questions": completed_questions,
        "remaining_questions": remaining_questions,
        "progress": progress,
    }