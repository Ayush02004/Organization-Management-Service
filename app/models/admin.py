# app/models/admin.py
from pydantic import BaseModel, EmailStr, Field
from typing import Optional, Literal
from datetime import datetime


class AdminCreate(BaseModel):
    org_id: Optional[str] = Field(None, description="Organization id (string). If None, assigned after org created.")
    email: EmailStr
    password: str   # plain password in request (remember to hash before saving)
    role: Literal["admin", "superadmin", "user"] = "admin"


class AdminInDB(BaseModel):
    id: Optional[str] = Field(None, alias="_id")
    org_id: str
    email: EmailStr
    password_hash: str
    role: Literal["admin", "superadmin", "user"] = "admin"
    is_active: bool = True
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        allow_population_by_field_name = True
        orm_mode = True


class AdminOut(BaseModel):
    id: str = Field(..., alias="_id")
    org_id: str
    email: EmailStr
    role: str
    is_active: bool
    created_at: Optional[str]
    updated_at: Optional[str]

    class Config:
        allow_population_by_field_name = True
