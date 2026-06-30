from sqlalchemy import Column, Integer, String, DateTime
from database import Base

#user is model
class User(Base):# if we not write base it become normal class with base we tell sql alchame that it is database model
    __tablename__ = "users" #why__ is a special attribute recognized by SQLAlchemy.

    id = Column(Integer, primary_key=True, index=True)

    name = Column(String(100))
    email = Column(String(100), unique=True)
    password = Column(String(255))

    college = Column(String(100))
    branch = Column(String(100))
    graduation_year = Column(Integer)
    primary_skill = Column(String(100))
    target_company = Column(String(100))
    target_role = Column(String(100))
    resume_filename = Column(String(255), nullable=True)
    # Password-reset fields
    reset_token = Column(String(255), nullable=True)
    reset_token_expiry = Column(DateTime, nullable=True)

    # Refresh-token field (stored hashed; NULL means logged-out)
    refresh_token = Column(String(255), nullable=True)
    role = Column(String, default="user")