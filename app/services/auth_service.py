# app/services/auth_service.py
from typing import Optional, Dict, Any
from bson import ObjectId

from app.db.mongo import get_master_db
from app.core.security import verify_password, create_access_token


class AuthService:
    def __init__(self):
        self.db = get_master_db()
        # collections
        self.admins = self.db["admin_users"]
        self.organizations = self.db["organizations"]

    async def find_admin_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        """
        Find an active admin by email across master admin_users collection.
        Note: admin email uniqueness is per-org in schema, but for login we search globally.
        """
        doc = await self.admins.find_one({"email": email, "is_active": True})
        return doc

    async def authenticate_admin(self, email: str, password: str) -> Optional[Dict[str, Any]]:
        """
        Verify credentials. If success, return admin doc with org metadata (org_id and collection_name).
        """
        admin = await self.find_admin_by_email(email)
        if not admin:
            return None

        hashed = admin.get("password_hash") or admin.get("password")  # compatibility if different field
        if not hashed:
            return None

        if not verify_password(password, hashed):
            return None

        # fetch organization metadata for token (optional safety)
        org_id = admin.get("org_id")
        org = await self.organizations.find_one({"_id": ObjectId(org_id)}) if org_id else None

        return {
            "admin": admin,
            "org": org,
        }

    async def create_token_for_admin(self, admin_doc: Dict[str, Any]) -> str:
        """
        Given a verified admin_doc, create a JWT token containing admin_id and org_id.
        """
        admin_id = str(admin_doc["_id"])
        org_id = str(admin_doc["org_id"]) if admin_doc.get("org_id") else ""
        token = create_access_token(subject=admin_id, org_id=org_id)
        return token
