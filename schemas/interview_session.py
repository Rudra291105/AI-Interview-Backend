from pydantic import BaseModel


class InterviewSessionCreate(BaseModel):
    company_id: int
    interview_type: str = "practice"


class InterviewSessionResponse(BaseModel):
    id: int
    user_id: int
    company_id: int
    interview_type: str
    status: str

    class Config:
        from_attributes = True