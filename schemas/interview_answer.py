from pydantic import BaseModel


class EvaluateAnswerRequest(BaseModel):
    session_id: int
    question_id: int
    answer: str


class EvaluateAnswerResponse(BaseModel):
    score: int
    feedback: str
    strengths: str
    improvements: str