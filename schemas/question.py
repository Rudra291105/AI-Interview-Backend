from pydantic import BaseModel


class QuestionCreate(BaseModel):
    question_text: str
    company_id: int
    topic_id: int
    difficulty_id: int
    question_type_id: int


class QuestionResponse(BaseModel):
    id: int
    question_text: str
    company_id: int
    topic_id: int
    difficulty_id: int
    question_type_id: int

    is_bookmarked: bool = False
    is_completed: bool = False

    class Config:
        from_attributes = True
class QuestionUpdate(BaseModel):
    question_text: str
    company_id: int
    topic_id: int
    difficulty_id: int
    question_type_id: int        
