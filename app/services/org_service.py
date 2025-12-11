# app/services/org_service.py
import re
from datetime import datetime
from typing import Any, Dict, Optional

from bson import ObjectId
from pymongo.errors import CollectionInvalid

from app.core.security import hash_password, verify_password, decode_access_token
from app.db.mongo import get_master_db
from app.models.utils import serialize_mongo_doc


class OrganizationService:
    """
    Handles organization lifecycle operations (create, fetch, update, delete).
    For now create and read flows are implemented for the assignment.
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

    async def get_organization_by_name(self, organization_name: str) -> Optional[Dict[str, Any]]:
        """
        Fetch an organization document by its name (case-insensitive, normalized).
        Returns a serialized document or None if not found.
        """
        normalized = self._normalize_name(organization_name)
        if not normalized:
            return None

        org = await self.organizations.find_one({"name": normalized})
        if not org:
            return None

        owner_email: Optional[str] = None
        owner_admin_id = org.get("owner_admin_id")
        if owner_admin_id:
            admin = await self.admins.find_one({"_id": owner_admin_id})
            if admin:
                owner_email = admin.get("email")

        # hide internal identifiers and expose owner email instead
        org = dict(org)
        org.pop("_id", None)
        org.pop("owner_admin_id", None)
        org["owner_email"] = owner_email

        return serialize_mongo_doc(org)

    async def update_organization(self, organization_name: str, email: str, password: str) -> Dict[str, Any]:
        """
        Rename an organization and migrate its collection contents.
        Authenticates using admin email/password (no JWT as requested).
        """
        normalized_new = self._normalize_name(organization_name)
        if not normalized_new:
            raise ValueError("Organization name is empty after normalization")

        # authenticate admin
        admin = await self.admins.find_one({"email": email, "is_active": True})
        if not admin:
            raise ValueError("Invalid credentials")
        hashed = admin.get("password_hash") or admin.get("password")
        if not hashed or not verify_password(password, hashed):
            raise ValueError("Invalid credentials")

        # fetch current org
        org_id = admin.get("org_id")
        if not org_id:
            raise ValueError("Admin is not linked to the organization")
        org = await self.organizations.find_one({"_id": org_id})
        if not org:
            raise ValueError("Organization not found")

        # if name unchanged, just return current view
        current_name = org.get("name")
        if current_name == normalized_new:
            existing = await self.get_organization_by_name(organization_name)
            return {"organization": existing}

        # ensure new name does not clash
        existing = await self.organizations.find_one({"name": normalized_new})
        if existing:
            raise ValueError("Organization name already exists")

        old_collection = org.get("collection_name")
        if not old_collection:
            raise ValueError("Organization collection missing")
        new_collection = f"org_{normalized_new}"
        now = datetime.now()

        # create new collection and migrate documents
        try:
            await self.db.create_collection(new_collection)
        except CollectionInvalid:
            raise ValueError("Organization collection already exists")

        old_coll = self.db[old_collection]
        new_coll = self.db[new_collection]
        try:
            docs = await old_coll.find({}).to_list(length=None)
            if docs:
                await new_coll.insert_many(docs)
        except Exception:
            # rollback newly created collection if migration fails
            await new_coll.drop()
            raise

        # drop old collection after successful copy
        await old_coll.drop()

        # update organization metadata
        await self.organizations.update_one(
            {"_id": org_id},
            {
                "$set": {
                    "name": normalized_new,
                    "display_name": organization_name,
                    "collection_name": new_collection,
                    "updated_at": now,
                }
            },
        )

        updated = await self.get_organization_by_name(organization_name)
        return {"organization": updated}

    async def update_organization_better(
        self, current_name: str, new_name: str, email: str, password: str
    ) -> Dict[str, Any]:
        """
        Rename an organization from a provided current name to a new name.
        - Authenticates using admin email/password (no JWT).
        - Verifies the admin belongs to the target org.
        - Errors if current org missing or new name already exists.
        - Migrates data to the new org collection name.
        """
        normalized_current = self._normalize_name(current_name)
        normalized_new = self._normalize_name(new_name)
        if not normalized_current:
            raise ValueError("Current organization name is required")
        if not normalized_new:
            raise ValueError("New organization name is empty after normalization")

        # authenticate admin
        admin = await self.admins.find_one({"email": email, "is_active": True})
        if not admin:
            raise ValueError("Invalid credentials")
        hashed = admin.get("password_hash") or admin.get("password")
        if not hashed or not verify_password(password, hashed):
            raise ValueError("Invalid credentials")

        # fetch current org by name
        org = await self.organizations.find_one({"name": normalized_current})
        if not org:
            raise ValueError("Organization not found")

        # ensure admin belongs to this org
        if admin.get("org_id") != org.get("_id"):
            raise ValueError("Admin not authorized for this organization")

        # if same name, just return current view
        if normalized_current == normalized_new:
            existing = await self.get_organization_by_name(current_name)
            return {"organization": existing}

        # ensure new name does not clash
        existing = await self.organizations.find_one({"name": normalized_new})
        if existing:
            raise ValueError("Organization name already exists")

        old_collection = org.get("collection_name")
        if not old_collection:
            raise ValueError("Organization collection missing")
        new_collection = f"org_{normalized_new}"
        now = datetime.now()

        # create new collection and migrate documents
        try:
            await self.db.create_collection(new_collection)
        except CollectionInvalid:
            raise ValueError("Organization collection already exists")

        old_coll = self.db[old_collection]
        new_coll = self.db[new_collection]
        try:
            docs = await old_coll.find({}).to_list(length=None)
            if docs:
                await new_coll.insert_many(docs)
        except Exception:
            await new_coll.drop()
            raise

        # drop old collection after successful copy
        await old_coll.drop()

        # update organization metadata
        await self.organizations.update_one(
            {"_id": org["_id"]},
            {
                "$set": {
                    "name": normalized_new,
                    "display_name": new_name,
                    "collection_name": new_collection,
                    "updated_at": now,
                }
            },
        )

        updated = await self.get_organization_by_name(new_name)
        return {"organization": updated}

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

    async def delete_organization(self, organization_name: str, token: str) -> Dict[str, Any]:
        """
        Delete an organization and its collection. Auth via JWT bearer token.
        Token must contain admin_id (sub) and org_id (org) that match the target org.
        """
        if not token:
            raise ValueError("Missing token")

        bearer_prefix = "bearer "
        token_str = token.strip()
        if token_str.lower().startswith(bearer_prefix):
            token_str = token_str[len(bearer_prefix) :].strip()

        try:
            payload = decode_access_token(token_str)
        except Exception:
            raise ValueError("Invalid token")

        admin_id = payload.get("sub")
        org_id = payload.get("org")
        if not admin_id or not org_id:
            raise ValueError("Invalid token payload")

        try:
            admin_obj_id = ObjectId(admin_id)
            org_obj_id = ObjectId(org_id)
        except Exception:
            raise ValueError("Invalid token payload")

        admin = await self.admins.find_one({"_id": admin_obj_id, "is_active": True})
        if not admin:
            raise ValueError("Invalid credentials")
        if admin.get("org_id") != org_obj_id:
            raise ValueError("Admin not authorized for this organization")

        normalized = self._normalize_name(organization_name)
        if not normalized:
            raise ValueError("Organization name is required")

        org = await self.organizations.find_one({"name": normalized})
        if not org:
            raise ValueError("Organization not found")

        if org.get("_id") != org_obj_id:
            raise ValueError("Token does not match organization")

        collection_name = org.get("collection_name")
        if collection_name:
            await self.db[collection_name].drop()

        await self.admins.delete_many({"org_id": org_obj_id})
        await self.organizations.delete_one({"_id": org_obj_id})

        return {"deleted": True, "organization_name": org.get("display_name") or organization_name}
