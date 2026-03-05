from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status
import uuid
from app.models.project import Project
from app.models.membership import Membership
from app.schemas.project_schema import ProjectCreate, ProjectUpdate
from app.models.user import User


class ProjectService:

    # app/services/project_service.py

    @staticmethod
    async def create_project(
        db: AsyncSession,
        org_id: str, 
        project_data: ProjectCreate,
        user: User,
    ) -> Project:
        project = Project(
            id=str(uuid.uuid4()),
            name=project_data.name,
            description=project_data.description, # Ensure this matches your Project model
            organization_id=str(org_id),
            created_by=str(user.id),
        )

        db.add(project)
        await db.commit()
        await db.refresh(project) # This fetches the created_at from the DB

        return project # <--- CRITICAL: If this is missing, the route crashes
   
   
    @staticmethod
    async def update_project(db: AsyncSession, project_id: uuid.UUID, project_data: ProjectUpdate, user: User) -> Project:
        result = await db.execute(select(Project).where(Project.id == str(project_id))) 
        project = result.scalar_one_or_none()

        if not project:
            raise HTTPException(status_code=404, detail="Project not found")

        # Update fields if provided
        if project_data.name is not None:
            project.name = project_data.name
        if project_data.description is not None: # ADDED
            project.description = project_data.description

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