import os
import csv
from io import StringIO
from fastapi import FastAPI, UploadFile, File, HTTPException, Depends, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from database import engine, Base, get_db
from Models.user import User
from Models.interview import Interview
from Models.company import Company
from Models.topic import Topic
from Models.difficulty import DifficultyLevel
from Models.question_type import QuestionType
from Models.question import Question
from Models.bookmark import Bookmark
from routers.auth import router as auth_router
from routers.dashboard import router as dashboard_router
from routers.question import router as question_router
from utils.security import hash_password
from utils.dependency import get_current_user
from Models.user_question_progress import UserQuestionProgress
from routers.interview_session import router as interview_session_router
from routers.interview_answer import router as interview_answer_router
from routers.interview import router as virtual_interview_router

Base.metadata.create_all(bind=engine)

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(interview_session_router)
app.include_router(auth_router)
app.include_router(dashboard_router)
app.include_router(question_router)
app.include_router(interview_answer_router)
app.include_router(
    interview_answer_router,
    prefix="/interview-answers",
    tags=["Interview Answers"]
)
app.include_router(virtual_interview_router)


# ── Resume Upload (updated: saves filename to user record) ────────
@app.post("/upload-resume")
async def upload_resume(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),   # ← NEW: requires auth
    db: Session = Depends(get_db),                    # ← NEW: needs DB
):
    # Validate file type
    allowed_extensions = {".pdf", ".doc", ".docx"}
    file_ext = os.path.splitext(file.filename)[1].lower()
    if file_ext not in allowed_extensions:
        raise HTTPException(
            status_code=400,
            detail="Only PDF, DOC, and DOCX files are allowed."
        )

    os.makedirs("uploads", exist_ok=True)

    # Save with user_id prefix to avoid filename conflicts between users
    safe_filename = f"user_{current_user.id}_{file.filename}"
    file_path = os.path.join("uploads", safe_filename)

    with open(file_path, "wb") as buffer:
        buffer.write(await file.read())

    # ← NEW: persist filename on the user record
    current_user.resume_filename = safe_filename
    db.commit()

    return {
        "message": "Resume uploaded successfully",
        "filename": safe_filename
    }


@app.get("/")
def home():
    return {"message": "FastAPI is running"}


@app.post("/admin/import-users")
async def import_users(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Only admins can import users")
    if not file.filename.endswith(".csv"):
        raise HTTPException(status_code=400, detail="Please upload a CSV file")
    content = await file.read()
    csv_file = StringIO(content.decode("utf-8"))
    reader = csv.DictReader(csv_file)
    inserted = 0
    failed = 0
    for row in reader:
        existing_user = db.query(User).filter(User.email == row["email"]).first()
        if existing_user:
            failed += 1
            continue
        new_user = User(
            name=row["name"],
            email=row["email"],
            password=hash_password(row["password"]),
            college=row["college"],
            branch=row["branch"],
            graduation_year=int(row["graduation_year"]),
            primary_skill=row["primary_skill"],
            target_company=row["target_company"],
            target_role=row["target_role"],
            role=row["role"]
        )
        db.add(new_user)
        inserted += 1
    db.commit()
    return {"message": "Import completed", "inserted": inserted, "failed": failed}


@app.get("/admin/users")
def get_all_users(
    role: str | None = Query(None),
    branch: str | None = Query(None),
    skill: str | None = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Only admins can access this resource")
    query = db.query(User)
    if role:
        query = query.filter(User.role == role)
    if branch:
        query = query.filter(User.branch == branch)
    if skill:
        query = query.filter(User.primary_skill == skill)
    users = query.all()
    return [
        {
            "id": user.id,
            "name": user.name,
            "email": user.email,
            "college": user.college,
            "branch": user.branch,
            "graduation_year": user.graduation_year,
            "primary_skill": user.primary_skill,
            "target_company": user.target_company,
            "target_role": user.target_role,
            "role": user.role,
        }
        for user in users
    ]