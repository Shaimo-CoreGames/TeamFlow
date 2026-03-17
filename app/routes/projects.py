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
from app.models.membership import ProjectMember
from app.schemas.user_schema import InviteUserRequest
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

@router.post("/projects/{project_id}/invite", status_code=status.HTTP_201_CREATED)
async def invite_user_to_project(
    project_id: str,
    request: InviteUserRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # 1. Verify the project exists
    project_query = select(Project).where(Project.id == project_id)
    project_result = await db.execute(project_query)
    project = project_result.scalars().first()
    
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # 2. Check if the user is already invited or a member
    membership_query = select(ProjectMember).where(
        ProjectMember.project_id == project_id,
        ProjectMember.user_id == request.user_id
    )
    membership_result = await db.execute(membership_query)
    existing_membership = membership_result.scalars().first()

    if existing_membership:
        raise HTTPException(
            status_code=400, 
            detail="User is already a member or has a pending invitation"
        )

    # 3. Create the new pending membership
    new_invite = ProjectMember(
        project_id=project_id,
        user_id=request.user_id,
        role="member",      # Default role
        status="pending"    # This is the "Invitation" state
    )

    db.add(new_invite)
    try:
        await db.commit()
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail="Database error during invitation")

    return {"message": "Invitation sent successfully"}

@router.post("/projects/{project_id}/respond-invite")
async def respond_to_invite(
    project_id: str,
    response: str, # "accepted" or "declined"
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Find the pending invitation
    stmt = select(ProjectMember).where(
        ProjectMember.project_id == project_id,
        ProjectMember.user_id == current_user.id,
        ProjectMember.status == "pending"
    )
    result = await db.execute(stmt)
    membership = result.scalar_one_or_none()

    if not membership:
        raise HTTPException(status_code=404, detail="Invitation not found")

    if response == "accepted":
        membership.status = "accepted"
        membership.role = "member" # Or whatever default role you prefer
    else:
        # If declined, we can just delete the record
        await db.delete(membership)
    
    await db.commit()
    return {"message": f"Invitation {response}"}