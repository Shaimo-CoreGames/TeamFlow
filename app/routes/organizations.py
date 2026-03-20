from sqlalchemy import select

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from app.database import get_db
from app.models.org_role import OrganizationRole
from app.models.organization import Organization
from app.schemas.organization_schema import OrgRead, OrganizationCreate
from app.services.organization_service import OrganizationService
from app.dependencies.auth_dependency import get_current_user
from app.models.membership import Membership
from sqlalchemy.orm import selectinload


router = APIRouter(prefix="/organizations", tags=["Organizations"])

@router.post("/", response_model=OrgRead, status_code=status.HTTP_201_CREATED)
async def create_org(
    org_in: OrganizationCreate,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user)
):
    # Optional: Check if slug already exists
    return await OrganizationService.create_organization(
        db=db, 
        org_data=org_in, 
        owner=current_user
    )

@router.get("/", response_model=List[OrgRead])
async def list_my_organizations(
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Returns all organizations the current user belongs to"""
    return await OrganizationService.get_user_organizations(db, current_user)

@router.get("/me/invites")
async def get_my_invitations(
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Called by checkInvitations() in JS to populate the bell icon"""
    return await OrganizationService.get_pending_invites_for_user(db, current_user.email)

@router.put("/{org_id}", response_model=OrgRead)
async def update_org(
    org_id: str,
    org_in: OrganizationCreate,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user)
):
    return await OrganizationService.update_organization(db, org_id, org_in, current_user)

@router.get("/{org_id}", response_model=OrgRead)
async def get_organization(
    org_id: str,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user)
):
    # This calls the helper we wrote in the Service
    return await OrganizationService.get_org_by_id(db, org_id)
@router.delete("/{org_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_org(
    org_id: str,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user)
):
    await OrganizationService.delete_organization(db, org_id, current_user)
    return None # HTTP 204 requires no body



@router.put("/{org_id}/roles/{role_id}", response_model=OrgRead)
async def update_org_role(
    org_id: str,
    role_id: str,
    role_name: str, # You might want a small schema for this
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user)
):
    # Security Check
    await OrganizationService._check_admin_access(db, org_id, str(current_user.id))
    
    result = await db.execute(
        select(OrganizationRole).where(
            OrganizationRole.id == role_id, 
            OrganizationRole.organization_id == org_id
        )
    )
    role = result.scalar_one_or_none()
    if not role:
        raise HTTPException(status_code=404, detail="Role not found")
        
    role.role_name = role_name
    await db.commit()
    
    # Return the whole Org so the frontend state stays in sync
    return await OrganizationService.get_org_by_id(db, org_id)

@router.delete("/{org_id}/roles/{role_id}")
async def delete_org_role(
    org_id: str,
    role_id: str,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user)
):
    await OrganizationService._check_admin_access(db, org_id, str(current_user.id))
    
    result = await db.execute(
        select(OrganizationRole).where(
            OrganizationRole.id == role_id, 
            OrganizationRole.organization_id == org_id
        )
    )
    role = result.scalar_one_or_none()
    if role:
        await db.delete(role)
        await db.commit()
    return {"message": "Role deleted"}

@router.post("/{org_id}/invite", status_code=status.HTTP_201_CREATED)
async def invite_org_member(
    org_id: str,
    email: str, 
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user)
):
    # 1. Security Check: Only admins can invite
    await OrganizationService.check_admin_access(db, org_id, str(current_user.id))

    # 2. Call the NEW invitation logic
    # This creates a row in the Invitations table, NOT the Memberships table
    return await OrganizationService.invite_member(
        db=db, 
        org_id=org_id, 
        email=email, 
        sender_id=str(current_user.id)
    )

@router.delete("/{org_id}/members/{user_id}", response_model=OrgRead)
async def remove_org_member(
    org_id: str,
    user_id: str,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user)
):
    # 1. Security: Only allow admins to remove members
    await OrganizationService.check_admin_access(db, org_id, current_user.id)
    
    # 2. Call the service to handle the deletion
    return await OrganizationService.remove_member(db, org_id, user_id)

@router.post("/invites/{invite_id}/accept")
async def accept_invitation(
    invite_id: str,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Moves user from 'Invitation' to 'Membership' table"""
    return await OrganizationService.accept_invitation(db, invite_id, current_user)

@router.post("/invites/{invite_id}/decline")
async def decline_invitation(
    invite_id: str,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user)
):
    return await OrganizationService.decline_invitation(db, invite_id, current_user)
