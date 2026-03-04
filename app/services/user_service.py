from typing import List, Optional

from sqlalchemy import select, update, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.schemas.user_schema import UserUpdate
from app.core.security import hash_password


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