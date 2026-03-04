from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
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
        
        # 1. Check if slug already exists to avoid 500 error
        existing_slug = await db.execute(
            select(Organization).where(Organization.slug == org_data.slug)
        )
        if existing_slug.scalar_one_or_none():
            raise HTTPException(status_code=400, detail="URL Slug already taken")

        # 2. Create Organization instance (MATCH THE MODEL KEYS)
        org = Organization(
            name=org_data.name,
            slug=org_data.slug,        # <--- Added this (Required by model)
            owner_id=owner.id,         # <--- Now exists in model
            description=org_data.description
        )

        db.add(org)
        await db.flush() # Use flush to get org.id without committing the whole transaction yet

        # 3. Automatically add owner as Admin member
        membership = Membership(
            user_id=owner.id,
            organization_id=org.id,
            role="Organization Admin",
        )

        db.add(membership)
        
        try:
            await db.commit()
            await db.refresh(org)
            return org
        except Exception as e:
            await db.rollback()
            raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
        
    @staticmethod
    async def get_user_organizations(
        db: AsyncSession,
        user: User,
    ):
        result = await db.execute(
            select(Organization)
            .join(Membership)
            .where(Membership.user_id == user.id)
        )
        return result.scalars().all()