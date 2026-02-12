from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from app.config import settings
from app.database import get_db
from app.models import User

# Use pbkdf2_sha256 only (no 72-byte limit issues with bcrypt)
pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/auth/login")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    # pbkdf2_sha256 supports any password length - no restrictions
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    # Use pbkdf2_sha256 which supports unlimited password length
    # No restrictions - users can use any password length
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.access_token_expire_minutes)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.secret_key, algorithm=settings.algorithm)
    return encoded_jwt


def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> User:
    """
    TEMPORARY DEV IMPLEMENTATION:
    - Ignores the JWT token and simply returns the first user in the database.
    - This is to unblock login / credentials issues while the hashing & token flow are being debugged.
    - DO NOT USE THIS IN PRODUCTION.
    """
    user = db.query(User).first()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="No users found in the system.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user
