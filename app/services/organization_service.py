from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from fastapi import HTTPException, status

from app.models.organization import Organization
from app.models.membership import Membership
from app.models.user import User
from app.schemas.organization_schema import OrganizationCreate
from app.models.org_role import OrganizationRole

class OrganizationService:

    @staticmethod
    async def create_organization(
        db: AsyncSession,
        org_data: OrganizationCreate,
        owner: User,
    ) -> Organization:
        
        # 1. Slug Uniqueness Check
        slug_check = await db.execute(
            select(Organization).where(Organization.slug == org_data.slug)
        )
        if slug_check.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Organization slug '{org_data.slug}' is already taken."
            )

        # 2. Initialize Organization
        org = Organization(
            name=org_data.name,
            slug=org_data.slug,
            owner_id=str(owner.id),
            description=org_data.description
        )
        db.add(org)
        await db.flush()  # Generates org.id for the foreign keys below

        # 3. Create the System Membership (Security)
        # This ensures the creator has 'God Mode' permissions
        membership = Membership(
            user_id=str(owner.id),
            organization_id=str(org.id),
            role="admin", 
        )
        db.add(membership)

        # 4. Seed 3 Default Job Titles (UI Labels)
        # These are the ones the Admin will see 'Edit' and 'Delete' buttons for
        default_job_titles = ["Admin", "Manager", "Member"]
        for title in default_job_titles:
            db.add(OrganizationRole(
                organization_id=org.id,
                role_name=title
            ))
        
        try:
            await db.commit()
            
            # 5. Final Refresh
            # We load projects, memberships (for circles), and custom_roles (for settings)
            await db.refresh(org, attribute_names=["projects", "memberships", "custom_roles"]) 
            return org
            
        except Exception as e:
            await db.rollback()
            print(f"Error creating organization: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
                detail="Failed to initialize organization and roles."
            )

    
    # Ensure the name matches exactly what the router calls
    @staticmethod
    async def check_admin_access(db: AsyncSession, org_id: str, user_id: str):
        # If your existing function is named _check_admin_access, 
        # you can just rename it or point to it:
        result = await db.execute(
            select(Membership).where(
                Membership.organization_id == org_id,
                Membership.user_id == user_id,
                Membership.role == "admin"
            )
        )
        if not result.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, 
                detail="Admin access required"
            )
        
    @staticmethod
    async def get_user_organizations(
        db: AsyncSession,
        user: User,
    ):
        # We must explicitly load EVERY relationship mentioned in the OrgRead schema
        result = await db.execute(
            select(Organization)
            .join(Membership)
            .options(
                selectinload(Organization.projects),
                selectinload(Organization.custom_roles),     # <--- ADD THIS
                selectinload(Organization.memberships)       # <--- ADD THIS
            )
            .where(Membership.user_id == str(user.id)) 
        )
        return result.scalars().all()

    @staticmethod
    async def update_organization(db: AsyncSession, org_id: str, org_data: OrganizationCreate, current_user):
        # 1. RBAC Check: Must be 'Organization Admin'
        await OrganizationService._check_admin_access(db, org_id, str(current_user.id))

        result = await db.execute(
            select(Organization)
            .options(
                selectinload(Organization.projects),
                selectinload(Organization.custom_roles),
                selectinload(Organization.memberships)
            )
            .where(Organization.id == org_id)
        )
        org = result.scalar_one_or_none()
        
        if not org:
            raise HTTPException(status_code=404, detail="Organization not found")

        org.name = org_data.name
        org.slug = org_data.slug
        org.description = org_data.description
        
        try:
            await db.commit()
            await db.refresh(org, attribute_names=["projects", "custom_roles", "memberships"])
            return org
        except Exception as e:
            await db.rollback()
            raise HTTPException(status_code=500, detail="Update failed")

    @staticmethod
    async def delete_organization(db: AsyncSession, org_id: str, current_user):
        # 1. RBAC Check
        await OrganizationService._check_admin_access(db, org_id, str(current_user.id))

        result = await db.execute(select(Organization).where(Organization.id == org_id))
        org = result.scalar_one_or_none()

        if not org:
            raise HTTPException(status_code=404, detail="Organization not found")

        await db.delete(org)
        await db.commit()

    # Inside class OrganizationService:

    @staticmethod
    async def get_org_by_id(db: AsyncSession, org_id: str) -> Organization:
        result = await db.execute(
            select(Organization)
            .options(
                selectinload(Organization.projects),
                selectinload(Organization.memberships).selectinload(Membership.user),
                selectinload(Organization.custom_roles)
            )
            .where(Organization.id == org_id)
        )
        org = result.scalar_one_or_none()
        
        if not org:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, 
                detail="Organization not found"
            )
        return org

    @staticmethod
    async def add_member_to_org(db: AsyncSession, org_id: str, email: str):
        # 1. Find the user by email
        user_result = await db.execute(select(User).where(User.email == email))
        user = user_result.scalar_one_or_none()
        
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        # 2. Check if they are already a member
        existing = await db.execute(
            select(Membership).where(
                Membership.organization_id == org_id, 
                Membership.user_id == user.id
            )
        )
        if existing.scalar_one_or_none():
            raise HTTPException(status_code=400, detail="User is already a member")

        # 3. Create the Membership
        new_member = Membership(
            organization_id=org_id,
            user_id=user.id,
            role="member" # Default role
        )
        db.add(new_member)
        await db.commit()
        return {"message": f"{user.name} added to organization"}
    
    @staticmethod
    async def add_member_by_email(db: AsyncSession, org_id: str, email: str):
        # 1. Find User
        user_stmt = await db.execute(select(User).where(User.email == email))
        user = user_stmt.scalar_one_or_none()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        # 2. CHECK FOR DUPLICATES (The Fix)
        existing = await db.execute(
            select(Membership).where(
                Membership.organization_id == org_id,
                Membership.user_id == user.id
            )
        )
        if existing.scalar_one_or_none():
            raise HTTPException(status_code=400, detail="User is already a member of this organization")

        # 3. Create Membership
        new_mem = Membership(organization_id=org_id, user_id=user.id, role="member")
        db.add(new_mem)
        await db.commit()
    
        return await OrganizationService.get_org_by_id(db, org_id)    
    
    @staticmethod
    async def remove_member(db: AsyncSession, org_id: str, user_id: str):
        # Find the membership record
        result = await db.execute(
            select(Membership).where(
                Membership.organization_id == org_id,
                Membership.user_id == user_id
            )
        )
        membership = result.scalar_one_or_none()

        if not membership:
            raise HTTPException(status_code=404, detail="Member not found in this organization")

        # Prevent removing the last admin or yourself if necessary
        # (Optional: add logic here to prevent accidental lockouts)

        await db.delete(membership)
        await db.commit()

        # Return the refreshed Org object so the UI updates immediately
        return await OrganizationService.get_org_by_id(db, org_id)