from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from fastapi import HTTPException, status

from app.models.organization import Organization
from app.models.membership import Membership
from app.models.user import User
from app.schemas.organization_schema import OrganizationCreate


class OrganizationService:

    @staticmethod
    async def create_organization(
        db: AsyncSession,
        org_data: OrganizationCreate,
        owner: User,
    ) -> Organization:
        
        slug_check = await db.execute(select(Organization).where(Organization.slug == org_data.slug))
        if slug_check.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Organization slug '{org_data.slug}' is already taken."
            )

        org = Organization(
            name=org_data.name,
            slug=org_data.slug,
            owner_id=str(owner.id),
            description=org_data.description
        )

        db.add(org)
        await db.flush() 

        membership = Membership(
            user_id=str(owner.id),
            organization_id=str(org.id),
            role="Organization Admin",
        )
        db.add(membership)
        
        try:
            await db.commit()
            # Update the refresh to include the projects relationship
            await db.refresh(org, attribute_names=["projects"]) 
            return org
        except Exception as e:
            await db.rollback()
            raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")  
        
    @staticmethod
    async def get_user_organizations(
        db: AsyncSession,
        user: User,
    ):
        # 1. We join Membership to find which orgs the user belongs to
        # 2. We use selectinload to fetch the projects for those orgs
        result = await db.execute(
            select(Organization)
            .join(Membership)
            .options(selectinload(Organization.projects)) # <--- CRITICAL FIX
            .where(Membership.user_id == str(user.id)) 
        )
        return result.scalars().all()
        
    @staticmethod
    async def update_organization(db: AsyncSession, org_id: str, org_data: OrganizationCreate, current_user):
        # 1. Find the org and explicitly load projects using selectinload
        result = await db.execute(
            select(Organization)
            .options(selectinload(Organization.projects)) # <--- ADD THIS
            .where(Organization.id == org_id, Organization.owner_id == str(current_user.id))
        )
        org = result.scalar_one_or_none()
        
        if not org:
            raise HTTPException(status_code=404, detail="Organization not found or access denied")

        # 2. Update fields
        org.name = org_data.name
        org.slug = org_data.slug
        org.description = org_data.description
        
        try:
            await db.commit()
            # 3. Refresh to make sure everything is in sync
            await db.refresh(org, attribute_names=["projects"]) 
            return org
        except Exception as e:
            await db.rollback()
            raise HTTPException(status_code=500, detail=f"Update failed: {str(e)}")
        
    @staticmethod
    async def delete_organization(db: AsyncSession, org_id: str, current_user):
        # Find the org and ensure the current user is the owner
        result = await db.execute(
            select(Organization).where(Organization.id == org_id, Organization.owner_id == current_user.id)
        )
        org = result.scalar_one_or_none()

        if not org:
            raise HTTPException(status_code=404, detail="Organization not found or access denied")

        # Delete the organization (cascading projects depends on your DB relationship config)
        await db.delete(org)
        await db.commit()