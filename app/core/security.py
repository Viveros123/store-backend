"""Hasheo de contraseñas (bcrypt) y tokens de acceso (JWT)."""

from datetime import datetime, timedelta, timezone

import bcrypt
import jwt

from app.core.config import settings

# bcrypt trabaja sobre bytes y tiene un límite de 72 bytes en la contraseña.
_BCRYPT_MAX_BYTES = 72


def hash_password(plain: str) -> str:
    data = plain.encode("utf-8")[:_BCRYPT_MAX_BYTES]
    return bcrypt.hashpw(data, bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    data = plain.encode("utf-8")[:_BCRYPT_MAX_BYTES]
    try:
        return bcrypt.checkpw(data, hashed.encode("utf-8"))
    except ValueError:
        return False


def create_access_token(subject: str | int, extra: dict | None = None) -> str:
    now = datetime.now(timezone.utc)
    payload: dict = {
        "sub": str(subject),
        "iat": now,
        "exp": now + timedelta(minutes=settings.access_token_expire_minutes),
    }
    if extra:
        payload.update(extra)
    return jwt.encode(payload, settings.secret_key, algorithm=settings.algorithm)


def decode_access_token(token: str) -> dict:
    return jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
