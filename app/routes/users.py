from sqlalchemy import select
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.membership import ProjectMember
from app.models.project import Project
from app.schemas.user_schema import UserResponse, UserUpdate
from app.models.user import User
from app.services.user_service import UserService
from app.dependencies.auth_dependency import get_current_user

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

@router.get("/me/invitations")
async def get_my_invitations(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # This joins ProjectMember with Project to get the name
    stmt = select(
        Project.id.label("project_id"), 
        Project.name.label("project_name")
    ).join(ProjectMember, Project.id == ProjectMember.project_id).where(
        ProjectMember.user_id == current_user.id,
        ProjectMember.status == "pending"
    )
    result = await db.execute(stmt)
    return result.mappings().all()


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

@router.put(
    "/{user_id}",
    response_model=UserResponse,
    status_code=status.HTTP_200_OK,
)
async def update_user(
    user_id: str,
    user_data: UserUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Update a user.
    Only allow self-update or admin (optional logic).
    """

    # Optional: prevent updating other users
    if current_user.id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to update this user",
        )

    updated_user = await UserService.update_user(
        db=db,
        user_id=user_id,
        user_data=user_data,
    )

    if not updated_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    return updated_user


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
