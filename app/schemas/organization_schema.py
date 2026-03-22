from pydantic import BaseModel, ConfigDict, Field
from uuid import UUID
from datetime import datetime
from typing import List, Optional
from app.schemas.project_schema import ProjectResponse
from app.schemas.user_schema import UserResponse

class OrgBase(BaseModel):
    name: str
    slug: str = Field(..., description="Unique URL-friendly identifier")
    description: Optional[str] = None
class OrganizationCreate(OrgBase):
    pass
class OrganizationRoleRead(BaseModel):
    id: str
    role_name: str
    
    model_config = ConfigDict(from_attributes=True)
class MembershipRead(BaseModel):
    user_id: str
    role: str  # e.g., "Organization Admin"
    # job_title: Optional[str] = None # For future expansion
    user: Optional[UserResponse] = None # If you want to nest user info
    
    model_config = ConfigDict(from_attributes=True)
class OrgRead(OrgBase):
    id: str
    owner_id: str
    created_at: datetime
    
    # 1. The list of projects (already here)
    projects: List[ProjectResponse] = []
    
    # 2. The list of dynamic labels (Admin, Manager, Member, Weaver, etc.)
    custom_roles: List[OrganizationRoleRead] = []
    
    # 3. The list of actual people in the org (for the Circles)
    memberships: List[MembershipRead] = []
    
    model_config = ConfigDict(from_attributes=True)
    @property
    def member_count(self) -> int:
        return len(self.memberships)
class OrgMemberAdd(BaseModel):
    user_id: str
    role: str = "Member"  # Default matches your seed
