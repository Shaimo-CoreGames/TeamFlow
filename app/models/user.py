import uuid
from sqlalchemy import Column, String, Boolean, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base

class User(Base):
    __tablename__ = "users"

    # 1. CHANGE THIS TO STRING(36)
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    
    name = Column(String(255))
    email = Column(String(255), unique=True)
    hashed_password = Column(String(255))
    
    # Use server_default for more reliable SQLite timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    is_active = Column(Boolean, default=True)

    # Relationships
    comments = relationship("Comment", back_populates="author", cascade="all, delete-orphan")
    project_memberships = relationship("ProjectMember", back_populates="user")
    memberships = relationship(
        "Membership", 
        back_populates="user", 
        cascade="all, delete-orphan"
    )
    tasks_assigned = relationship("Task", back_populates="assignee")