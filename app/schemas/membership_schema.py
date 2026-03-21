from typing import Optional
from pydantic import BaseModel, Field, ConfigDict
from app.schemas.user_schema import UserResponse
class MembershipBase(BaseModel):
    user_id: str
    organization_id: str
    user: Optional[UserResponse] = None
    role: str = Field(..., min_length=3, max_length=50)
class MembershipCreate(MembershipBase):
    pass
class MembershipResponse(MembershipBase):
    id: str
    model_config = ConfigDict(from_attributes=True)