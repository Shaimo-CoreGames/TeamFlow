from datetime import datetime, timedelta

import bcrypt
from jose import jwt, JWTError
from sqlalchemy import select
from fastapi import HTTPException, status

from app.models.user import User
from app.core.config import settings



# ==============================
# Password Utilities
# ==============================

def hash_password(password: str) -> str:
    # 1. Encode to bytes
    # 2. Truncate to 72 bytes (Bcrypt limit)
    password_bytes = password.encode("utf-8")[:72]
    
    # 3. Generate salt and hash
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password_bytes, salt)
    
    # 4. Return as a string to store in DB
    return hashed.decode("utf-8")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    # 1. Encode plain password and truncate
    password_bytes = plain_password.encode("utf-8")[:72]
    
    # 2. Encode the stored hash string back to bytes for comparison
    hashed_bytes = hashed_password.encode("utf-8")
    
    # 3. Check compatibility
    return bcrypt.checkpw(password_bytes, hashed_bytes)
# ==============================
# JWT Utilities
# ==============================

def create_access_token(user_id: int) -> str:
    expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = {"sub": str(user_id), "exp": expire, "type": "access"}
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)

def create_refresh_token(user_id: int) -> str:
    expire = datetime.utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    payload = {"sub": str(user_id), "exp": expire, "type": "refresh"}
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)

def decode_token(token: str) -> dict:
    try:
        return jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token")