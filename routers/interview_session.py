from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from database import get_db
from Models.interview_session import InterviewSession
from schemas.interview_session import (
    InterviewSessionCreate
)

router = APIRouter(
    prefix="/interview-sessions",
    tags=["Interview Sessions"]
)


@router.post("/start")
def start_interview(
    data: InterviewSessionCreate,
    db: Session = Depends(get_db)
):

    session = InterviewSession(
        user_id=1,  # replace with JWT user later
        company_id=data.company_id,
        interview_type=data.interview_type
    )

    db.add(session)
    db.commit()
    db.refresh(session)

    return {
        "message": "Interview Started",
        "session_id": session.id
    }


@router.get("/")
def get_sessions(
    db: Session = Depends(get_db)
):
    return db.query(
        InterviewSession
    ).all()