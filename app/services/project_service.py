from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status
import uuid
from app.models.project import Project
from app.models.membership import Membership
from app.schemas.project_schema import ProjectCreate, ProjectUpdate
from app.models.user import User


class ProjectService:

    @staticmethod
    async def create_project(
        db: AsyncSession,
        org_id: uuid.UUID,
        project_data: ProjectCreate,
        user: User,
    ) -> Project:

        # Ensure user belongs to organization
        result = await db.execute(
            select(Membership).where(
                Membership.organization_id == str(org_id), # Force to string
                Membership.user_id == str(user.id),
            )
        )
        membership = result.scalar_one_or_none()

        if not membership:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized in this organization",
            )

        project = Project(
            id=str(uuid.uuid4()),            # Explicit string
            name=project_data.name,
            organization_id=str(org_id),     # Explicit string
            created_by=str(user.id),         # Explicit string
        )

        db.add(project)
        await db.commit()
        await db.refresh(project)

        return project


    @staticmethod
    async def update_project(
        db: AsyncSession,
        project_id: uuid.UUID,
        project_data: ProjectUpdate,
        user: User,
    ) -> Project:

        result = await db.execute(
            select(Project).where(Project.id == project_id)
        ) 
        project = result.scalar_one_or_none()

        if not project:
            raise HTTPException(status_code=404, detail="Project not found")

        if project_data.name:
            project.name = project_data.name

        await db.commit()
        await db.refresh(project)

        return project


    @staticmethod
    async def delete_project(
        db: AsyncSession,
        project_id: uuid.UUID,
        user: User,
    ):
        result = await db.execute(
            select(Project).where(Project.id == project_id)
        )
        project = result.scalar_one_or_none()

        if not project:
            raise HTTPException(status_code=404, detail="Project not found")

        await db.delete(project)
        await db.commit()

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
    async def get_organization_projects(
        db: AsyncSession,
        org_id: str, # This comes from the FastAPI route
    ):
        # We must cast org_id to str() to match the String(36) column in SQLite
        result = await db.execute(
            select(Project).where(
                Project.organization_id == str(org_id)
            )
        )
        projects = result.scalars().all()
        return projects