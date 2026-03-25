from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.membership import Membership
from app.schemas.membership_schema import MembershipCreate
from app.models.user import User


class MembershipService:

    @staticmethod
    async def add_member(
        db: AsyncSession,
        membership_data: MembershipCreate,
        user: User,
    ) -> Membership:

        membership = Membership(
            user_id=membership_data.user_id,
            organization_id=membership_data.organization_id,
            role=membership_data.role,
        )

        db.add(membership)
        await db.commit()
        await db.refresh(membership)

        return membership