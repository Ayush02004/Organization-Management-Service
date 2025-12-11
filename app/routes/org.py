# app/routes/org.py
from fastapi import APIRouter, Body, HTTPException, Query, status
from fastapi import Header
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


class OrgGetOut(BaseModel):
    organization: dict


class OrgUpdateIn(BaseModel):
    organization_name: str = Field(..., description="New name for the organization")
    email: EmailStr
    password: str


class OrgUpdateBetterIn(BaseModel):
    current_organization_name: str = Field(..., description="Existing organization name")
    new_organization_name: str = Field(..., description="New organization name")
    email: EmailStr
    password: str


class OrgDeleteOut(BaseModel):
    deleted: bool
    organization_name: str


class OrgDeleteIn(BaseModel):
    organization_name: str = Field(..., description="Name of the organization to delete")


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


@router.get("/get", response_model=OrgGetOut)
async def get_org(organization_name: str = Query(..., description="Name of the organization")):
    service = OrganizationService()
    org = await service.get_organization_by_name(organization_name)
    if not org:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Organization not found")

    return {"organization": org}


@router.put("/update", response_model=OrgGetOut)
async def update_org(payload: OrgUpdateIn):
    service = OrganizationService()
    try:
        result = await service.update_organization(
            organization_name=payload.organization_name,
            email=payload.email,
            password=payload.password,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    if not result or not result.get("organization"):
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to update organization")

    return result


@router.put("/update_better", response_model=OrgGetOut)
async def update_org_better(payload: OrgUpdateBetterIn):
    service = OrganizationService()
    try:
        result = await service.update_organization_better(
            current_name=payload.current_organization_name,
            new_name=payload.new_organization_name,
            email=payload.email,
            password=payload.password,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    if not result or not result.get("organization"):
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to update organization")

    return result


@router.delete("/delete", response_model=OrgDeleteOut)
async def delete_org(
    organization_name: str | None = Query(None, description="Name of the organization to delete (optional if provided in body)"),
    authorization: str = Header(None, alias="Authorization"),
    payload: OrgDeleteIn | None = Body(None),
):
    service = OrganizationService()
    org_name = payload.organization_name if payload and payload.organization_name else organization_name
    if not org_name:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="organization_name is required")
    try:
        result = await service.delete_organization(organization_name=org_name, token=authorization)
    except ValueError as e:
        detail = str(e)
        if detail.lower().startswith("invalid token") or "token" in detail.lower() or "credentials" in detail.lower():
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=detail)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=detail)

    if not result or not result.get("deleted"):
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to delete organization")

    return result
