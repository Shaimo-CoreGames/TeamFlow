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
# Response
# ==============================

class ProjectResponse(ProjectBase):
    id: str
    organization_id: str
    created_by: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)