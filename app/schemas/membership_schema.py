from typing import Optional

from pydantic import BaseModel, Field, ConfigDict

from app.schemas.user_schema import UserResponse


# ==============================
# Base
# ==============================

class MembershipBase(BaseModel):
    user_id: int
    organization_id: int
    user: Optional[UserResponse] = None
    role: str = Field(..., min_length=3, max_length=50)


# ==============================
# Create
# ==============================

class MembershipCreate(MembershipBase):
    pass


# ==============================
# Response
# ==============================

class MembershipResponse(MembershipBase):
    id: int
    user: Optional[UserResponse] = None

    model_config = ConfigDict(from_attributes=True)