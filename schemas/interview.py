from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime


# =====================================================
# Save Interview (Existing Functionality – unchanged)
# =====================================================

class InterviewCreate(BaseModel):
    user_id: int
    company: Optional[str] = None
    role: str
    score: float
    questions_count: int
    duration: int
    feedback: str


# =====================================================
# Start Interview
# =====================================================

class StartInterviewRequest(BaseModel):
    company: Optional[str] = None
    role: str
    question_type: Optional[str] = None
    difficulty: Optional[str] = None


class StartInterviewResponse(BaseModel):
    interview_id: int
    greeting: str
    question: str
    question_type: str
    difficulty: str
    is_followup: bool = False


# =====================================================
# Submit Answer → Get Next Question
# =====================================================

class SubmitAnswerRequest(BaseModel):
    interview_id: int
    answer: str


class SubmitAnswerResponse(BaseModel):
    # Evaluation of the submitted answer
    score: float
    feedback: str
    strengths: str
    improvements: str

    # Next question (None if interview is complete)
    next_question: Optional[str] = None
    question_type: Optional[str] = None
    difficulty: Optional[str] = None
    is_followup: bool = False

    # Interview progress
    questions_asked: int
    interview_complete: bool


# =====================================================
# Interview Message (stored in DB)
# =====================================================

class InterviewMessageResponse(BaseModel):
    id: int
    question: str
    answer: Optional[str] = None
    score: Optional[float] = None
    feedback: Optional[str] = None
    difficulty: Optional[str] = None
    question_type: Optional[str] = None

    class Config:
        from_attributes = True


# =====================================================
# End Interview → Trigger Final Report
# =====================================================

class EndInterviewRequest(BaseModel):
    interview_id: int


# =====================================================
# Final Detailed Interview Report
# =====================================================

class FinalReportResponse(BaseModel):
    interview_id: int
    overall_score: float
    technical_knowledge: float
    communication: float
    confidence: float
    problem_solving: float
    strengths: List[str]
    weaknesses: List[str]
    suggested_improvements: List[str]
    topics_to_study: List[str]
    final_feedback: str
    total_questions: int
    company: Optional[str] = None
    role: str


# =====================================================
# Interview History
# =====================================================

class InterviewHistoryResponse(BaseModel):
    interview_id: int
    company: Optional[str] = None
    role: str
    score: float
    questions_count: int
    duration: int
    feedback: str
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True