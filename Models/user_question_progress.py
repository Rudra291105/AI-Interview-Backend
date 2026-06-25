from sqlalchemy import Column,Integer,Boolean,ForeignKey,DateTime
from sqlalchemy.sql import func
from database import Base


class UserQuestionProgress(Base):
    __tablename__ = "user_question_progress"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer,ForeignKey("users.id"))
    question_id = Column(Integer,ForeignKey("questions.id"))
    is_completed = Column(Boolean,default=False)
    completed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime,server_default=func.now())