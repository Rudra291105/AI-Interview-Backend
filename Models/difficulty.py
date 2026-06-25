from sqlalchemy import Column, Integer, String
from database import Base

class DifficultyLevel(Base):
    __tablename__ = "difficulty_levels"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), unique=True)