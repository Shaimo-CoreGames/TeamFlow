import uuid
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload # CRITICAL IMPORT
from fastapi import HTTPException

from app.models.project import Project
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
        assignee_id = task_data.assigned_to if task_data.assigned_to else str(user.id)

        task = Task(
            title=task_data.title,
            description=task_data.description,
            project_id=task_data.project_id,
            assigned_to=assignee_id,
            priority=task_data.priority,
            status=task_data.status,
            due_date=task_data.due_date,
        )

        db.add(task)
        await db.commit()
        
        # After commit, fetch the task AGAIN with the assignee loaded
        result = await db.execute(
            select(Task)
            .options(joinedload(Task.assignee))
            .where(Task.id == task.id)
        )
        return result.scalar_one()

    @staticmethod
    async def update_task(
        db: AsyncSession,
        task_id: str,
        task_data: TaskUpdate,
        user: User,
    ) -> Task:
        # Load assignee here so the response model doesn't crash
        result = await db.execute(
            select(Task)
            .options(joinedload(Task.assignee))
            .where(Task.id == str(task_id))
        )
        task = result.scalar_one_or_none()

        if not task:
            raise HTTPException(status_code=404, detail="Task not found")

        for field, value in task_data.model_dump(exclude_unset=True).items():
            setattr(task, field, value)

        await db.commit()
        await db.refresh(task, ["assignee"]) # Ensure relationship is still there
        return task

    @staticmethod
    async def get_tasks_by_project(db: AsyncSession, project_id: str):
        result = await db.execute(
            select(Task)
            .options(
                joinedload(Task.assignee),           # Loads the User (UserMin)
                joinedload(Task.project).joinedload(Project.organization) # Loads Project & Org
            )
            .where(Task.project_id == str(project_id))
            .order_by(Task.created_at.desc())
        )
        tasks = result.scalars().all()

        # MANUALLY MAP THE NAMES (since they aren't direct columns on the Task table)
        for t in tasks:
            if t.project:
                t.project_name = t.project.name
                if t.project.organization:
                    t.organization_name = t.project.organization.name
                    t.organization_id = t.project.organization.id
                    
        return tasks
    
    @staticmethod
    async def update_task_status(db: AsyncSession, task_id: str, status: str):
        result = await db.execute(
            select(Task)
            .options(joinedload(Task.assignee)) # 👈 Add this
            .where(Task.id == str(task_id))
        )
        task = result.scalar_one_or_none()
        
        if task:
            task.status = status
            await db.commit()
            await db.refresh(task, ["assignee"])
        return task

    @staticmethod
    async def delete_task(
        db: AsyncSession,
        task_id: str,
        user: User,
    ):
        result = await db.execute(
            select(Task).where(Task.id == str(task_id))
        )
        task = result.scalar_one_or_none()

        if not task:
            raise HTTPException(status_code=404, detail="Task not found")

        await db.delete(task)
        await db.commit()