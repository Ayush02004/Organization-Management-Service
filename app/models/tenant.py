# app/models/tenant.py
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class TenantBaseDoc(BaseModel):
    id: Optional[str] = Field(None, alias="_id")
    created_at: Optional[datetime] = None
    created_by_admin_id: Optional[str] = None

    class Config:
        allow_population_by_field_name = True
