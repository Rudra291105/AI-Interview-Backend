from pydantic import BaseModel

class InterviewCreate(BaseModel):
    user_id: int
    role: str
    score: float
    questions_count: int
    duration: int
    feedback: str