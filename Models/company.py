from sqlalchemy import Column, Integer, String
from database import Base

class Company(Base):
    __tablename__ = "companies"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, nullable=False)
    description = Column(String(500))
    interview_rounds = Column(String(500))
    tips = Column(String(1000))