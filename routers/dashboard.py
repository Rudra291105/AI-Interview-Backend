from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from database import get_db
from Models.interview import Interview
from Models.user import User
from utils.dependency import get_current_user

router = APIRouter()


@router.get("/dashboard")
def dashboard(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Returns interview stats for the authenticated user."""
    interviews = (
        db.query(Interview)
        .filter(Interview.user_id == current_user.id)
        .all()
    )

    total_interviews = len(interviews)

    avg_score = (
        sum(i.score for i in interviews) / total_interviews
        if total_interviews > 0
        else 0
    )

    best_score = max((i.score for i in interviews), default=0)

    total_questions = sum(i.questions_count for i in interviews)

    return {
        "total_interviews": total_interviews,
        "average_score": round(avg_score, 2),
        "best_score": best_score,
        "total_questions": total_questions,
    }

@router.get("/analytics")
def analytics(
    db: Session = Depends(get_db)
):
    interviews = db.query(
        Interview
    ).all()

    if not interviews:
        return {
            "total_interviews": 0,
            "average_score": 0,
            "best_score": 0
        }

    scores = [i.score for i in interviews]

    return {
        "total_interviews": len(interviews),
        "average_score": round(
            sum(scores) / len(scores),
            2
        ),
        "best_score": max(scores)
    }