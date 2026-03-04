from datetime import datetime
import uuid
from sqlalchemy import Column, ForeignKey, DateTime, Text, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

class Comment(Base):
    __tablename__ = "comments"

    # Use UUID for consistency with your other models
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )

    # Use UUID for the task reference if your Tasks use UUIDs
    task_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), 
        ForeignKey("tasks.id", ondelete="CASCADE"),
        nullable=False,
    )

    # CONSOLIDATED: Only one reference to the User table
    author_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), 
        ForeignKey("users.id", ondelete="CASCADE"), 
        nullable=False
    )

    content: Mapped[str] = mapped_column(Text, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
    )

    # Relationships
    task = relationship("Task", back_populates="comments")
    
    # This "author" relationship now points clearly to the author_id column
    author = relationship("User", back_populates="comments")