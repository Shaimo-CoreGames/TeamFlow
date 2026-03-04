from pydantic import BaseModel, ConfigDict, Field
from uuid import UUID
from datetime import datetime
from typing import List, Optional
from app.models.membership import UserRole
from app.schemas.project_schema import ProjectResponse

class OrgBase(BaseModel):
    name: str
    slug: str = Field(..., description="Unique URL-friendly identifier")
    description: Optional[str] = None

class OrganizationCreate(OrgBase):
    pass

class OrgRead(OrgBase):
    id: str  # Change from UUID to str
    owner_id: str  # Change from UUID to str
    created_at: datetime
    projects: List[ProjectResponse] = []
    
    model_config = ConfigDict(from_attributes=True)

class OrgMemberAdd(BaseModel):
    user_id: str
    role: str = "Members"