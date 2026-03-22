from sqlalchemy import String, ForeignKey,DateTime,func
from sqlalchemy.orm import Mapped, mapped_column, relationship
import uuid
from app.database import Base

class Project(Base):
    __tablename__ = "projects"

    # Use str for SQLite compatibility with UUIDs
    # default=lambda: str(uuid.uuid4()) ensures every new project gets a unique ID
    id: Mapped[str] = mapped_column(
        String(36), 
        primary_key=True, 
        index=True, 
        default=lambda: str(uuid.uuid4())
    )

    name: Mapped[str] = mapped_column(String(255), nullable=False)

    # CHANGE THESE TO str TO MATCH YOUR UUIDs
    organization_id: Mapped[str] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
    )

    created_by: Mapped[str] = mapped_column(
        ForeignKey("users.id"),
        nullable=False,
    )
    created_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), 
        server_default=func.now()
    )
    
    description: Mapped[str | None] = mapped_column(String(1000), nullable=True)

    # Relationships
    organization = relationship("Organization", back_populates="projects")
    tasks = relationship("Task", back_populates="project", cascade="all, delete")
    members = relationship("ProjectMember", back_populates="project", cascade="all, delete-orphan")
    project_members = relationship("ProjectMember", back_populates="project", cascade="all, delete-orphan")