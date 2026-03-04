from pydantic import BaseModel, Field, ConfigDict


# ==============================
# Base
# ==============================

class MembershipBase(BaseModel):
    user_id: int
    organization_id: int
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

    model_config = ConfigDict(from_attributes=True)