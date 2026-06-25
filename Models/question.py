from sqlalchemy import (Column,Integer,String,Text,ForeignKey,)
from database import Base

class Question(Base):
    __tablename__ = "questions"
    id = Column(Integer, primary_key=True, index=True)
    question_text = Column(Text, nullable=False)
    company_id = Column(Integer,ForeignKey("companies.id"))
    topic_id = Column(Integer,ForeignKey("topics.id"))
    difficulty_id = Column(Integer,ForeignKey("difficulty_levels.id"))
    question_type_id = Column(Integer,ForeignKey("question_types.id"))