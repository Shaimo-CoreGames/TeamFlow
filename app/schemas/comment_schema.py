from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, ConfigDict


# ==============================
# Base
# ==============================

class CommentBase(BaseModel):
    content: str = Field(..., min_length=1)


# ==============================
# Create
# ==============================

class CommentCreate(CommentBase):
    task_id: int


# ==============================
# Update
# ==============================

class CommentUpdate(BaseModel):
    content: Optional[str] = Field(None, min_length=1)


# ==============================
# Response
# ==============================

class CommentResponse(CommentBase):
    id: int
    task_id: int
    user_id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)