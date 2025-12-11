# app/core/security.py
from datetime import datetime, timedelta
from typing import Optional, Dict, Any

from jose import jwt
from passlib.context import CryptContext

from app.core.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
ALGORITHM = settings.JWT_ALGORITHM
SECRET_KEY = settings.JWT_SECRET
ACCESS_TOKEN_EXPIRE_MINUTES = settings.ACCESS_TOKEN_EXPIRE_MINUTES


def hash_password(plain_password: str) -> str:
    return pwd_context.hash(plain_password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(subject: str, org_id: str, expires_delta: Optional[timedelta] = None) -> str:
    """
    Create a JWT token with 'sub' (admin id) and 'org' (organization id) in payload.
    """
    now = datetime.now()
    if expires_delta is None:
        expires_delta = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    expire = now + expires_delta
    to_encode: Dict[str, Any] = {
        "sub": subject,
        "org": org_id,
        "iat": int(now.timestamp()),
        "exp": int(expire.timestamp()),
    }
    token = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return token


def decode_access_token(token: str) -> Dict[str, Any]:
    """
    Decode JWT and return payload. Raises jose.JWTError on invalid token.
    """
    payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    return payload
