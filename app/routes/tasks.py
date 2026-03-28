from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from app.database import get_db
from app.schemas.task_schema import (
    TaskCreate,
    TaskResponse,
    TaskUpdate,
)
from app.services.task_service import TaskService
from app.dependencies.auth_dependency import get_current_user
from app.models.user import User
from sqlalchemy import select
from app.models.task import Task
from sqlalchemy.orm import joinedload # Import this!
from app.models.project import Project 
from sqlalchemy import func, String 

router = APIRouter(
    tags=["Tasks"],
)

@router.post(
    "/projects/{project_id}/tasks",
    response_model=TaskResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_task(
    project_id: str, # Get this from the URL
    task_data: TaskCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Force the task to belong to the project in the URL
    task_data.project_id = project_id 
    return await TaskService.create_task(
        db=db,
        task_data=task_data,
        user=current_user,
    )


@router.put(
    "/tasks/{task_id}",
    response_model=TaskResponse,
)
async def update_task(
    task_id: str,
    task_data: TaskUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await TaskService.update_task(
        db=db,
        task_id=task_id,
        task_data=task_data,
        user=current_user,
    )


@router.delete(
    "/tasks/{task_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_task(
    task_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    await TaskService.delete_task(
        db=db,
        task_id=task_id,
        user=current_user,
    )

@router.get("/tasks/project/{project_id}", response_model=List[TaskResponse])
async def get_project_tasks(
    project_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user) # Add this line!
):
    return await TaskService.get_tasks_by_project(db, project_id)


@router.patch("/tasks/{task_id}/status", response_model=TaskResponse)
async def update_task_status(
    task_id: str, 
    payload: dict,
    db: AsyncSession = Depends(get_db)
):
    new_status = payload.get("status")
    if not new_status:
        raise HTTPException(status_code=400, detail="Status field is required")

    # Call the service layer to update the DB
    task = await TaskService.update_task_status(db, task_id, new_status)
    
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
        
    return task

@router.get("/tasks/recent", response_model=list[TaskResponse]) # Use the updated schema
async def get_recent_tasks(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    result = await db.execute(
        select(Task)
        .options(joinedload(Task.assignee)) # 👈 This joins the User table
        .where(Task.assigned_to == str(current_user.id)) 
        .order_by(Task.created_at.desc())
        .limit(5)
    )
    return result.scalars().all()

@router.get("/tasks/my-tasks", response_model=List[TaskResponse])
async def get_my_global_tasks(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Ensure we are searching by the exact string ID
    user_id_str = str(current_user.id).strip()

    query = (
        select(Task)
        .options(
            joinedload(Task.assignee),
            joinedload(Task.project).joinedload(Project.organization)
        )
        # Use func.cast to ensure the DB treats the column as a string
        .where(func.cast(Task.assigned_to, String) == user_id_str)
    )
    
    result = await db.execute(query)
    tasks = result.scalars().all()
    
    # Debug: See what the DB actually found
    print(f"DEBUG: Found {len(tasks)} tasks for User ID {user_id_str}")

    for t in tasks:
        if t.project:
            t.project_name = t.project.name
            t.organization_id = str(t.project.organization_id)
            if t.project.organization:
                t.organization_name = t.project.organization.name
        
    return tasks