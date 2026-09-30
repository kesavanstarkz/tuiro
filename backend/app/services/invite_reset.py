"""invite_reset.py – F-4 invite flow and F-5 password reset services."""
from __future__ import annotations

import logging
import secrets
from datetime import datetime, timedelta, timezone
from hashlib import sha256
from typing import Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import TuiroError
from app.core.security import hash_password
from app.models import (
    InviteCode,
    Organization,
    OrganizationMember,
    Parent,
    PasswordResetToken,
    RefreshSession,
    Student,
    StudentParent,
    User,
)
from app.schemas import OrganizationItem, TokenPair

logger = logging.getLogger(__name__)


def _tokens(db: Session, user: User, organization_id: UUID, role: str) -> TokenPair:
    """Reuse the token generation logic (duplicated to avoid circular import)."""
    from app.core.security import create_access_token, create_refresh_token
    from app.models import RefreshSession as RS

    raw_refresh, refresh_hash, expires_at = create_refresh_token()
    db.add(RS(user_id=user.id, organization_id=organization_id, token_hash=refresh_hash, expires_at=expires_at))
    memberships = db.scalars(select(OrganizationMember).where(OrganizationMember.user_id == user.id)).all()
    org_items = []
    for m in memberships:
        org = db.get(Organization, m.organization_id)
        if org:
            org_items.append(OrganizationItem(id=org.id, name=org.name, role=m.role))
    return TokenPair(
        access_token=create_access_token(str(user.id), str(organization_id), role),
        refresh_token=raw_refresh,
        token_type="bearer",
        organizations=org_items,
    )


# ---------------------------------------------------------------------------
# F-4: Invite flow
# ---------------------------------------------------------------------------

def create_invite(
    db: Session,
    organization_id: UUID,
    created_by_user_id: UUID,
    role: str,
    email: Optional[str] = None,
    phone: Optional[str] = None,
    linked_student_id: Optional[UUID] = None,
    expires_hours: int = 72,
) -> InviteCode:
    """Create a single-use invite code."""
    allowed_roles = {"ADMIN", "TEACHER", "PARENT", "STUDENT"}
    if role not in allowed_roles:
        raise TuiroError("INVALID_ROLE", f"Role must be one of {allowed_roles}.", 400)

    if linked_student_id is not None:
        s = db.get(Student, linked_student_id)
        if s is None or s.organization_id != organization_id:
            raise TuiroError("RESOURCE_NOT_FOUND", "Linked student not found.", 404)

    code = secrets.token_urlsafe(32)
    expires_at = datetime.now(timezone.utc) + timedelta(hours=expires_hours)
    invite = InviteCode(
        organization_id=organization_id,
        code=code,
        role=role,
        email=email.lower() if email else None,
        phone=phone,
        linked_student_id=linked_student_id,
        created_by=created_by_user_id,
        expires_at=expires_at,
    )
    db.add(invite)
    db.commit()
    db.refresh(invite)
    return invite


def accept_invite(
    db: Session,
    code: str,
    display_name: str,
    password: str,
    email: Optional[str] = None,
) -> TokenPair:
    """Accept an invite: create (or link) a user and join the org."""
    now = datetime.now(timezone.utc)
    invite = db.scalar(select(InviteCode).where(InviteCode.code == code))
    if invite is None:
        raise TuiroError("INVITE_NOT_FOUND", "Invite code not found or already used.", 404)

    expires = invite.expires_at.replace(tzinfo=timezone.utc) if invite.expires_at.tzinfo is None else invite.expires_at
    if invite.used_at is not None or expires < now:
        raise TuiroError("INVITE_EXPIRED", "This invite code has already been used or has expired.", 410)

    resolved_email = (invite.email or email or "").lower()
    if not resolved_email:
        raise TuiroError("EMAIL_REQUIRED", "An email address is required to create an account.", 400)

    user = db.scalar(select(User).where(User.email == resolved_email))
    if user is None:
        user = User(
            email=resolved_email,
            password_hash=hash_password(password),
            display_name=display_name,
        )
        db.add(user)
        db.flush()

    existing_mem = db.scalar(
        select(OrganizationMember).where(
            OrganizationMember.user_id == user.id,
            OrganizationMember.organization_id == invite.organization_id,
        )
    )
    if existing_mem:
        raise TuiroError("ALREADY_MEMBER", "This user is already a member of the organization.", 409)

    db.add(OrganizationMember(user_id=user.id, organization_id=invite.organization_id, role=invite.role))

    # If PARENT: create Parent record and link to student
    if invite.role == "PARENT" and invite.linked_student_id:
        parts = display_name.split(None, 1)
        first = parts[0]
        last = parts[1] if len(parts) > 1 else ""
        parent = db.scalar(
            select(Parent).where(
                Parent.organization_id == invite.organization_id,
                Parent.user_id == user.id,
            )
        )
        if parent is None:
            parent = Parent(
                organization_id=invite.organization_id,
                user_id=user.id,
                first_name=first,
                last_name=last,
            )
            db.add(parent)
            db.flush()
        existing_link = db.scalar(
            select(StudentParent).where(
                StudentParent.student_id == invite.linked_student_id,
                StudentParent.parent_id == parent.id,
            )
        )
        if not existing_link:
            db.add(StudentParent(student_id=invite.linked_student_id, parent_id=parent.id, is_primary=True))

    invite.used_by = user.id
    invite.used_at = now
    tokens = _tokens(db, user, invite.organization_id, invite.role)
    db.commit()
    return tokens


# ---------------------------------------------------------------------------
# F-5: Password reset
# ---------------------------------------------------------------------------

def _hash_token(raw: str) -> str:
    return sha256(raw.encode()).hexdigest()


_last_reset_token: Optional[str] = None


def request_password_reset(db: Session, email: str) -> None:
    """Issue a reset token. Silent whether or not the email exists."""
    global _last_reset_token
    user = db.scalar(select(User).where(User.email == email.lower()))
    if user is None:
        return  # Intentionally silent
    raw = secrets.token_urlsafe(32)
    _last_reset_token = raw
    token_hash = _hash_token(raw)
    expires_at = datetime.now(timezone.utc) + timedelta(hours=1)
    db.add(PasswordResetToken(user_id=user.id, token_hash=token_hash, expires_at=expires_at))
    db.commit()
    # In production send the raw token by email.
    # Logged here for testing only — never log tokens in production.
    logger.info("Password reset token for %s: %s", email, raw)


def complete_password_reset(db: Session, raw_token: str, new_password: str) -> None:
    """Verify reset token, set new password, revoke all refresh sessions."""
    now = datetime.now(timezone.utc)
    token_hash = _hash_token(raw_token)
    prt = db.scalar(select(PasswordResetToken).where(PasswordResetToken.token_hash == token_hash))
    if prt is None:
        raise TuiroError("INVALID_RESET_TOKEN", "Password reset token is invalid or expired.", 400)
    expires = prt.expires_at.replace(tzinfo=timezone.utc) if prt.expires_at.tzinfo is None else prt.expires_at
    if prt.used_at is not None or expires < now:
        raise TuiroError("INVALID_RESET_TOKEN", "Password reset token is invalid or expired.", 400)
    user = db.get(User, prt.user_id)
    if user is None or not user.is_active:
        raise TuiroError("INVALID_RESET_TOKEN", "Password reset token is invalid or expired.", 400)
    user.password_hash = hash_password(new_password)
    prt.used_at = now
    # Revoke all active refresh sessions
    sessions = db.scalars(
        select(RefreshSession).where(
            RefreshSession.user_id == user.id,
            RefreshSession.revoked_at.is_(None),
        )
    ).all()
    for s in sessions:
        s.revoked_at = now
    db.commit()
