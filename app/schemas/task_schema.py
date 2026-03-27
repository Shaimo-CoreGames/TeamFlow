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

# Add this above TaskResponse
class UserMin(BaseModel):
    id: str
    name: str  # Or 'name' - check your User model field!
    
    model_config = ConfigDict(from_attributes=True)

# Update TaskResponse
class TaskResponse(TaskBase):
    id: str
    project_id: str
    assigned_to: Optional[str] = None
    assignee: Optional[UserMin] = None 
    
    # --- ADD THESE FOR THE UI ---
    project_name: Optional[str] = None
    organization_name: Optional[str] = None
    organization_id: Optional[str] = None # Helpful for navigation
    
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)