from datetime import datetime
from sqlalchemy import String, ForeignKey, DateTime, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
import uuid
from app.database import Base

class Task(Base):
    __tablename__ = "tasks"

    # ID using UUID string to match your frontend logic
    id: Mapped[str] = mapped_column(
        String(36), 
        primary_key=True, 
        index=True, 
        default=lambda: str(uuid.uuid4())
    )

    title: Mapped[str] = mapped_column(String(255), nullable=False)
    
    # --- ADDED MISSING COLUMNS START ---
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    
    priority: Mapped[str] = mapped_column(
        String(50), 
        default="Medium", 
        server_default="Medium"
    )
    
    status: Mapped[str] = mapped_column(
        String(50), 
        default="Pending", 
        server_default="Pending"
    )
    
    due_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime, 
        default=datetime.utcnow, 
        server_default="now()"
    )
    # --- ADDED MISSING COLUMNS END ---

    # Foreign Keys
    project_id: Mapped[str] = mapped_column(
        String(36), 
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
    )

    assigned_to: Mapped[str | None] = mapped_column(
        String(36), 
        ForeignKey("users.id"),
        nullable=True,
    )

    # Relationships
    project = relationship("Project", back_populates="tasks")
    assignee = relationship("User", back_populates="tasks_assigned")
    comments = relationship("Comment", back_populates="task", cascade="all, delete")