#!/usr/bin/env python3
"""Simple script to check registered users in the database"""
from app.database import SessionLocal
from app.models import User

def check_users():
    db = SessionLocal()
    try:
        users = db.query(User).all()
        print(f"\n{'='*60}")
        print(f"Total Registered Users: {len(users)}")
        print(f"{'='*60}\n")
        
        if len(users) == 0:
            print("No users found in the database.")
        else:
            for i, user in enumerate(users, 1):
                print(f"User {i}:")
                print(f"  ID: {user.id}")
                print(f"  Email: {user.email}")
                print(f"  Name: {user.name}")
                print(f"  Created: {user.created_at}")
                print(f"  Has Password: {'Yes' if user.password_hash else 'No'}")
                print()
        
        print(f"{'='*60}\n")
    finally:
        db.close()

if __name__ == "__main__":
    check_users()
