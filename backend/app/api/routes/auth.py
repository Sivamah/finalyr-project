from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.db.models import User
from app.schemas.user import UserCreate, UserResponse, UserLogin, Token
from app.api.deps import SessionDep, CurrentUser
from app.core import security
from app.core.config import settings

router = APIRouter()


@router.post("/register", response_model=UserResponse, status_code=201,
             summary="Register a new user")
def register(user_in: UserCreate, db: SessionDep):
    user = db.query(User).filter(User.email == user_in.email).first()
    if user:
        raise HTTPException(
            status_code=400,
            detail="The user with this email already exists in the system.",
        )
    if user_in.role == "Admin":
        raise HTTPException(
            status_code=400,
            detail="Admin registration is disabled.",
        )
    if user_in.phone:
        user_by_phone = db.query(User).filter(User.phone == user_in.phone).first()
        if user_by_phone:
            raise HTTPException(
                status_code=400,
                detail="The user with this phone number already exists in the system.",
            )

    user_data = user_in.model_dump(exclude={"password"})
    user_data["password_hash"] = security.get_password_hash(user_in.password)

    db_user = User(**user_data)
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user


@router.post("/login", response_model=Token, summary="Login and get JWT token")
def login(user_in: UserLogin, db: SessionDep):
    """Accepts JSON body: { "email": "...", "password": "..." }"""
    user = db.query(User).filter(User.email == user_in.email).first()
    if not user or not security.verify_password(user_in.password, user.password_hash):
        raise HTTPException(status_code=400, detail="Incorrect email or password")
    if user.role != user_in.role:
        raise HTTPException(status_code=400, detail="Incorrect role selected")

    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = security.create_access_token(
        user.id, expires_delta=access_token_expires
    )
    return {
        "access_token": access_token,
        "token_type": "bearer",
    }


@router.get("/profile", response_model=UserResponse, summary="Get current user profile")
def read_user_me(current_user: CurrentUser):
    return current_user


@router.post("/logout", summary="Logout (client-side token removal)")
def logout():
    # JWT is stateless; logout is handled by the client removing the token.
    return {"message": "Successfully logged out"}
