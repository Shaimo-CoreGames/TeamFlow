from typing import List, Optional

from sqlalchemy import select,or_, update, delete
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.user import User
from app.schemas.user_schema import UserUpdate
from app.core.security import hash_password
from app.models.project import Project
from app.models.membership import ProjectMember

class UserService:

    # -----------------------------------------------------
    # Get All Users
    # -----------------------------------------------------
    @staticmethod
    async def get_all_users(db: AsyncSession) -> List[User]:
        result = await db.execute(select(User))
        return result.scalars().all()

    # -----------------------------------------------------
    # Get User By ID
    # -----------------------------------------------------
    @staticmethod
    async def get_user_by_id(
        db: AsyncSession,
        user_id: int,
    ) -> Optional[User]:

        result = await db.execute(
            select(User).where(User.id == user_id)
        )
        return result.scalar_one_or_none()

    # -----------------------------------------------------
    # Get User By Email
    # -----------------------------------------------------
    @staticmethod
    async def get_user_by_email(
        db: AsyncSession,
        email: str,
    ) -> Optional[User]:

        result = await db.execute(
            select(User).where(User.email == email)
        )
        return result.scalar_one_or_none()

    # -----------------------------------------------------
    # Update User
    # -----------------------------------------------------
    @staticmethod
    async def update_user(
        db: AsyncSession,
        user_id: int,
        user_data: UserUpdate,
    ) -> Optional[User]:

        result = await db.execute(
            select(User).where(User.id == user_id)
        )
        user = result.scalar_one_or_none()

        if not user:
            return None

        update_data = user_data.model_dump(exclude_unset=True)

        # If password is being updated → hash it
        if "password" in update_data:
            update_data["hashed_password"] = hash_password(
                update_data.pop("password")
            )

        for key, value in update_data.items():
            setattr(user, key, value)

        await db.commit()
        await db.refresh(user)

        return user

    # -----------------------------------------------------
    # Delete User
    # -----------------------------------------------------
    @staticmethod
    async def delete_user(
        db: AsyncSession,
        user_id: int,
    ) -> bool:

        result = await db.execute(
            select(User).where(User.id == user_id)
        )
        user = result.scalar_one_or_none()

        if not user:
            return False

        await db.delete(user)
        await db.commit()

        return True
    
    @staticmethod
    async def search_users(db: AsyncSession, query: str):
        # This looks for partial matches in both name and email
        stmt = select(User).where(
            or_(
                User.name.ilike(f"%{query}%"),
                User.email.ilike(f"%{query}%")
            )
        ).limit(10) # Limit results for performance
        
        result = await db.execute(stmt)
        return result.scalars().all()

    @staticmethod
    async def get_user_invitations(db: AsyncSession, user_id: str):
        # We select the project name so the user knows what they are joining
        stmt = (
            select(Project.id, Project.name)
            .join(ProjectMember, Project.id == ProjectMember.project_id)
            .where(
                ProjectMember.user_id == user_id,
                ProjectMember.status == "pending"
            )
        )
        result = await db.execute(stmt)
        # Convert rows to a list of dictionaries for the frontend
        return [{"project_id": row.id, "project_name": row.name} for row in result]