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
    organization_id: int


# ==============================
# Update
# ==============================

class ProjectUpdate(BaseModel):
    name: str | None = Field(None, min_length=2, max_length=255)


# ==============================
# Response
# ==============================

class ProjectResponse(ProjectBase):
    id: int
    organization_id: int
    created_by: int

    model_config = ConfigDict(from_attributes=True)