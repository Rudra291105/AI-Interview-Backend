from pydantic import BaseModel, EmailStr
from typing import Optional

class UserCreate(BaseModel):#BaseModel help in identifing that is a validation class 
    name: str
    email: EmailStr
    password: str
    college: str
    branch: str
    graduation_year: int
    primary_skill: str
    target_company: str
    target_role: str

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    role: str

class RefreshRequest(BaseModel):
    refresh_token: str


class ProfileUpdate(BaseModel):
    name: Optional[str] = None
    college: Optional[str] = None
    branch: Optional[str] = None
    graduation_year: Optional[int] = None
    primary_skill: Optional[str] = None
    target_company: Optional[str] = None
    target_role: Optional[str] = None


class ProfileResponse(BaseModel):
    id: int
    name: str
    email: str

    college: Optional[str]
    branch: Optional[str]
    graduation_year: Optional[int]
    primary_skill: Optional[str]
    target_company: Optional[str]
    target_role: Optional[str]

    class Config:
        from_attributes = True