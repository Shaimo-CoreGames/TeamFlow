from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, ConfigDict


# ==============================
# Base
# ==============================

class TaskBase(BaseModel):
    title: str = Field(..., min_length=2, max_length=255)
    description: Optional[str] = None
    priority: Optional[str] = Field(default="Medium", max_length=50)
    status: Optional[str] = Field(default="Pending", max_length=50)
    due_date: Optional[datetime] = None


# ==============================
# Create
# ==============================

class TaskCreate(TaskBase):
    project_id: str
    assigned_to: Optional[str] = None


# ==============================
# Update
# ==============================

class TaskUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=2, max_length=255)
    description: Optional[str] = None
    priority: Optional[str] = Field(None, max_length=50)
    status: Optional[str] = Field(None, max_length=50)
    assigned_to: Optional[str] = None
    due_date: Optional[datetime] = None


# ==============================
# Response
# ==============================

class TaskResponse(TaskBase):
    id: str
    project_id: str
    assigned_to: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)