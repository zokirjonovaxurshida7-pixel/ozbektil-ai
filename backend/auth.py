"""
Autentifikatsiya: parol xeshlash (PBKDF2, tashqi kutubxonasiz) va JWT tokenlar.
"""

import datetime
import hashlib
import hmac
import os
from typing import Optional

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from db import get_db
from models import User

SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-key-CHANGE-THIS-IN-PRODUCTION")
JWT_ALGORITHM = "HS256"
TOKEN_TTL_HOURS = 24 * 7  # 7 kun

PBKDF2_ITERATIONS = 260_000

security = HTTPBearer(auto_error=False)


# ---------- Parol xeshlash ----------
def hash_password(password: str) -> str:
    salt = os.urandom(16)
    derived = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, PBKDF2_ITERATIONS)
    return f"{salt.hex()}${derived.hex()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        salt_hex, hash_hex = stored.split("$", 1)
    except ValueError:
        return False
    salt = bytes.fromhex(salt_hex)
    expected = bytes.fromhex(hash_hex)
    derived = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, PBKDF2_ITERATIONS)
    return hmac.compare_digest(derived, expected)


# ---------- JWT ----------
def create_access_token(user_id: int) -> str:
    payload = {
        "sub": str(user_id),
        "exp": datetime.datetime.utcnow() + datetime.timedelta(hours=TOKEN_TTL_HOURS),
        "iat": datetime.datetime.utcnow(),
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=JWT_ALGORITHM)


def decode_token(token: str) -> Optional[int]:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[JWT_ALGORITHM])
        return int(payload["sub"])
    except Exception:
        return None


# ---------- FastAPI dependency'lar ----------
def get_optional_user(
    creds: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: Session = Depends(get_db),
) -> Optional[User]:
    """Token bo'lsa foydalanuvchini qaytaradi, bo'lmasa None (xato chiqarmaydi)."""
    if not creds:
        return None
    user_id = decode_token(creds.credentials)
    if user_id is None:
        return None
    return db.query(User).filter(User.id == user_id).first()


def get_current_user(
    creds: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: Session = Depends(get_db),
) -> User:
    """Token majburiy — bo'lmasa yoki noto'g'ri bo'lsa 401 xatosi."""
    if not creds:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Tizimga kirish talab qilinadi.")
    user_id = decode_token(creds.credentials)
    if user_id is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Token yaroqsiz yoki muddati o'tgan.")
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Foydalanuvchi topilmadi.")
    return user


def get_current_admin(user: User = Depends(get_current_user)) -> User:
    if not user.is_admin:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Bu amal faqat administratorlar uchun.")
    return user
