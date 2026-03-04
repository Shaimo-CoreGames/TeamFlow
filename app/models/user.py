import uuid
from sqlalchemy import Column, String, Boolean,DateTime
from datetime import datetime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String)
    email = Column(String, unique=True)
    hashed_password = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow) # <--- Must exist!
    is_active = Column(Boolean, default=True)

    # Handshake Part 3: CRITICAL FIX
    # 1. First arg must be "Membership" (The class name)
    # 2. back_populates must be "user" (The variable name in Membership)
    # 3. DO NOT use secondary="user_organizations" here anymore
    comments = relationship("Comment", back_populates="author", cascade="all, delete-orphan")
    memberships = relationship(
        "Membership", 
        back_populates="user", 
        cascade="all, delete-orphan"
    )
    tasks_assigned = relationship("Task", back_populates="assignee")