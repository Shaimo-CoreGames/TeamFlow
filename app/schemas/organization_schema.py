from pydantic import BaseModel, ConfigDict, Field
from uuid import UUID
from datetime import datetime
from typing import Optional
from app.models.membership import UserRole

class OrgBase(BaseModel):
    name: str
    slug: str = Field(..., description="Unique URL-friendly identifier")
    description: Optional[str] = None

class OrganizationCreate(OrgBase):
    pass

class OrgRead(OrgBase):
    id: UUID
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)

class OrgMemberAdd(BaseModel):
    user_id: UUID
    role: UserRole = UserRole.MEMBER