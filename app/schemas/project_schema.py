import uuid

from pydantic import BaseModel, Field, ConfigDict


# ==============================
# Base
# ==============================

class ProjectBase(BaseModel):
    name: str = Field(..., min_length=2, max_length=255)


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


# ==============================
# Response
# ==============================

class ProjectResponse(ProjectBase):
    id: str
    organization_id: str
    created_by: str

    model_config = ConfigDict(from_attributes=True)