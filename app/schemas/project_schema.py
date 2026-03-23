from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime

# ==============================
# Base
# ==============================

class ProjectBase(BaseModel):
    name: str = Field(..., min_length=2, max_length=255)
    description: str | None = Field(None, max_length=1000)

# ==============================
# Create
# ==============================

class ProjectCreate(ProjectBase):
    pass

# ==============================
# Update
# ==============================

class ProjectUpdate(BaseModel):
    name: str | None = Field(None, min_length=2, max_length=255)
    description: str | None = Field(None, max_length=1000)

# ==============================
# Project Member Schemas
# ==============================

class UserMinimalResponse(BaseModel):
    id: str
    name: str
    email: str
    model_config = ConfigDict(from_attributes=True)

class ProjectMemberResponse(BaseModel):
    user_id: str
    role: str
    user: UserMinimalResponse  # This maps to pm.user from your selectinload
    
    model_config = ConfigDict(from_attributes=True)

# ==============================
# Final Response Schema
# ==============================

class ProjectResponse(ProjectBase):
    id: str
    organization_id: str
    created_by: str
    created_at: datetime
    # Add this line to include the members in the JSON response
    project_members: list[ProjectMemberResponse] = [] 

    model_config = ConfigDict(from_attributes=True)