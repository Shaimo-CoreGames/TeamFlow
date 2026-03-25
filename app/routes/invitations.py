from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.models.user import User
from app.services.auth_service import get_current_user
from app.services.organization_service import OrganizationService

router = APIRouter()

@router.get("/users/me/invites")
async def get_my_invitations(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Returns a list of all pending invitations for the logged-in user.
    """
    return await OrganizationService.get_pending_invites_for_user(db, current_user.email)

@router.post("/invitations/{invite_id}/accept")
async def accept_org_invitation(
    invite_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Accepts an invitation and creates the organization membership.
    """
    return await OrganizationService.accept_invitation(db, invite_id, current_user)

@router.post("/invitations/{invite_id}/decline")
async def decline_org_invitation(
    invite_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Declines the invitation by marking it as 'declined'.
    """
    return await OrganizationService.decline_invitation(db, invite_id, current_user)