# app/routes/auth.py
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, EmailStr

from app.services.auth_service import AuthService

router = APIRouter(prefix="/admin", tags=["auth"])


class AdminLoginIn(BaseModel):
    email: EmailStr
    password: str


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"


@router.post("/login", response_model=TokenOut)
async def admin_login(payload: AdminLoginIn):
    auth = AuthService()
    result = await auth.authenticate_admin(payload.email, payload.password)
    if not result:
        # do not reveal whether email exists
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    admin_doc = result["admin"]
    token = await auth.create_token_for_admin(admin_doc)

    return {"access_token": token, "token_type": "bearer"}
