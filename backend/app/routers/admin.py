from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from app.database import get_db
from app.models import User
from app.schemas import UserResponse
from app.auth import get_current_user

router = APIRouter()


@router.get("/users", response_model=List[UserResponse])
async def list_all_users(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List all users (for debugging - requires authentication)"""
    users = db.query(User).all()
    return users


@router.get("/users/debug")
async def debug_users(db: Session = Depends(get_db)):
    """Debug endpoint to see all users without authentication"""
    users = db.query(User).all()
    return {
        "total_users": len(users),
        "users": [
            {
                "id": u.id,
                "email": u.email,
                "name": u.name,
                "created_at": str(u.created_at),
                "has_password_hash": bool(u.password_hash),
            }
            for u in users
        ]
    }
