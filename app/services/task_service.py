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
        # 1. Determine assignee (Default to the creator if not specified)
        assignee_id = task_data.assigned_to if task_data.assigned_to else str(user.id)

        # 2. Create the instance
        task = Task(
            title=task_data.title,
            description=task_data.description,
            project_id=task_data.project_id,
            assigned_to=assignee_id,
            priority=task_data.priority or "Medium",
            status=task_data.status or "Pending",
            due_date=task_data.due_date,
        )

        # 3. Save to database
        db.add(task)
        await db.commit()
        
        # 4. Fetch the task with ALL relationships loaded
        # This specifically avoids the 'MissingGreenlet' error for Amir
        result = await db.execute(
            select(Task)
            .options(
                joinedload(Task.assignee),
                joinedload(Task.project).joinedload(Project.organization)
            )
            .where(Task.id == task.id)
        )
        
        db_task = result.scalar_one()

        # 5. Manual Mapping for the 'Flattened' Schema fields
        # These fields (project_name, etc.) are needed by TaskResponse
        if db_task.project:
            db_task.project_name = db_task.project.name
            db_task.organization_id = str(db_task.project.organization_id)
            
            if db_task.project.organization:
                db_task.organization_name = db_task.project.organization.name
        
        return db_task 
    
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