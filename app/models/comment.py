import uuid
from datetime import datetime
from sqlalchemy import Column, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship, backref
from app.database import Base

class Comment(Base):
    __tablename__ = "comments"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # --- CRITICAL CHANGES HERE ---
    # 1. Make task_id optional so project-level comments can exist
    task_id = Column(String(36), ForeignKey("tasks.id", ondelete="CASCADE"), nullable=True)
    
    # 2. Add project_id so we know which project the general chat belongs to
    project_id = Column(String(36), ForeignKey("projects.id", ondelete="CASCADE"), nullable=True)
    # -----------------------------

    user_id = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    parent_id = Column(String(36), ForeignKey("comments.id", ondelete="CASCADE"), nullable=True)

    # Relationships
    task = relationship("Task", back_populates="comments")
    project = relationship("Project") # Add this to link to Project model
    user = relationship("User", back_populates="comments")
    
    replies = relationship(
        "Comment", 
        backref=backref('parent', remote_side=[id]),
        cascade="all, delete-orphan"
    )