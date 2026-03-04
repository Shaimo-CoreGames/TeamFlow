from sqlalchemy.ext.asyncio import AsyncSession

from app.models.comment import Comment
from app.schemas.comment_schema import CommentCreate
from app.models.user import User


class CommentService:

    @staticmethod
    async def create_comment(
        db: AsyncSession,
        comment_data: CommentCreate,
        user: User,
    ) -> Comment:

        comment = Comment(
            task_id=comment_data.task_id,
            user_id=user.id,
            content=comment_data.content,
        )

        db.add(comment)
        await db.commit()
        await db.refresh(comment)

        return comment