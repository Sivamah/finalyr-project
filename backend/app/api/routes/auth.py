from datetime import timedelta
from fastapi import APIRouter, HTTPException
from app.db.models import User
from app.schemas.auth import UserLogin, Token, UserResponse
from app.api.deps import SessionDep, CurrentUser
from app.core import security
from app.core.config import settings

router = APIRouter()


@router.post("/login", response_model=Token)
def login(user_in: UserLogin, db: SessionDep):
    user = db.query(User).filter(User.email == user_in.email).first()
    if not user or not security.verify_password(user_in.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Incorrect email or password")
    if user.role != "Admin":
        raise HTTPException(status_code=403, detail="Admin access only")

    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = security.create_access_token(
        user.id, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}


@router.get("/profile", response_model=UserResponse)
def read_user_me(current_user: CurrentUser):
    return current_user


@router.post("/logout")
def logout():
    return {"message": "Successfully logged out"}
