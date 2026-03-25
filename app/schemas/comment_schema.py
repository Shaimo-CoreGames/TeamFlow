from pydantic import BaseModel, ConfigDict
from datetime import datetime
from typing import List, Optional

class CommentBase(BaseModel):
    content: str
    parent_id: Optional[str] = None

class CommentCreate(CommentBase):
    pass

class UserMinimal(BaseModel):
    id: str
    name: str
    model_config = ConfigDict(from_attributes=True)

class UserSnippet(BaseModel):
    name: str
    class Config:
        from_attributes = True

class CommentResponse(BaseModel):
    id: str
    content: str
    created_at: datetime
    project_id: str
    user: UserSnippet # Does this match the relationship name in your Comment Model?

    class Config:
        from_attributes = True