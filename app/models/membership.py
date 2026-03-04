import uuid
import enum
from sqlalchemy import Column, String, ForeignKey, DateTime, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base

class UserRole(str, enum.Enum):
    ADMIN = "admin"
    MEMBER = "member"

class Membership(Base):
    __tablename__ = "memberships"

    # 1. Use String(36) and a lambda that returns a STRING
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    
    # 2. Match foreign keys to the String(36) format
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    organization_id = Column(String(36), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False)
    
    # 3. Using your UserRole enum properly
    role = Column(String(50), default=UserRole.MEMBER.value, nullable=False)
    joined_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    user = relationship("User", back_populates="memberships")
    organization = relationship("Organization", back_populates="memberships")