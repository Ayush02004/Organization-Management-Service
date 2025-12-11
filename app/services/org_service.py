# app/services/org_service.py
import re
from datetime import datetime
from typing import Any, Dict, Optional

from bson import ObjectId
from pymongo.errors import CollectionInvalid

from app.core.security import hash_password
from app.db.mongo import get_master_db
from app.models.utils import serialize_mongo_doc


class OrganizationService:
    """
    Handles organization lifecycle operations (create, fetch, update, delete).
    Only the create flow is implemented for the current assignment.
    """

    def __init__(self) -> None:
        self.db = get_master_db()
        self.organizations = self.db["organizations"]
        self.admins = self.db["admin_users"]

    @staticmethod
    def _normalize_name(name: str) -> str:
        """Turn organization name into a slug usable in collection names."""
        slug = name.strip().lower()
        slug = re.sub(r"[^a-z0-9]+", "_", slug).strip("_")
        return slug

    async def create_organization(self, organization_name: str, email: str, password: str) -> Dict[str, Any]:
        """
        Create organization metadata + initial admin, and create the org collection.
        Returns both created documents.
        Raises ValueError on duplicates or bad input.
        """
        normalized = self._normalize_name(organization_name)
        if not normalized:
            raise ValueError("Organization name is empty after normalization")

        # ensure org uniqueness
        existing = await self.organizations.find_one({"name": normalized})
        if existing:
            raise ValueError("Organization name already exists")

        collection_name = f"org_{normalized}"
        now = datetime.now()

        # create org collection upfront; if it somehow exists, fail to avoid collisions
        try:
            await self.db.create_collection(collection_name)
        except CollectionInvalid:
            # motor raises CollectionInvalid if it already exists
            raise ValueError("Organization collection already exists")

        org_doc = {
            "name": normalized,
            "display_name": organization_name,
            "collection_name": collection_name,
            "owner_admin_id": None,
            "status": "active",
            "created_at": now,
            "updated_at": now,
        }

        org_res = await self.organizations.insert_one(org_doc)
        org_id = org_res.inserted_id

        admin_doc = {
            "org_id": org_id,
            "email": email,
            "password_hash": hash_password(password),
            "role": "admin",
            "is_active": True,
            "created_at": now,
            "updated_at": now,
        }
        admin_res = await self.admins.insert_one(admin_doc)
        admin_id = admin_res.inserted_id

        # link owner admin back to org
        await self.organizations.update_one({"_id": org_id}, {"$set": {"owner_admin_id": admin_id}})

        # fetch fresh docs for response
        org = await self.organizations.find_one({"_id": org_id})
        admin = await self.admins.find_one({"_id": admin_id})

        return {
            "organization": serialize_mongo_doc(org) if org else None,
            "admin": serialize_mongo_doc(admin) if admin else None,
        }
