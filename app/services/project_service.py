from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status
import uuid
from app.models.project import Project
from app.models.membership import Membership, ProjectMember
from app.schemas.project_schema import ProjectCreate, ProjectUpdate
from app.models.user import User
from sqlalchemy.orm import selectinload


class ProjectService:
    @staticmethod
    async def create_project(
        db: AsyncSession,
        org_id: str, 
        project_data: ProjectCreate,
        user: User,
    ) -> Project:
        """
        CREATION LOGIC:
        Creates project and adds the Admin as the first member.
        """
        # 1. Create the Project
        project = Project(
            id=str(uuid.uuid4()),
            name=project_data.name,
            description=project_data.description,
            organization_id=str(org_id),
            created_by=str(user.id),
        )
        db.add(project)
        
        # 2. Flush to ensure project.id is available
        await db.flush() 

        # 3. Add the creator (Shah Meer) to the project team
        # Note: Since Shah Meer is Admin, he'd see it anyway, but 
        # this ensures his initials show up in the "Project Team" list.
        new_member = ProjectMember(
            id=str(uuid.uuid4()),
            project_id=project.id,
            user_id=str(user.id),
            role="admin" # The creator is the project admin
        )
        db.add(new_member)

        await db.commit()
        await db.refresh(project) 
        return project
    
    @staticmethod
    async def update_project(db: AsyncSession, project_id: uuid.UUID, project_data: ProjectUpdate, user: User) -> Project:
        result = await db.execute(select(Project).where(Project.id == str(project_id))) 
        project = result.scalar_one_or_none()

        if not project:
            raise HTTPException(status_code=404, detail="Project not found")

        # Update fields if provided
        if project_data.name is not None:
            project.name = project_data.name
        if project_data.description is not None: 
            project.description = project_data.description

        await db.commit()
        await db.refresh(project)
        return project

    @staticmethod
    async def delete_project(db: AsyncSession, project_id: str, user: User):
        result = await db.execute(select(Project).where(Project.id == project_id))
        project = result.scalar_one_or_none()

        if not project:
            raise HTTPException(status_code=404, detail="Project not found")

        await db.delete(project)
        await db.commit() # Don't forget to commit the deletion!

    @staticmethod
    async def get_organization_projects(
        db: AsyncSession,
        org_id: str, # Or uuid.UUID
    ):
        result = await db.execute(
            select(Project).where(
                Project.organization_id == str(org_id) # <--- Force to string
            )
        )
        return result.scalars().all()

    @staticmethod
    async def get_organization_projects(db: AsyncSession, org_id: str, user: User):
        """
        FETCH LOGIC: 
        Checks if user is Admin (sees all) or Member (sees only assigned).
        """
        # 1. Identify User's Role in this Org
        membership_result = await db.execute(
            select(Membership).where(
                Membership.organization_id == str(org_id),
                Membership.user_id == str(user.id)
            )
        )
        membership = membership_result.scalar_one_or_none()
        
        if not membership:
            return []

        is_admin = membership.role.lower() == "admin"

        # 2. Fetch Projects with members loaded for the privacy check
        result = await db.execute(
            select(Project)
            .where(Project.organization_id == str(org_id))
            .options(
                selectinload(Project.project_members)
                .selectinload(ProjectMember.user)
            )
        )
        projects = result.scalars().unique().all()

        # 3. Apply the Privacy Filter
        if is_admin:
            # Shah Meer (Admin) sees everything
            return projects
        else:
            # Amir (Member) ONLY sees projects where he is in project_members
            return [
                p for p in projects 
                if any(pm.user_id == str(user.id) for pm in p.project_members)
            ]

    @staticmethod
    async def add_member_to_project(db: AsyncSession, project_id: str, user_email: str, current_user: User):
        # 1. Find the project and its parent Organization
        result = await db.execute(
            select(Project).where(Project.id == project_id)
        )
        project = result.scalar_one_or_none()
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")

        # 2. Find the user being invited by email
        user_result = await db.execute(
            select(User).where(User.email == user_email)
        )
        target_user = user_result.scalar_one_or_none()
        if not target_user:
            raise HTTPException(status_code=404, detail="User with this email not found")

        # 3. SECURITY CHECK: Is this user actually in the Organization?
        # This prevents external users from being 'snuck' into private projects
        org_check = await db.execute(
            select(Membership).where(
                Membership.organization_id == project.organization_id,
                Membership.user_id == str(target_user.id)
            )
        )
        if not org_check.scalar_one_or_none():
            raise HTTPException(
                status_code=403, 
                detail="This user must be added to the Organization first."
            )

        # 4. Check if already a member of the project
        existing = await db.execute(
            select(ProjectMember).where(
                ProjectMember.project_id == project_id,
                ProjectMember.user_id == str(target_user.id)
            )
        )
        if existing.scalar_one_or_none():
            raise HTTPException(status_code=400, detail="User is already in this project")

        # 5. Success: Create the project membership
        new_member = ProjectMember(
            project_id=project_id, 
            user_id=str(target_user.id),
            role="Member" # Or dynamic role if needed
        )
        db.add(new_member)
        await db.commit()
        return {"message": f"{target_user.name} added to project successfully"}