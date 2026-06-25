from sqlalchemy import (Column,Integer,String,Float,DateTime,BigInteger)
from database import Base
from datetime import datetime

class Interview(Base):
    __tablename__ = "interviews"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer)
    role = Column(String)
    score = Column(Float)
    questions_count = Column(Integer)
    duration = Column(Integer)
    feedback = Column(String)
    created_at = Column(DateTime,default=datetime.utcnow)