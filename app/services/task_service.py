import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException

from app.models.task import Task
from app.schemas.task_schema import TaskCreate, TaskUpdate
from app.models.user import User


class TaskService:

    @staticmethod
    async def create_task(
        db: AsyncSession,
        task_data: TaskCreate,
        user: User,
    ) -> Task:

        task = Task(
            title=task_data.title,
            description=task_data.description,
            project_id=task_data.project_id,
            assigned_to=task_data.assigned_to,
            priority=task_data.priority,
            status=task_data.status,
            due_date=task_data.due_date,
        )

        db.add(task)
        await db.commit()
        await db.refresh(task)

        return task

    @staticmethod
    async def update_task(
        db: AsyncSession,
        task_id: str,
        task_data: TaskUpdate,
        user: User,
    ) -> Task:

        result = await db.execute(
            select(Task).where(Task.id == task_id)
        )
        task = result.scalar_one_or_none()

        if not task:
            raise HTTPException(status_code=404, detail="Task not found")

        for field, value in task_data.model_dump(exclude_unset=True).items():
            setattr(task, field, value)

        await db.commit()
        await db.refresh(task)

        return task

    @staticmethod
    async def delete_task(
        db: AsyncSession,
        task_id: str,
        user: User,
    ):
        result = await db.execute(
            select(Task).where(Task.id == task_id)
        )
        task = result.scalar_one_or_none()

        if not task:
            raise HTTPException(status_code=404, detail="Task not found")

        await db.delete(task)
        await db.commit()
        # app/services/task_service.py


    @staticmethod
    async def get_tasks_by_project(db: AsyncSession, project_id: str):
        # Ensure project_id is handled as a string for SQLite compatibility
        result = await db.execute(
            select(Task).where(Task.project_id == str(project_id))
        )
        return result.scalars().all()
    
    @staticmethod
    async def update_task_status(db: AsyncSession, task_id: str, status: str):
        # Use str(task_id) if there is any chance it's being passed as a UUID object
        result = await db.execute(select(Task).where(Task.id == str(task_id)))
        task = result.scalar_one_or_none()
        
        if task:
            task.status = status
            await db.commit()
            await db.refresh(task)
        return task