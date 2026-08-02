from typing import Optional
from pydantic import BaseModel, EmailStr
from datetime import datetime

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str

class UserResponse(BaseModel):
    id: int
    full_name: str
    email: str
    role: str
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True
