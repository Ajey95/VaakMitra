"""Session models."""
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class SessionCreate(BaseModel):
    """Session creation schema."""
    user_id: str
    lesson_id: int
    phoneme: str
    lesson_type: str


class SessionInDB(SessionCreate):
    """Session in database."""
    id: str = Field(alias="_id")
    created_at: datetime
    completed: bool = False
    
    class Config:
        populate_by_name = True
