from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status

from app.models.project import Project
from app.models.membership import Membership
from app.schemas.project_schema import ProjectCreate, ProjectUpdate
from app.models.user import User


class ProjectService:

    @staticmethod
    async def create_project(
        db: AsyncSession,
        project_data: ProjectCreate,
        user: User,
    ) -> Project:

        # Ensure user belongs to organization
        result = await db.execute(
            select(Membership).where(
                Membership.organization_id == project_data.organization_id,
                Membership.user_id == user.id,
            )
        )
        membership = result.scalar_one_or_none()

        if not membership:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized in this organization",
            )

        project = Project(
            name=project_data.name,
            organization_id=project_data.organization_id,
            created_by=user.id,
        )

        db.add(project)
        await db.commit()
        await db.refresh(project)

        return project

    @staticmethod
    async def update_project(
        db: AsyncSession,
        project_id: int,
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
        project_id: int,
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