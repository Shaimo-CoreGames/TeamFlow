from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from app.database import get_db
from app.schemas.organization_schema import OrgRead, OrganizationCreate
from app.services.organization_service import OrganizationService
from app.dependencies.auth_dependency import get_current_user

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