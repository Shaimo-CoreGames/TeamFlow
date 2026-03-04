from sqlalchemy import String, ForeignKey
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

    # Relationships
    organization = relationship("Organization", back_populates="projects")
    tasks = relationship("Task", back_populates="project", cascade="all, delete")