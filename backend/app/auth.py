import os
from datetime import datetime, timedelta
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict
from .database import get_db, User

# Security constants
SECRET_KEY = os.environ.get("JWT_SECRET_KEY", os.urandom(32).hex())
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 # 24 hours

pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

# IN-MEMORY SESSION CACHE
# Stores the decrypted UMKs for active sessions.
# This prevents the decrypted master key from ever being written to disk.
# Format: { "user_id": umk_bytes }
active_sessions: Dict[int, bytes] = {}

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: timedelta | None = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

async def get_current_user(token: str = Depends(oauth2_scheme), db: AsyncSession = Depends(get_db)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    result = await db.execute(select(User).filter(User.username == username))
    user = result.scalars().first()
    if user is None:
        raise credentials_exception
    return user

async def get_active_umk(current_user: User = Depends(get_current_user)):
    """Retrieve the decrypted UMK from memory. Ensures the session is active."""
    umk = active_sessions.get(current_user.id)
    if not umk:
        raise HTTPException(status_code=401, detail="Session expired or UMK not in memory. Please log in again.")
    return umk
