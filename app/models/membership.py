import uuid
import enum
from sqlalchemy import Column, String, ForeignKey, DateTime, Enum
from sqlalchemy.orm import Mapped, mapped_column, mapped_column, relationship
from sqlalchemy.sql import func
from app.database import Base

class Membership(Base):
    __tablename__ = "memberships"
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    # Ensure this matches what your Service/Queries use
    organization_id = Column(String(36), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False) 
    role: Mapped[str] = mapped_column(String(50), default="member")
    
    user = relationship("User", back_populates="memberships")
    organization = relationship("Organization", back_populates="memberships")

class ProjectMember(Base):
    __tablename__ = "project_members"

    # Use String(36) to match your UUID-as-string strategy
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    
    project_id = Column(String(36), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    
    # Role can be 'admin' or 'member'
    role = Column(String(50), default="member", nullable=False)
    
    # Status for your invitation system: 'pending', 'accepted', 'declined'
    status = Column(String(20), default="pending", nullable=False)
    
    joined_at = Column(DateTime(timezone=True), server_default=func.now())
     
    user = relationship("User", back_populates="project_memberships")
    project = relationship("Project", back_populates="members")


