from pydantic import BaseModel, EmailStr

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
