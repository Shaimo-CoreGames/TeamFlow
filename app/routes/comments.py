from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.comment_schema import (
    CommentCreate,
    CommentResponse,
)
from app.services.comment_service import CommentService
from app.dependencies.auth_dependency import get_current_user
from app.models.user import User

router = APIRouter(
    prefix="/comments",
    tags=["Comments"],
)


@router.post(
    "/",
    response_model=CommentResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_comment(
    comment_data: CommentCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await CommentService.create_comment(
        db=db,
        comment_data=comment_data,
        user=current_user,
    )