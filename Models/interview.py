from sqlalchemy import (
    Column,
    Integer,
    String,
    Float,
    DateTime,
    Text,
    Boolean,
    ForeignKey,
    JSON,
)
from sqlalchemy.orm import relationship
from database import Base
from datetime import datetime


class Interview(Base):
    __tablename__ = "interviews"

    id = Column(Integer, primary_key=True, index=True)

    # Candidate
    user_id = Column(Integer, nullable=False)

    # Interview Details
    company = Column(String, nullable=True)
    role = Column(String, nullable=False)

    # Interview Status
    status = Column(String, default="in_progress")  # in_progress | completed

    # Final Results
    score = Column(Float, default=0)
    questions_count = Column(Integer, default=0)
    duration = Column(Integer, default=0)   # seconds
    feedback = Column(Text, nullable=True)

    # Detailed AI-generated report stored as JSON
    detailed_report = Column(JSON, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)

    # One interview has many question-answer messages
    messages = relationship(
        "InterviewMessage",
        back_populates="interview",
        cascade="all, delete-orphan",
    )


class InterviewMessage(Base):
    __tablename__ = "interview_messages"

    id = Column(Integer, primary_key=True, index=True)

    interview_id = Column(
        Integer,
        ForeignKey("interviews.id"),
        nullable=False,
    )

    # AI Generated Question
    question = Column(Text, nullable=False)

    # Candidate Answer
    answer = Column(Text, nullable=True)

    # AI Evaluation
    score = Column(Float, nullable=True)
    feedback = Column(Text, nullable=True)
    strengths = Column(Text, nullable=True)
    improvements = Column(Text, nullable=True)

    # Metadata
    difficulty = Column(String, nullable=True)      # Easy / Medium / Hard
    question_type = Column(String, nullable=True)   # Technical / DSA / System Design / Behavioral / HR / Follow-up
    is_followup = Column(Boolean, default=False)

    created_at = Column(DateTime, default=datetime.utcnow)

    interview = relationship(
        "Interview",
        back_populates="messages",
    )