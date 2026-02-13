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
# OAuth2PasswordBearer extracts token from Authorization: Bearer <token> header
# tokenUrl is only used for the OpenAPI docs, not for actual token extraction
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


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
    Proper JWT-based current user resolver.
    Uses the `sub` claim from the access token to look up the user by ID.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    print(f"=== AUTH DEBUG START ===")
    print(f"Token received (first 50 chars): {token[:50] if token else 'None'}...")
    print(f"Token length: {len(token) if token else 0}")
    print(f"Secret key length: {len(settings.secret_key)}")
    print(f"Secret key (first 30 chars): {settings.secret_key[:30]}...")
    print(f"Algorithm: {settings.algorithm}")
    
    try:
        # Decode the JWT token
        print(f"Attempting to decode token...")
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
        print(f"Token decoded successfully. Payload: {payload}")
        
        user_id = payload.get("sub")
        print(f"Extracted user_id (sub): {user_id}, type: {type(user_id)}")
        
        if user_id is None:
            print(f"ERROR: No 'sub' claim in token payload: {payload}")
            raise credentials_exception
        
        # Convert user_id to int (JWT may encode it as string)
        try:
            user_id = int(user_id)
            print(f"Converted user_id to int: {user_id}")
        except (TypeError, ValueError) as e:
            print(f"ERROR: Could not convert user_id to int: {user_id}, error: {e}")
            raise credentials_exception
        
        print(f"Looking up user with ID: {user_id}")
        
        # Query the user from database
        user = db.query(User).filter(User.id == user_id).first()
        
        if user is None:
            print(f"ERROR: User with ID {user_id} not found in database")
            # List all users for debugging
            all_users = db.query(User).all()
            print(f"Available user IDs in database: {[u.id for u in all_users]}")
            raise credentials_exception
        
        print(f"SUCCESS: Found user: {user.email} (ID: {user.id})")
        print(f"=== AUTH DEBUG END ===")
        return user
        
    except JWTError as e:
        print(f"ERROR: JWT decode error: {str(e)}")
        print(f"ERROR: Token received: {token[:50]}...")
        print(f"ERROR: Secret key length: {len(settings.secret_key)}")
        print(f"ERROR: Secret key (first 20 chars): {settings.secret_key[:20]}...")
        print(f"=== AUTH DEBUG END ===")
        raise credentials_exception
    except HTTPException:
        print(f"=== AUTH DEBUG END ===")
        raise
    except Exception as e:
        print(f"ERROR: Unexpected error in get_current_user: {str(e)}")
        import traceback
        traceback.print_exc()
        print(f"=== AUTH DEBUG END ===")
        raise credentials_exception
