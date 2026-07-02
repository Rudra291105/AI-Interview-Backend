import secrets
import smtplib
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from database import get_db
from Models.user import User
from schemas.user import UserCreate, UserLogin, TokenResponse, RefreshRequest
from utils.security import (hash_password,verify_password,hash_refresh_token,verify_refresh_token,create_access_token,create_refresh_token,verify_token,)
from utils.dependency import get_current_user
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session


from utils.dependency import get_current_user

from schemas.user import ProfileUpdate, ProfileResponse
router = APIRouter()


# ─────────────────────────── Register ────────────────────────────

@router.post("/register", status_code=status.HTTP_201_CREATED)
def register(user: UserCreate, db: Session = Depends(get_db)): #bd is database connection session
   #user create for request validation it ensure incomming data has correct stru
    existing_user = db.query(User).filter(User.email == user.email).first()

    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )

    new_user = User(
        name=user.name,
        email=user.email,
        password=hash_password(user.password),
        college=user.college,
        branch=user.branch,
        graduation_year=user.graduation_year,
        primary_skill=user.primary_skill,
        target_company=user.target_company,
        target_role=user.target_role,
    )

    db.add(new_user)
    db.commit()

    return {"message": "User registered successfully"}


# ─────────────────────────── Login ───────────────────────────────

@router.post("/login", response_model=TokenResponse)
def login(user: UserLogin, db: Session = Depends(get_db)):
    db_user = db.query(User).filter(User.email == user.email).first()#this is fetching database related to the corresponding email

    if not db_user or not verify_password(user.password, db_user.password):#verify_password(user.password, db_user.password): checks if the provided password matches the hashed password stored in the database. If either the user is not found or the password is incorrect, we raise an HTTP 401 Unauthorized error with a generic message to prevent user enumeration attacks.
        # Return the same error for both cases to avoid user enumeration
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token_data = {"sub": db_user.email,"role": db_user.role}

    access_token = create_access_token(token_data)
    refresh_token = create_refresh_token(token_data)
    db_user.refresh_token = hash_refresh_token(refresh_token)
    db.commit()

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        role=db_user.role
    )


# ─────────────────────────── Refresh ─────────────────────────────

@router.post("/refresh", response_model=TokenResponse)
def refresh_tokens(body: RefreshRequest, db: Session = Depends(get_db)):
    """
    Accepts a valid refresh token and returns a new access + refresh token pair.
    The old refresh token is rotated (invalidated) on every call.
    """
    payload = verify_token(body.refresh_token, token_type="refresh")

    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    email: str = payload.get("sub")
    db_user = db.query(User).filter(User.email == email).first()

    if not db_user or not db_user.refresh_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session not found — please log in again",
        )

    # Verify the incoming token matches the one we stored
    if not verify_refresh_token(body.refresh_token, db_user.refresh_token):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token mismatch — please log in again",
        )

    # Rotate tokens
    token_data = {"sub": db_user.email}
    new_access_token = create_access_token(token_data)
    new_refresh_token = create_refresh_token(token_data)

    db_user.refresh_token = hash_refresh_token(new_refresh_token)
    db.commit()

    return TokenResponse(
        access_token=new_access_token,
        refresh_token=new_refresh_token,
    )


# ─────────────────────────── Logout ──────────────────────────────

@router.post("/logout", status_code=status.HTTP_200_OK)
def logout(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Invalidates the stored refresh token so the session cannot be resumed.
    The short-lived access token remains valid until it naturally expires.
    """
    current_user.refresh_token = None
    db.commit()
    return {"message": "Logged out successfully"}


# ─────────────────────── Forgot Password ─────────────────────────

@router.post("/forgot-password")
def forgot_password(email: str, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == email).first()

    # Don't reveal whether the email exists
    if not user:
        return {"message": "If that email is registered, a reset link has been sent"}

    token = secrets.token_urlsafe(32)
    user.reset_token = token
    user.reset_token_expiry = datetime.utcnow() + timedelta(minutes=15)
    db.commit()

    EMAIL = "interviewtest214@gmail.com"
    APP_PASSWORD = "blqqmctwmujwcjuu"

    reset_link = f"http://localhost:5173/reset-password?token={token}"
    message = f"""Subject: Password Reset

Hello,

Click the link below to reset your password:

{reset_link}

This link expires in 15 minutes.
"""

    try:
        server = smtplib.SMTP_SSL("smtp.gmail.com", 465)
        server.login(EMAIL, APP_PASSWORD)
        server.sendmail(EMAIL, user.email, message)
        server.quit()
    except Exception as e:
        return {"message": "Email sending failed", "error": str(e)}

    return {"message": "If that email is registered, a reset link has been sent"}


# ─────────────────────── Reset Password ──────────────────────────

@router.post("/reset-password")
def reset_password(token: str, new_password: str, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.reset_token == token).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid token",
        )

    if user.reset_token_expiry and user.reset_token_expiry < datetime.utcnow():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Token expired",
        )

    user.password = hash_password(new_password)
    user.reset_token = None
    user.reset_token_expiry = None
    db.commit()

    return {"message": "Password reset successful"}


# ──────────────────────────── Profile ────────────────────────────

@router.get("/profile")
def get_profile(current_user: User = Depends(get_current_user)):
    """Returns the profile of the currently authenticated user."""
    return {
        "id": current_user.id,
        "name": current_user.name,
        "email": current_user.email,
        "college": current_user.college,
        "branch": current_user.branch,
        "graduation_year": current_user.graduation_year,
        "primary_skill": current_user.primary_skill,
        "target_company": current_user.target_company,
        "target_role": current_user.target_role,
    }


@router.delete("/delete_user/{email}")
def delete_user(email: str, db: Session = Depends(get_db)):

    db_user = db.query(User).filter(User.email == email).first()

    if not db_user:
        raise HTTPException(
            status_code=404,
            detail="User not found"
        )

    db.delete(db_user)
    db.commit()

    return {
        "message": "User deleted successfully"
    }

@router.put("/profile", response_model=ProfileResponse)
def update_profile(
    profile: ProfileUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if profile.name is not None:
        current_user.name = profile.name

    if profile.college is not None:
        current_user.college = profile.college

    if profile.branch is not None:
        current_user.branch = profile.branch

    if profile.graduation_year is not None:
        current_user.graduation_year = profile.graduation_year

    if profile.primary_skill is not None:
        current_user.primary_skill = profile.primary_skill

    if profile.target_company is not None:
        current_user.target_company = profile.target_company

    if profile.target_role is not None:
        current_user.target_role = profile.target_role

    db.commit()
    db.refresh(current_user)

    return current_user