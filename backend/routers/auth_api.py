from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.auth import create_access_token, get_current_user, verify_password
from backend.db import get_db
from backend.models import User
from backend.schemas import DemoUserResponse, LoginRequest, LoginResponse, UserResponse


router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/login", response_model=LoginResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)) -> LoginResponse:
    user = db.query(User).filter(User.username == payload.username).first()
    if user is None or not user.active or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid username or password")
    return LoginResponse(access_token=create_access_token(user), user=user)


@router.get("/me", response_model=UserResponse)
def me(current_user: User = Depends(get_current_user)) -> User:
    return current_user


@router.get("/demo-users", response_model=list[DemoUserResponse])
def demo_users() -> list[DemoUserResponse]:
    return [
        DemoUserResponse(
            username="admin",
            display_name="Demo Admin",
            role="admin",
            password_hint="demo password: admin-demo-password",
        ),
        DemoUserResponse(
            username="manager",
            display_name="Demo Manager",
            role="manager",
            password_hint="demo password: manager-demo-password",
        ),
        DemoUserResponse(
            username="viewer",
            display_name="Demo Viewer",
            role="viewer",
            password_hint="demo password: viewer-demo-password",
        ),
    ]
