from sqlalchemy import Column, Integer, String
from database import Base

class QuestionType(Base):
    __tablename__ = "question_types"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), unique=True)