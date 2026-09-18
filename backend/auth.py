import hashlib
import secrets 
from datetime import UTC, datetime, timedelta
from typing import Annotated
import jwt 
from jwt.exceptions import InvalidTokenError 
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from pwdlib import PasswordHash
from config import settings
from sqlalchemy import select 
from sqlalchemy.ext.asyncio import AsyncSession
from database import get_db
import models



password_hash = PasswordHash.recommended()

# Tells FastAPI to look for a "Bearer <token>" string inside the Authorization Header
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="users/token") # match endpoint api

def hash_password(password: str) -> str:
    return password_hash.hash(password)

def verify_password(plain_password:str, hashed_password:str) -> bool:
    return password_hash.verify(plain_password, hashed_password)

def generate_reset_token() -> str:
    return secrets.token_urlsafe(32)  # Generates a secure random token

def hash_reset_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()

def create_access_token(data:dict, expires_delta:timedelta) -> str:
    """Create a JWT access token here"""
    to_endcode = data.copy()
    if expires_delta:
        expire = datetime.now(UTC) + expires_delta
    else: 
        expire = datetime.now(UTC) + timedelta(minutes=settings.access_token_expire_minutes,)

    to_endcode.update({"exp": expire})
    encoded_jwt = jwt.encode(
        to_endcode,
        settings.secret_key.get_secret_value(),
        algorithm=settings.algorithm,
    )
    return encoded_jwt

def verify_access_token(token:str) -> str | None:
    """Verify jwt access token and return the subject (user id) if valid"""
    try: 
        payload = jwt.decode(
            token,
            settings.secret_key.get_secret_value(),
            algorithms=[settings.algorithm],
            options={"require": ["exp", "sub"]}
        )
    except jwt.InvalidTokenError:
        return None
    else: 
        return payload.get("sub")


async def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    db: Annotated[AsyncSession, Depends(get_db)]
) -> models.User: 

    unauthorized_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired token",
        headers={"WWW-Authenticate": "Bearer"},
    )

    user_id = verify_access_token(token)
    if user_id is None: 
        raise unauthorized_exception

    try:
        user_id_int = int(user_id)
    except (TypeError, ValueError):
        raise unauthorized_exception

    result = await db.execute(
        select(models.User).where(models.User.id == user_id_int)
    )
    user = result.scalars().first()
    if not user:
        raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="User not found",
        headers={"WWW-Authenticate": "Bearer"},
    )
    return user

# convenient alias - usage 
CurrentUser = Annotated[models.User, Depends(get_current_user)]