"""User creation and lookup."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth import hash_password, verify_password
from app.models.user import User

DEMO_EMAIL = "demo@studypath.app"
DEMO_PASSWORD = "demo-password"


def get_user_by_email(db: Session, email: str) -> User | None:
    return db.scalar(select(User).where(User.email == email.lower()))


def create_user(db: Session, email: str, password: str) -> User:
    user = User(email=email.lower(), password_hash=hash_password(password))
    db.add(user)
    db.flush()
    return user


def authenticate(db: Session, email: str, password: str) -> User | None:
    user = get_user_by_email(db, email)
    if user is None or not verify_password(password, user.password_hash):
        return None
    return user


def get_or_create_demo_user(db: Session) -> User:
    user = get_user_by_email(db, DEMO_EMAIL)
    if user is None:
        user = create_user(db, DEMO_EMAIL, DEMO_PASSWORD)
    return user
