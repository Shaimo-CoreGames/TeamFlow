from sqlalchemy import Table, Column, String, ForeignKey
from app.database import Base

project_members = Table(
    "project_members",
    Base.metadata,
    Column("user_id", String(36), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
    Column("project_id", String(36), ForeignKey("projects.id", ondelete="CASCADE"), primary_key=True),
)