# app/core/deps.py
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from typing import Dict, Any
from bson import ObjectId

from jose import JWTError, ExpiredSignatureError

from app.core.security import decode_access_token
from app.db.mongo import get_master_db

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/admin/login")


async def get_current_admin(token: str = Depends(oauth2_scheme)) -> Dict[str, Any]:
    """
    Decode token and fetch admin from DB. Raises HTTPException 401 on invalid/expired token.
    Returns admin document (dict) and adds 'org' (organization doc) under the key 'org_doc' optionally.
    """
    try:
        payload = decode_access_token(token)
    except ExpiredSignatureError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token expired")
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

    admin_id = payload.get("sub")
    org_id = payload.get("org")

    if not admin_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token payload")

    db = get_master_db()
    try:
        admin_doc = await db["admin_users"].find_one({"_id": ObjectId(admin_id), "is_active": True})
    except Exception:
        admin_doc = None

    if not admin_doc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Admin not found or inactive")

    org_doc = None
    if org_id:
        try:
            org_doc = await db["organizations"].find_one({"_id": ObjectId(org_id)})
        except Exception:
            org_doc = None

    # attach org_doc if useful
    admin_doc["org_doc"] = org_doc
    return admin_doc
