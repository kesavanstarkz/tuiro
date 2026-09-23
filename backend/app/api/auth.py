from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.dependencies import Principal, require_authenticated_user
from app.db import get_db
from app.schemas import LoginRequest, RefreshRequest, RegisterRequest, TokenPair, UserResponse
from app.services import auth

router = APIRouter()


@router.post("/register", response_model=TokenPair, status_code=201)
def register(request: RegisterRequest, db: Session = Depends(get_db)) -> TokenPair:
    return auth.register(db, request)


@router.post("/login", response_model=TokenPair)
def login(request: LoginRequest, db: Session = Depends(get_db)) -> TokenPair:
    return auth.login(db, request)


@router.post("/refresh", response_model=TokenPair)
def refresh(request: RefreshRequest, db: Session = Depends(get_db)) -> TokenPair:
    return auth.refresh(db, request.refresh_token)


@router.post("/logout", status_code=204)
def logout(request: RefreshRequest, db: Session = Depends(get_db)) -> None:
    auth.logout(db, request.refresh_token)


def me(principal: Principal = Depends(require_authenticated_user)) -> UserResponse:
    return UserResponse(id=principal.user.id, email=principal.user.email, display_name=principal.user.display_name, organization_id=principal.organization_id, role=principal.role)
