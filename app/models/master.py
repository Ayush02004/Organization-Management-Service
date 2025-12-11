# app/models/master.py
from pydantic import BaseModel, Field
from typing import Optional, Literal
from datetime import datetime


class OrganizationCreate(BaseModel):
    # input for create endpoint (assignment originally used "organization_name", "email", "password")
    organization_name: str = Field(..., description="slug-safe organization name (unique)")
    display_name: str = Field(..., description="Human readable org name")
    owner_admin_email: Optional[str] = Field(None, description="email address of initial admin")


class OrganizationInDB(BaseModel):
    # representation of the document stored in Mongo (ids are strings here for API compatibility)
    id: Optional[str] = Field(None, alias="_id")
    name: str
    display_name: str
    collection_name: str
    owner_admin_id: Optional[str] = None
    status: Literal["active", "disabled", "deleted"] = "active"
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        allow_population_by_field_name = True
        orm_mode = True


class OrganizationOut(BaseModel):
    id: str = Field(..., alias="_id")
    name: str
    display_name: str
    collection_name: str
    owner_admin_id: Optional[str]
    status: str
    created_at: Optional[str]
    updated_at: Optional[str]

    class Config:
        allow_population_by_field_name = True
