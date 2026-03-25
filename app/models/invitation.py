import uuid
from sqlalchemy import Column, String, ForeignKey, DateTime
from sqlalchemy.sql import func
from app.database import Base

class Invitation(Base):
    __tablename__ = "invitations"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    organization_id = Column(String(36), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False)
    email = Column(String(255), nullable=False) # The email of the person being invited
    role = Column(String(50), default="member")
    status = Column(String(20), default="pending") # pending, accepted, declined
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    invited_by = Column(String, ForeignKey("users.id"), nullable=True)