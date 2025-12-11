# app/routes/org.py
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, EmailStr, Field

from app.services.org_service import OrganizationService

router = APIRouter(prefix="/org", tags=["org"])


class OrgCreateIn(BaseModel):
    organization_name: str = Field(..., description="Name of the organization")
    email: EmailStr
    password: str


class OrgCreateOut(BaseModel):
    organization: dict
    admin: dict


@router.post("/create", response_model=OrgCreateOut)
async def create_org(payload: OrgCreateIn):
    service = OrganizationService()
    try:
        result = await service.create_organization(
            organization_name=payload.organization_name,
            email=payload.email,
            password=payload.password,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    if not result or not result.get("organization"):
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to create organization")

    return result
