from sqlalchemy import Column, Integer, Text, DateTime,BigInteger
from database import Base
from datetime import datetime

class InterviewAnswer(Base):
    __tablename__ = "interview_answers"
    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(BigInteger, nullable=False)
    question_id = Column(Integer, nullable=False)
    answer = Column(Text, nullable=False)
    score = Column(Integer, default=0)
    feedback = Column(Text, nullable=True)
    strengths = Column(Text, nullable=True)
    improvements = Column(Text, nullable=True)
    created_at = Column(DateTime,default=datetime.utcnow)