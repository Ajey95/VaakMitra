"""User models and schemas."""
from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator
from typing import Literal, Optional
from datetime import datetime
from bson import ObjectId


class PyObjectId(ObjectId):
    """Custom ObjectId for Pydantic."""
    
    @classmethod
    def __get_validators__(cls):
        yield cls.validate
    
    @classmethod
    def validate(cls, v):
        if not ObjectId.is_valid(v):
            raise ValueError("Invalid ObjectId")
        return ObjectId(v)


class UserBase(BaseModel):
    """Base user schema."""
    model_config = ConfigDict(str_strip_whitespace=True)

    email: EmailStr
    full_name: str = Field(min_length=2, max_length=100)
    child_name: str = Field(min_length=2, max_length=100)
    child_age: int = Field(ge=4, le=12)
    language: Literal["Tamil", "Telugu", "English"] = "Tamil"

    @field_validator("email", mode="before")
    @classmethod
    def normalize_email(cls, value):
        return value.strip().lower() if isinstance(value, str) else value


class UserCreate(UserBase):
    """User creation schema."""
    password: str = Field(min_length=10, max_length=72)
    confirm_password: str = Field(min_length=10, max_length=72)

    @field_validator("password")
    @classmethod
    def validate_password_strength(cls, value: str) -> str:
        if not any(char.isupper() for char in value):
            raise ValueError("Password must contain an uppercase letter")
        if not any(char.islower() for char in value):
            raise ValueError("Password must contain a lowercase letter")
        if not any(char.isdigit() for char in value):
            raise ValueError("Password must contain a number")
        if not any(not char.isalnum() for char in value):
            raise ValueError("Password must contain a special character")
        return value


class UserInDB(UserBase):
    """User in database."""
    model_config = ConfigDict(
        str_strip_whitespace=True,
        populate_by_name=True,
        json_encoders={ObjectId: str},
    )

    id: str = Field(alias="_id")
    password_hash: str
    role: str = "user"
    created_at: datetime
    last_login: Optional[datetime] = None
    total_sessions: int = 0
    total_stars: int = 0
    
class UserResponse(UserBase):
    """User response schema."""
    model_config = ConfigDict(str_strip_whitespace=True, from_attributes=True)

    id: str
    role: str
    total_sessions: int
    total_stars: int
    created_at: datetime
    
class LoginRequest(BaseModel):
    """Login request schema."""
    email: EmailStr
    password: str

    @field_validator("email", mode="before")
    @classmethod
    def normalize_email(cls, value):
        return value.strip().lower() if isinstance(value, str) else value


class TokenData(BaseModel):
    """Token data schema."""
    email: Optional[str] = None
    role: Optional[str] = None
