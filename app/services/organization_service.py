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
        
        # ... (slug check logic remains the same) ...

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
            # 1. Force a refresh to load database-generated fields like created_at
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
        # Force user.id to string to match the String(36) column in SQLite
        result = await db.execute(
            select(Organization)
            .join(Membership)
            .where(Membership.user_id == str(user.id)) 
        )
        return result.scalars().all()