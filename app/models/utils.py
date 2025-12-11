# app/models/utils.py
from typing import Any, Dict
from datetime import datetime
from bson import ObjectId


def is_objectid(v: Any) -> bool:
    try:
        return isinstance(v, ObjectId) or ObjectId(str(v)) is not None
    except Exception:
        return False


def objid_to_str(oid: ObjectId) -> str:
    return str(oid)


def str_to_objid(s: str) -> ObjectId:
    return ObjectId(s)


def serialize_datetime(dt: datetime) -> str:
    return dt.isoformat() if isinstance(dt, datetime) else dt


def serialize_mongo_doc(doc: Dict) -> Dict:
    """
    Convert a MongoDB document to a JSON-serializable dict:
    - Convert ObjectId fields to strings for keys named '_id' or ending with '_id'
    - Convert datetimes to ISO strings
    """
    out: Dict = {}
    for k, v in doc.items():
        if isinstance(v, ObjectId):
            out[k] = str(v)
        elif isinstance(v, datetime):
            out[k] = v.isoformat()
        elif isinstance(v, dict):
            out[k] = serialize_mongo_doc(v)
        elif isinstance(v, list):
            out[k] = [serialize_mongo_doc(i) if isinstance(i, dict) else (str(i) if isinstance(i, ObjectId) else i) for i in v]
        else:
            out[k] = v
    return out
