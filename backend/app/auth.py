# backend/app/auth.py
"""
Authentication helpers for the MathSight app.

Provides:
 - get_password_hash(password) -> str
 - verify_password(plain_password, hashed_password) -> bool
 - create_access_token(data, expires_delta=None) -> str
 - authenticate_user(db, username_or_email, password) -> user model or None

This uses a SHA-256 hex pre-hash to avoid bcrypt 72-byte limit, then uses passlib CryptContext
(bcrypt_sha256 preferred) to store and verify hashes.
"""

import os
import hashlib
from datetime import datetime, timedelta
from typing import Optional

from passlib.context import CryptContext
from jose import jwt
from sqlalchemy.orm import Session

from . import models

# CryptContext: prefer bcrypt_sha256 (pre-hashes with SHA256 internally),
# but include bcrypt for compatibility.
pwd_context = CryptContext(schemes=["bcrypt_sha256", "bcrypt"], deprecated="auto", default="bcrypt_sha256")

# JWT config: use env var if present, otherwise fallback to a placeholder (change for production)
SECRET_KEY = os.getenv("SECRET_KEY", "CHANGE_ME_TO_A_SECURE_RANDOM_KEY")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 60 * 24))


def _sha256_hex(s: str) -> str:
    """Return SHA-256 hex digest of the given string (deterministic, 64 hex chars)."""
    if isinstance(s, bytes):
        b = s
    else:
        b = s.encode("utf-8", errors="surrogatepass")
    return hashlib.sha256(b).hexdigest()


def get_password_hash(password: str) -> str:
    """
    Hash a password for storage.
    We first compute the SHA-256 hex digest then call passlib to hash that digest.
    """
    digest = _sha256_hex(password)
    return pwd_context.hash(digest)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a plaintext password against a stored hash.
    Compute SHA-256 digest of the plain password and verify against stored.
    """
    digest = _sha256_hex(plain_password)
    try:
        return pwd_context.verify(digest, hashed_password)
    except Exception:
        # Any exception -> treat as verification failure
        return False


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """
    Create a signed JWT access token. 'data' should contain identifying fields (e.g. {"sub": username}).
    """
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded


def authenticate_user(db: Session, username_or_email: str, password: str):
    """
    Find user by username OR email and verify password.
    Returns the user model object on success, or None on failure.
    """
    # Query by username or email (case-sensitive as stored)
    user = (
        db.query(models.User)
        .filter((models.User.username == username_or_email) | (models.User.email == username_or_email))
        .first()
    )
    if not user:
        return None
    if not verify_password(password, user.hashed_password):
        return None
    return user
