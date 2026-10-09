from __future__ import annotations

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.dependencies import Principal, require_authenticated_user, require_roles
from app.db import get_db
from app.models import InviteCode
from app.schemas import LoginRequest, RefreshRequest, RegisterRequest, SwitchOrganizationRequest, TokenPair, UserResponse
from app.services import auth, invite_reset

router = APIRouter()


from app.core.rate_limit import check_rate_limit


@router.post("/register", response_model=TokenPair, status_code=201)
def register(request: RegisterRequest, db: Session = Depends(get_db)) -> TokenPair:
    return auth.register(db, request)


@router.post("/login", response_model=TokenPair)
def login(request: LoginRequest, db: Session = Depends(get_db)) -> TokenPair:
    check_rate_limit(f"login_{request.email.lower()}", max_attempts=15, window_seconds=60)
    return auth.login(db, request)


@router.post("/refresh", response_model=TokenPair)
def refresh(request: RefreshRequest, db: Session = Depends(get_db)) -> TokenPair:
    return auth.refresh(db, request.refresh_token)


@router.post("/switch-organization", response_model=TokenPair)
def switch_organization(
    request: SwitchOrganizationRequest,
    principal: Principal = Depends(require_authenticated_user),
    db: Session = Depends(get_db),
) -> TokenPair:
    return auth.switch_organization(db, principal.user.id, request)


@router.post("/logout", status_code=204)
def logout(request: RefreshRequest, db: Session = Depends(get_db)) -> None:
    auth.logout(db, request.refresh_token)


def me(principal: Principal = Depends(require_authenticated_user)) -> UserResponse:
    return UserResponse(id=principal.user.id, email=principal.user.email, display_name=principal.user.display_name, organization_id=principal.organization_id, role=principal.role)


# ---------------------------------------------------------------------------
# F-4: Invite flow
# ---------------------------------------------------------------------------

class CreateInviteRequest(BaseModel):
    role: str = Field(pattern="^(ADMIN|TEACHER|PARENT|STUDENT)$")
    email: Optional[str] = None
    phone: Optional[str] = None
    linked_student_id: Optional[UUID] = None
    expires_hours: int = Field(default=72, ge=1, le=720)


class AcceptInviteRequest(BaseModel):
    code: str = Field(min_length=1)
    display_name: str = Field(min_length=1, max_length=160)
    password: str = Field(min_length=8)
    email: Optional[str] = None


@router.post("/invites", status_code=201)
def create_invite(
    request: CreateInviteRequest,
    principal: Principal = Depends(require_roles("OWNER", "ADMIN")),
    db: Session = Depends(get_db),
):
    invite = invite_reset.create_invite(
        db,
        organization_id=principal.organization_id,
        created_by_user_id=principal.user.id,
        role=request.role,
        email=request.email,
        phone=request.phone,
        linked_student_id=request.linked_student_id,
        expires_hours=request.expires_hours,
    )
    return {
        "id": invite.id,
        "code": invite.code,
        "role": invite.role,
        "email": invite.email,
        "phone": invite.phone,
        "linked_student_id": invite.linked_student_id,
        "expires_at": invite.expires_at,
        "created_at": invite.created_at,
    }


@router.post("/invites/accept", response_model=TokenPair)
def accept_invite(request: AcceptInviteRequest, db: Session = Depends(get_db)) -> TokenPair:
    return invite_reset.accept_invite(
        db,
        code=request.code,
        display_name=request.display_name,
        password=request.password,
        email=request.email,
    )


@router.get("/invites")
def list_invites(
    principal: Principal = Depends(require_roles("OWNER", "ADMIN")),
    db: Session = Depends(get_db),
):
    invites = db.scalars(
        select(InviteCode)
        .where(InviteCode.organization_id == principal.organization_id)
        .order_by(InviteCode.created_at.desc())
    ).all()
    return [
        {
            "id": i.id,
            "code": i.code,
            "role": i.role,
            "email": i.email,
            "phone": i.phone,
            "linked_student_id": i.linked_student_id,
            "used_at": i.used_at,
            "expires_at": i.expires_at,
            "created_at": i.created_at,
        }
        for i in invites
    ]


@router.delete("/invites/{invite_id}", status_code=204)
def revoke_invite(
    invite_id: UUID,
    principal: Principal = Depends(require_roles("OWNER", "ADMIN")),
    db: Session = Depends(get_db),
) -> None:
    invite_reset.revoke_invite(db, organization_id=principal.organization_id, invite_id=invite_id)


# ---------------------------------------------------------------------------
# F-5: Password reset & Rate Limiting
# ---------------------------------------------------------------------------

class PasswordResetRequestBody(BaseModel):
    email: str = Field(min_length=1, max_length=320)


class PasswordResetCompleteBody(BaseModel):
    token: str = Field(min_length=1)
    new_password: str = Field(min_length=8)


@router.post("/password-reset/request", status_code=204)
def request_password_reset(request: PasswordResetRequestBody, db: Session = Depends(get_db)) -> None:
    check_rate_limit(f"pwd_reset_{request.email.lower()}", max_attempts=5, window_seconds=60)
    invite_reset.request_password_reset(db, request.email)


@router.post("/password-reset/complete", status_code=204)
def complete_password_reset(request: PasswordResetCompleteBody, db: Session = Depends(get_db)) -> None:
    check_rate_limit("pwd_reset_complete", max_attempts=10, window_seconds=60)
    invite_reset.complete_password_reset(db, request.token, request.new_password)


# ---------------------------------------------------------------------------
# Email Verification
# ---------------------------------------------------------------------------

class EmailVerifyRequestBody(BaseModel):
    email: str = Field(min_length=1, max_length=320)


class EmailVerifyConfirmBody(BaseModel):
    token: str = Field(min_length=1)


@router.post("/verify-email/request", status_code=204)
def request_email_verification(request: EmailVerifyRequestBody, db: Session = Depends(get_db)) -> None:
    check_rate_limit(f"verify_email_{request.email.lower()}", max_attempts=5, window_seconds=60)
    invite_reset.request_email_verification(db, request.email)


@router.post("/verify-email/confirm")
def confirm_email_verification(request: EmailVerifyConfirmBody, db: Session = Depends(get_db)) -> dict:
    check_rate_limit("verify_email_confirm", max_attempts=10, window_seconds=60)
    success = invite_reset.confirm_email_verification(db, request.token)
    return {"verified": success}
