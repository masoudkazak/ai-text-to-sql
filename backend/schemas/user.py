from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from models.enums import UserRole


class UserCreate(BaseModel):
    name: str
    email: EmailStr
    password: str
    role: UserRole
    allowed_tables: list[str] = Field(default_factory=list)
    daily_query_limit: int = 100


class UserRegister(BaseModel):
    name: str
    email: EmailStr
    password: str


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    email: EmailStr
    role: UserRole
    allowed_tables: list[str]
    daily_query_limit: int
    queries_today: int
    is_active: bool
    created_at: datetime


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class UsageSummaryOut(BaseModel):
    global_daily_limit: int
    global_used: int
    global_remaining: int
    user_daily_limit: int
    user_used: int
    user_remaining: int
    available_tables: list[str]
