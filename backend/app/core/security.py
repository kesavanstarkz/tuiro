from datetime import datetime, timedelta, timezone
from hashlib import sha256
import secrets

from jose import JWTError, jwt
from pwdlib import PasswordHash

from app.core.config import settings

password_hash = PasswordHash.recommended()


def hash_password(value: str) -> str:
    return password_hash.hash(value)


def verify_password(value: str, hashed: str) -> bool:
    return password_hash.verify(value, hashed)


def create_access_token(user_id: str, organization_id: str, role: str) -> str:
    expires = datetime.now(timezone.utc) + timedelta(minutes=settings.access_token_minutes)
    return jwt.encode({"sub": user_id, "org": organization_id, "role": role, "exp": expires, "type": "access"}, settings.jwt_secret, algorithm="HS256")


def create_refresh_token() -> tuple[str, str, datetime]:
    raw = secrets.token_urlsafe(48)
    expires = datetime.now(timezone.utc) + timedelta(days=settings.refresh_token_days)
    return raw, sha256(raw.encode()).hexdigest(), expires


def decode_access_token(token: str) -> dict:
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=["HS256"])
        if payload.get("type") != "access" or not payload.get("sub"):
            raise JWTError
        return payload
    except JWTError as exc:
        raise ValueError("Invalid access token") from exc


def hash_refresh_token(value: str) -> str:
    return sha256(value.encode()).hexdigest()
