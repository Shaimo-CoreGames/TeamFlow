from sqlalchemy import distinct, or_, or_, select,func
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.security import hash_password
from app.database import get_db
from app.schemas.user_schema import UserResponse, UserUpdate
from app.models.user import User
from app.services.user_service import UserService
from app.dependencies.auth_dependency import get_current_user
from sqlalchemy import func, select
from app.models.organization import Organization
from app.models.task import Task
from app.models.project import Project
from app.models.organization import Organization
from sqlalchemy import select, func, or_, distinct
from app.models.membership import Membership

router = APIRouter(
    prefix="/users",
    tags=["Users"],
)

# --------------------------------------------------------
# Get Current Logged-in User
# --------------------------------------------------------

@router.get(
    "/me",
    response_model=UserResponse,
    status_code=status.HTTP_200_OK,
)
async def get_me(
    current_user: User = Depends(get_current_user),
):
    """
    Returns currently authenticated user.
    """
    return current_user

# --------------------------------------------------------
# Search Users by Username or Email
# --------------------------------------------------------

@router.get(
    "/search",
    response_model=List[UserResponse],
    status_code=status.HTTP_200_OK,
)
async def search_users(
    q: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Search for users by username or email.
    """
    if not q or len(q) < 2:
        return []
        
    return await UserService.search_users(db, query=q)

# --------------------------------------------------------
# Get User By ID
# --------------------------------------------------------

@router.get(
    "/{user_id}",
    response_model=UserResponse,
    status_code=status.HTTP_200_OK,
)
async def get_user_by_id(
    user_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    user = await UserService.get_user_by_id(db, user_id)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    return user


# --------------------------------------------------------
# Update User
# --------------------------------------------------------

# app/routes/users.py

# If main.py uses prefix="/users", this should just be "/{user_id}"
# app/routes/users.py

@router.put("/{user_id}", response_model=UserResponse) 
async def update_user(
    user_id: str, # Change this from UUID to str
    user_update: UserUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Convert string to the format your DB uses (UUID or keep as str)
    # Check if the user is trying to update someone else
    if str(user_id) != str(current_user.id):
        raise HTTPException(status_code=403, detail="Not authorized to update this profile")

    # Update fields
    if user_update.name is not None:
        current_user.name = user_update.name
    
    if user_update.password:
        # Assuming you have a pwd_context or hash function
        current_user.hashed_password = hash_password(user_update.password)

    await db.commit()
    await db.refresh(current_user)
    return current_user


# --------------------------------------------------------
# Delete User
# --------------------------------------------------------

@router.delete(
    "/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_user(
    user_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Delete a user.
    Only self or admin.
    """

    if current_user.id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to delete this user",
        )

    success = await UserService.delete_user(db, user_id)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    return None

@router.get("/me/summary")
async def get_user_summary(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    user_id_str = str(current_user.id)

    # 1. Total Orgs (Owned OR Joined via Membership)
    org_query = (
        select(func.count(distinct(Organization.id)))
        .outerjoin(Membership, Organization.id == Membership.organization_id) # Join with Membership
        .where(
            or_(
                Organization.owner_id == user_id_str,
                Membership.user_id == user_id_str
            )
        )
    )
    org_count = await db.scalar(org_query)

    # 2. Total Projects (In Orgs he owns OR belongs to)
    project_query = (
        select(func.count(distinct(Project.id)))
        .join(Organization)
        .outerjoin(Membership, Organization.id == Membership.organization_id)
        .where(
            or_(
                Organization.owner_id == user_id_str,
                Membership.user_id == user_id_str
            )
        )
    )
    project_count = await db.scalar(project_query)

    # 3. Total Tasks assigned to him
    task_count = await db.scalar(
        select(func.count(Task.id)).where(Task.assigned_to == user_id_str)
    )
    
    # 4. Completed Tasks
    done_count = await db.scalar(
        select(func.count(Task.id))
        .where(
            Task.assigned_to == user_id_str,
            func.lower(func.trim(Task.status)) == "completed"
        )
    )

    return {
        "total_orgs": org_count or 0,
        "total_projects": project_count or 0,
        "total_tasks": task_count or 0,
        "completed_tasks": done_count or 0
    }