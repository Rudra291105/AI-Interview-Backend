from sqlalchemy import Column, Integer, String, DateTime
from database import Base
from datetime import datetime


class InterviewSession(Base):
    __tablename__ = "interview_sessions"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=False)
    company_id = Column(Integer, nullable=False)
    interview_type = Column(String,default="practice" )
    status = Column(String, default="in_progress")
    started_at = Column(DateTime,default=datetime.utcnow)
    completed_at = Column(DateTime,nullable=True)