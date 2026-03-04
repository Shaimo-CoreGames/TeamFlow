from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.comment import Comment
from app.schemas.comment_schema import CommentCreate, CommentUpdate


class CommentService:

    # -----------------------------------------------------
    # Create Comment
    # -----------------------------------------------------
    @staticmethod
    async def create_comment(
        db: AsyncSession,
        comment_data: CommentCreate,
        user_id: int,
    ) -> Comment:

        new_comment = Comment(
            content=comment_data.content,
            task_id=comment_data.task_id,
            user_id=user_id,
        )

        db.add(new_comment)
        await db.commit()
        await db.refresh(new_comment)

        return new_comment


    # -----------------------------------------------------
    # Get Comment By ID
    # -----------------------------------------------------
    @staticmethod
    async def get_comment_by_id(
        db: AsyncSession,
        comment_id: int,
    ) -> Optional[Comment]:

        result = await db.execute(
            select(Comment).where(Comment.id == comment_id)
        )
        return result.scalar_one_or_none()


    # -----------------------------------------------------
    # Get Comments By Task
    # -----------------------------------------------------
    @staticmethod
    async def get_comments_by_task(
        db: AsyncSession,
        task_id: int,
    ) -> List[Comment]:

        result = await db.execute(
            select(Comment)
            .where(Comment.task_id == task_id)
            .order_by(Comment.created_at.asc())
        )
        return result.scalars().all()


    # -----------------------------------------------------
    # Update Comment
    # -----------------------------------------------------
    @staticmethod
    async def update_comment(
        db: AsyncSession,
        comment_id: int,
        comment_data: CommentUpdate,
        user_id: int,
    ) -> Optional[Comment]:

        result = await db.execute(
            select(Comment).where(Comment.id == comment_id)
        )
        comment = result.scalar_one_or_none()

        if not comment:
            return None

        # Only comment owner can update
        if comment.user_id != user_id:
            return None

        update_data = comment_data.model_dump(exclude_unset=True)

        for key, value in update_data.items():
            setattr(comment, key, value)

        await db.commit()
        await db.refresh(comment)

        return comment


    # -----------------------------------------------------
    # Delete Comment
    # -----------------------------------------------------
    @staticmethod
    async def delete_comment(
        db: AsyncSession,
        comment_id: int,
        user_id: int,
    ) -> bool:

        result = await db.execute(
            select(Comment).where(Comment.id == comment_id)
        )
        comment = result.scalar_one_or_none()

        if not comment:
            return False

        # Only owner can delete
        if comment.user_id != user_id:
            return False

        await db.delete(comment)
        await db.commit()

        return True