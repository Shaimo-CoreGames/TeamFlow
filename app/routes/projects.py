from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
import uuid
from app.database import get_db
from app.models.project import Project
from app.schemas.project_schema import (
    ProjectCreate,
    ProjectResponse,
    ProjectUpdate,
)
from app.models.membership import ProjectMember,Membership
from app.services.project_service import ProjectService
from app.dependencies.auth_dependency import get_current_user
from app.models.user import User
from sqlalchemy.orm import selectinload, joinedload # Add joinedload
from app.models.organization import Organization
from sqlalchemy.orm import selectinload, joinedload


router = APIRouter(
    tags=["Projects"],
)

@router.post("/organizations/{org_id}/projects", response_model=ProjectResponse)
async def create_project(
    org_id: str, 
    project_data: ProjectCreate, 
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # You MUST 'return' the result of the service call
    new_project = await ProjectService.create_project(
        db, uuid.UUID(org_id), project_data, current_user
    )
    
    return new_project

@router.put("/projects/{project_id}", response_model=ProjectResponse)
async def update_project(
    project_id: uuid.UUID,
    project_data: ProjectUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await ProjectService.update_project(
        db=db,
        project_id=project_id,
        project_data=project_data,
        user=current_user,
    )

@router.delete(
    "/projects/{project_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_project(
    project_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await ProjectService.delete_project(
        db=db,
        project_id=project_id,
        user=current_user,
    )

@router.get("/organizations/{org_id}/projects", response_model=List[ProjectResponse])
async def list_projects(
    org_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Pass current_user to the service for filtering
    return await ProjectService.get_organization_projects(db, org_id, current_user)


@router.post("/projects/{project_id}/members")
async def add_project_member(
    project_id: str,
    payload: dict,  # Expecting {"email": "user@example.com"}
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    email = payload.get("email")
    if not email:
        raise HTTPException(status_code=400, detail="Email is required")

    # 1. Fetch Project to get the Organization ID
    result = await db.execute(select(Project).where(Project.id == project_id))
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    user_result = await db.execute(select(User).where(User.email == email))
    target_user = user_result.scalar_one_or_none()
    if not target_user:
        raise HTTPException(status_code=404, detail="User not found in system")

    org_member_check = await db.execute(
        select(Membership).where(
            Membership.organization_id == project.organization_id,
            Membership.user_id == str(target_user.id)
        )
    )
    if not org_member_check.scalar_one_or_none():
        raise HTTPException(
            status_code=403, 
            detail="User must be a member of the Organization first"
        )

    # 4. Check if already in the project
    existing = await db.execute(
        select(ProjectMember).where(
            ProjectMember.project_id == project_id,
            ProjectMember.user_id == str(target_user.id)
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="User is already a project member")

    # 5. Success: Create Project Membership
    new_member = ProjectMember(
        project_id=project_id,
        user_id=str(target_user.id)
    )
    db.add(new_member)
    
    try:
        await db.commit()
        return {"message": "Member added to project successfully"}
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail="Database error during assignment")

@router.get("/projects", response_model=List[ProjectResponse])
async def get_all_user_projects(
    db: AsyncSession = Depends(get_db), 
    current_user: User = Depends(get_current_user)
):
    query = (
        select(Project)
        .options(
            # 1. Load project_members
            # 2. THEN load the user object inside each project_member
            selectinload(Project.project_members).selectinload(ProjectMember.user),
            joinedload(Project.organization)
        )
        .join(ProjectMember, Project.id == ProjectMember.project_id)
        .where(ProjectMember.user_id == str(current_user.id))
    )
    
    result = await db.execute(query)
    # Use .unique() because joining can create duplicate rows in the result set
    projects = result.scalars().unique().all()
    
    for p in projects:
        if p.organization:
            p.organization_name = p.organization.name
        
    return projects