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
        task_id: int,
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
        task_id: int,
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