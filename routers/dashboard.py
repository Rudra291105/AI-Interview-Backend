from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from database import get_db
from Models.interview import Interview
from Models.user import User
from utils.dependency import get_current_user
from collections import defaultdict
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


@router.get("/dashboard/progress")
def progress(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Returns complete analytics for the authenticated user.
    """

    interviews = (
        db.query(Interview)
        .filter(
            Interview.user_id == current_user.id,
            Interview.status == "completed",
        )
        .all()
    )

    if not interviews:
        return {
            "overall": {
                "total_interviews": 0,
                "average_score": 0,
                "best_score": 0,
                "total_questions": 0,
                "companies_practiced": 0,
                "roles_practiced": 0,
                "average_duration": 0,
            },
            "companies": [],
            "roles": [],
            "recent_interviews": [],
        }

    # =====================================================
    # Overall Statistics
    # =====================================================

    total_interviews = len(interviews)

    total_score = sum(i.score for i in interviews)
    total_questions = sum(i.questions_count for i in interviews)
    total_duration = sum(i.duration for i in interviews)

    average_score = round(total_score / total_interviews, 2)
    best_score = max(i.score for i in interviews)

    companies_practiced = len(
        set(i.company for i in interviews if i.company)
    )

    roles_practiced = len(
        set(i.role for i in interviews if i.role)
    )

    average_duration = round(
        total_duration / total_interviews,
        2,
    )

    # =====================================================
    # Company Analytics
    # =====================================================

    company_data = defaultdict(list)

    for interview in interviews:
        company = interview.company or "General"
        company_data[company].append(interview)

    companies = []

    for company, records in company_data.items():

        companies.append({
            "company": company,

            "interviews": len(records),

            "questions": sum(
                r.questions_count for r in records
            ),

            "average_score": round(
                sum(r.score for r in records) / len(records),
                2,
            ),

            "best_score": max(
                r.score for r in records
            ),

            "last_interview": max(
                (
                    r.completed_at
                    or r.created_at
                    for r in records
                )
            ),
        })

    companies.sort(
        key=lambda x: x["average_score"],
        reverse=True,
    )

    # =====================================================
    # Role Analytics
    # =====================================================

    role_data = defaultdict(list)

    for interview in interviews:
        role_data[interview.role].append(interview)

    roles = []

    for role, records in role_data.items():

        roles.append({
            "role": role,

            "interviews": len(records),

            "average_score": round(
                sum(r.score for r in records) / len(records),
                2,
            ),
        })

    roles.sort(
        key=lambda x: x["average_score"],
        reverse=True,
    )

    # =====================================================
    # Recent Interviews
    # =====================================================

    recent = sorted(
        interviews,
        key=lambda x: (
            x.completed_at
            or x.created_at
        ),
        reverse=True,
    )[:10]

    recent_interviews = []

    for interview in recent:

        recent_interviews.append({

            "interview_id": interview.id,

            "company": interview.company,

            "role": interview.role,

            "score": interview.score,

            "questions": interview.questions_count,

            "duration": interview.duration,

            "completed_at": (
                interview.completed_at
                or interview.created_at
            ),
        })

    # =====================================================
    # Final Response
    # =====================================================

    return {

        "overall": {

            "total_interviews": total_interviews,

            "average_score": average_score,

            "best_score": best_score,

            "total_questions": total_questions,

            "companies_practiced": companies_practiced,

            "roles_practiced": roles_practiced,

            "average_duration": average_duration,
        },

        "companies": companies,

        "roles": roles,

        "recent_interviews": recent_interviews,
    }