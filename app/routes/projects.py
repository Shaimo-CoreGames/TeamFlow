from typing import List

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
import uuid
from app.database import get_db
from app.schemas.project_schema import (
    ProjectCreate,
    ProjectResponse,
    ProjectUpdate,
)
from app.services.project_service import ProjectService
from app.dependencies.auth_dependency import get_current_user
from app.models.user import User

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
    # This connects the Route to the Service you just fixed!
    return await ProjectService.get_organization_projects(db, org_id)