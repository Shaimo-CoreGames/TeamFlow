from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.models.user import User
from app.models.project import Project
from app.schemas.comment_schema import CommentCreate, CommentResponse
from app.services.comment_service import CommentService
from app.routes.auth import get_current_user
from typing import List

router = APIRouter(tags=["Comments"])

@router.post("/projects/{project_id}/comments", response_model=CommentResponse)
async def add_project_comment(
    project_id: str,
    comment_data: CommentCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Check if user is in the project
    is_member = await CommentService.check_membership(db, project_id, current_user.id)
    
    if not is_member:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not a member of this project."
        )

    return await CommentService.create_project_comment(db, project_id, current_user.id, comment_data)

@router.get("/projects/{project_id}/comments") # Remove response_model temporarily
async def get_project_comments(
    project_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    try:
        is_member = await CommentService.check_membership(db, project_id, current_user.id)
        if not is_member:
             raise HTTPException(status_code=403, detail="Not a member")
        
        comments = await CommentService.get_comments_by_project(db, project_id)
        return comments
    except Exception as e:
        print(f"CRITICAL ERROR: {e}") # Check your VS Code Terminal for this!
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/comments/{comment_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_comment(
    comment_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # 1. Fetch the comment
    comment = await CommentService.get_comment_by_id(db, comment_id)
    
    if not comment:
        raise HTTPException(status_code=404, detail="Comment not found")
        
    # 2. SECURITY CHECK: Does this comment belong to the current user?
    if comment.user_id != current_user.id:
        raise HTTPException(
            status_code=403, 
            detail="You can only delete your own comments!"
        )

    # 3. Delete it
    await CommentService.delete_comment(db, comment_id)
    return None