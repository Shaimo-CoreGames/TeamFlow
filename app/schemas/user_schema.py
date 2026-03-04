from datetime import datetime
from typing import Optional

from uuid import UUID
from pydantic import BaseModel, EmailStr, Field, ConfigDict


# ==============================
# Base Schema
# ==============================

class UserBase(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    email: EmailStr


# ==============================
# Request Schemas
# ==============================

class UserCreate(UserBase):
    password: str = Field(
        ...,
        min_length=6,
        max_length=128,
        description="User password (min 8 characters)",
    )


class UserLogin(BaseModel):
    email: str = Field(..., example="user@example.com")
    password: str = Field(..., min_length=6, example="secret123")


# ==============================
# Response Schemas
# ==============================

class UserResponse(UserBase):
    id: UUID    
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ==============================
# Token Schemas
# ==============================

class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class TokenPayload(BaseModel):
    sub: str  # user id (subject)
    exp: int  # expiration timestamp


# ==============================
# Update Schema (Optional Future Use)
# ==============================

class UserUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=2, max_length=100)
    password: Optional[str] = Field(None, min_length=8, max_length=128)