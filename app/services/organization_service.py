from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from fastapi import HTTPException, status

from app.models.organization import Organization
from app.models.membership import ProjectMember,Membership
from app.models.user import User
from app.schemas.organization_schema import OrganizationCreate
from app.models.org_role import OrganizationRole
from app.models.invitation import Invitation
from app.models.project import Project

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

    @staticmethod
    async def check_admin_access(db: AsyncSession, org_id: str, user_id: str):
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
    async def get_user_organizations(db: AsyncSession, user: User):
            # 1. Fetch organizations where the user is a member
            result = await db.execute(
                select(Organization)
                .join(Membership)
                .options(
                    selectinload(Organization.custom_roles),
                    selectinload(Organization.memberships).selectinload(Membership.user),
                    selectinload(Organization.projects)
                        .selectinload(Project.project_members)
                        .selectinload(ProjectMember.user)
                )
                .where(Membership.user_id == str(user.id))
            )
            
            orgs = result.scalars().unique().all()

            # 2. Apply Privacy Filter
            for org in orgs:
                # Check if current user is Admin of THIS org
                user_membership = next((m for m in org.memberships if m.user_id == str(user.id)), None)
                is_admin = user_membership and user_membership.role.lower() == "admin"

                if not is_admin:
                    # Amir (Member) sees only projects he is specifically added to
                    # If he's added to 0 projects, org.projects becomes []
                    org.projects = [
                        p for p in org.projects 
                        if any(pm.user_id == str(user.id) for pm in p.project_members)
                    ]
            
            return orgs

    @staticmethod
    async def get_organization_projects(db: AsyncSession, org_id: str, user: User):
        # 1. Check the user's role in the Organization
        membership_result = await db.execute(
            select(Membership).where(
                Membership.organization_id == org_id,
                Membership.user_id == str(user.id)
            )
        )
        membership = membership_result.scalar_one_or_none()
        
        if not membership:
            return [] # User isn't even in this org

        is_admin = membership.role.lower() == "admin"

        # 2. Fetch Projects with their members loaded
        query = select(Project).where(Project.organization_id == org_id).options(
            selectinload(Project.project_members).selectinload(ProjectMember.user)
        )
        
        result = await db.execute(query)
        projects = result.scalars().unique().all()

        # 3. Apply the Privacy Filter
        if is_admin:
            # Admins see everything in the "Admin Portal" view
            return projects
        else:
            # Regular members ONLY see projects they are part of
            return [
                p for p in projects 
                if any(pm.user_id == str(user.id) for pm in p.project_members)
            ]
    
    
    @staticmethod
    async def update_organization(db: AsyncSession, org_id: str, org_data: OrganizationCreate, current_user):
        # 1. RBAC Check: Must be 'Organization Admin'
        await OrganizationService.check_admin_access(db, org_id, str(current_user.id))

        # 2. Fetch the existing organization
        result = await db.execute(
            select(Organization).where(Organization.id == org_id)
        )
        org = result.scalar_one_or_none()
        
        if not org:
            raise HTTPException(status_code=404, detail="Organization not found")

        # 3. Update the fields
        org.name = org_data.name
        org.slug = org_data.slug
        org.description = org_data.description
        
        try:
            await db.commit()
            
            # 4. CRITICAL: Re-fetch with the full nested relationship chain
            # db.refresh often fails with nested async relationships. 
            # A fresh select with selectinload is much more reliable.
            final_result = await db.execute(
                select(Organization)
                .options(
                    selectinload(Organization.projects),
                    selectinload(Organization.custom_roles),
                    # This chain is what fixes the "MissingGreenlet" error
                    selectinload(Organization.memberships).selectinload(Membership.user) 
                )
                .where(Organization.id == org_id)
            )
            return final_result.scalar_one()

        except Exception as e:
            await db.rollback()
            # Logging the error helps you debug if it's a slug conflict or DB error
            print(f"Update failed: {e}")
            raise HTTPException(status_code=500, detail="Update failed")
    @staticmethod
    async def delete_organization(db: AsyncSession, org_id: str, current_user):
        # 1. RBAC Check
        await OrganizationService.check_admin_access(db, org_id, str(current_user.id))

        result = await db.execute(select(Organization).where(Organization.id == org_id))
        org = result.scalar_one_or_none()

        if not org:
            raise HTTPException(status_code=404, detail="Organization not found")

        await db.delete(org)
        await db.commit()

    # Inside class OrganizationService:

    @staticmethod
    async def get_org_by_id(db: AsyncSession, org_id: str, user: User) -> Organization:
        # 1. Fetch the Organization with all relationships
        result = await db.execute(
            select(Organization)
            .options(
                # Load projects AND their members so we can check permissions
                selectinload(Organization.projects)
                    .selectinload(Project.project_members),
                selectinload(Organization.memberships)
                    .selectinload(Membership.user),
                selectinload(Organization.custom_roles)
            )
            .where(Organization.id == org_id)
        )
        org = result.scalar_one_or_none()
        
        if not org:
            raise HTTPException(
                status_code=404, 
                detail="Organization not found"
            )

        # 2. Identify the requester's role in this specific Org
        user_membership = next((m for m in org.memberships if m.user_id == str(user.id)), None)
        is_admin = user_membership and user_membership.role.lower() == "admin"

        # 3. Apply the Privacy Filter to the projects list
        if not is_admin:
            # If Amir is a member, only keep projects where he is a project_member
            org.projects = [
                p for p in org.projects 
                if any(pm.user_id == str(user.id) for pm in p.project_members)
            ]
            
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
    
    @staticmethod
    async def invite_member(db: AsyncSession, org_id: str, email: str, sender_id: str, role: str = "Member"):
        # 1. Check if already a member
        existing_mem = await db.execute(
            select(Membership).join(User).where(
                Membership.organization_id == org_id,
                User.email == email
            )
        )
        if existing_mem.first():
            raise HTTPException(status_code=400, detail="User is already a member")

        # 2. Check if an invite is already pending
        existing_invite = await db.execute(
            select(Invitation).where(Invitation.organization_id == org_id, Invitation.email == email, Invitation.status == "pending")
        )
        if existing_invite.first():
            raise HTTPException(status_code=400, detail="An invitation is already pending for this email")

        # 3. Create the invitation
        new_invite = Invitation(
        organization_id=org_id, 
        email=email, 
        role=role, 
        invited_by=sender_id # Good practice to track who sent it
        )
        db.add(new_invite)
        await db.commit()
        return {"message": f"Invitation sent successfully as {role}"}

    @staticmethod
    async def accept_invitation(db: AsyncSession, invite_id: str, current_user: User):
        # 1. Find the invitation
        result = await db.execute(
            select(Invitation).where(Invitation.id == invite_id, Invitation.status == "pending")
        )
        invite = result.scalar_one_or_none()

        if not invite:
            raise HTTPException(status_code=404, detail="Invitation not found or already processed")

        # 2. Check if email matches (Security)
        if invite.email != current_user.email:
            raise HTTPException(status_code=403, detail="This invitation was not sent to you")

        # 3. Create the Membership using the ROLE from the invitation
        new_member = Membership(
            user_id=current_user.id,
            organization_id=invite.organization_id,
            role=invite.role  # <--- CRITICAL: Use the role stored when invited!
        )
        
        # 4. Update invite status to 'accepted' (or delete it)
        invite.status = "accepted"
        
        db.add(new_member)
        await db.commit()
        
        return {"message": f"Successfully joined as {invite.role}"}

    @staticmethod
    async def get_pending_invites_for_user(db: AsyncSession, email: str):
        # We join with Organization to give the frontend the Org Name
        result = await db.execute(
            select(Invitation, Organization.name.label("organization_name"))
            .join(Organization, Invitation.organization_id == Organization.id)
            .where(Invitation.email == email, Invitation.status == "pending")
        )
        
        invites = []
        for row in result.all():
            invite_data = row[0].__dict__.copy()
            invite_data["organization_name"] = row[1]
            invites.append(invite_data)
        return invites

    @staticmethod
    async def decline_invitation(db: AsyncSession, invite_id: str, user: User):
        result = await db.execute(
            select(Invitation).where(Invitation.id == invite_id, Invitation.email == user.email)
        )
        invite = result.scalar_one_or_none()
        
        if not invite:
            raise HTTPException(status_code=404, detail="Invitation not found")

        invite.status = "declined"
        await db.commit()
        return {"message": "Invitation declined"}