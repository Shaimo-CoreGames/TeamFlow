import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.comment import Comment
from app.models.task import Task
from app.models.project import Project
from app.schemas.comment_schema import CommentCreate
from sqlalchemy.orm import selectinload

class CommentService:

    @staticmethod
    async def check_user_permission(db: AsyncSession, task_id: str, user_id: str) -> bool:
        """
        Verifies if the user is a member of the project that owns this task.
        """
        # 1. Get the project_id from the task
        task_result = await db.execute(select(Task).where(Task.id == task_id))
        task = task_result.scalar_one_or_none()
        if not task:
            return False

        # 2. Check if the user is in the ProjectMember table for that project
        member_result = await db.execute(
            select(Project).where(
                Project.id == task.project_id,
                Project.members.any(user_id == str(user_id))
            )
        )
        return member_result.scalar_one_or_none() is not None

    @staticmethod
    async def create_comment(db: AsyncSession, task_id: str, user_id: str, data: CommentCreate):
        new_comment = Comment(
            id=str(uuid.uuid4()),
            task_id=task_id,
            user_id=str(user_id),
            content=data.content,
            parent_id=data.parent_id  # For threaded replies
        )
        db.add(new_comment)
        await db.commit()
        await db.refresh(new_comment)
        return new_comment
    
    @staticmethod
    async def create_project_comment(db: AsyncSession, project_id: str, user_id: str, data: CommentCreate):
        new_comment = Comment(
            id=str(uuid.uuid4()),
            project_id=project_id, # Make sure your Comment model has project_id
            task_id=None,          # It's a general project comment
            user_id=str(user_id),
            content=data.content
        )
        db.add(new_comment)
        await db.commit()
        await db.refresh(new_comment)
        return new_comment

    @staticmethod
    async def get_task_comments(db: AsyncSession, task_id: str):
        # We use joinedload to get the user's name/avatar along with the comment
        result = await db.execute(
            select(Comment)
            .where(Comment.task_id == task_id)
            .order_by(Comment.created_at.asc())
        )
        return result.scalars().all()

    @staticmethod
    async def check_membership(db: AsyncSession, project_id: str, user_id: int):
        # This logic checks if the user is a member of the project's organization
        from app.models.project import Project
        from app.models.membership import Membership

        # Find the project to get its organization_id
        result = await db.execute(select(Project).where(Project.id == project_id))
        project = result.scalars().first()
        
        if not project:
            return False

        # Check if a membership exists for this user in that organization
        mem_result = await db.execute(
            select(Membership).where(
                Membership.organization_id == project.organization_id,
                Membership.user_id == user_id
            )
        )
        return mem_result.scalars().first() is not None

    @staticmethod
    async def get_comments_by_project(db: AsyncSession, project_id: str):
        # We MUST load the user relationship so the frontend gets the name
        result = await db.execute(
            select(Comment)
            .where(Comment.project_id == project_id)
            .options(selectinload(Comment.user)) # This prevents the 500 error
            .order_by(Comment.created_at.asc())
        )
        return result.scalars().all()

    @staticmethod
    async def get_comment_by_id(db: AsyncSession, comment_id: str):
        result = await db.execute(select(Comment).where(Comment.id == comment_id))
        return result.scalar_one_or_none()

    @staticmethod
    async def delete_comment(db: AsyncSession, comment_id: str):
        comment = await CommentService.get_comment_by_id(db, comment_id)
        if comment:
            await db.delete(comment)
            await db.commit()