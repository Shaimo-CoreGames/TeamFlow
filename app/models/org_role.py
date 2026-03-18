# app/models/organization_role.py
import uuid
from sqlalchemy import String, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base

class OrganizationRole(Base):
    __tablename__ = "organization_roles"

    id: Mapped[str] = mapped_column(
        String(36), 
        primary_key=True, 
        default=lambda: str(uuid.uuid4())
    )
    organization_id: Mapped[str] = mapped_column(
        String(36), 
        ForeignKey("organizations.id", ondelete="CASCADE"), 
        nullable=False
    )
    role_name: Mapped[str] = mapped_column(String(50), nullable=False)

    # Relationship back to the Organization
    organization = relationship("Organization", back_populates="custom_roles")