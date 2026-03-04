from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.membership_schema import (
    MembershipCreate,
    MembershipResponse,
)
from app.services.membership_service import MembershipService
from app.dependencies.auth_dependency import get_current_user
from app.models.user import User

router = APIRouter(
    prefix="/memberships",
    tags=["Memberships"],
)


@router.post(
    "/",
    response_model=MembershipResponse,
    status_code=status.HTTP_201_CREATED,
)
async def add_member(
    membership_data: MembershipCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await MembershipService.add_member(
        db=db,
        membership_data=membership_data,
        user=current_user,
    )