from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth import CurrentUser, create_access_token
from app.database import get_db
from app.models.user import User
from app.schemas.auth import Credentials, TokenResponse, UserOut
from app.services.users import authenticate, create_user, get_user_by_email

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/signup", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
def signup(credentials: Credentials, db: Session = Depends(get_db)) -> TokenResponse:
    if get_user_by_email(db, credentials.email) is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, "An account with that email already exists")
    user = create_user(db, credentials.email, credentials.password)
    db.commit()
    return _token_for(user)


@router.post("/login", response_model=TokenResponse)
def login(credentials: Credentials, db: Session = Depends(get_db)) -> TokenResponse:
    user = authenticate(db, credentials.email, credentials.password)
    if user is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Incorrect email or password")
    return _token_for(user)


@router.get("/me", response_model=UserOut)
def me(user: CurrentUser) -> UserOut:
    return UserOut.model_validate(user)


def _token_for(user: User) -> TokenResponse:
    return TokenResponse(
        access_token=create_access_token(user.id),
        user=UserOut.model_validate(user),
    )
