from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import TuiroError
from app.core.security import create_access_token, create_refresh_token, hash_password, hash_refresh_token, verify_password
from app.models import Organization, OrganizationMember, RefreshSession, Role, Subscription, SubscriptionPlan, User
from app.schemas import LoginRequest, OrganizationItem, RegisterRequest, SwitchOrganizationRequest, TokenPair


def _tokens(db: Session, user: User, organization_id: UUID, role: str) -> TokenPair:
    raw_refresh, refresh_hash, expires_at = create_refresh_token()
    db.add(RefreshSession(user_id=user.id, organization_id=organization_id, token_hash=refresh_hash, expires_at=expires_at))
    memberships = db.scalars(
        select(OrganizationMember).where(OrganizationMember.user_id == user.id)
    ).all()
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


def register(db: Session, request: RegisterRequest) -> TokenPair:
    if db.scalar(select(User).where(User.email == request.email.lower())):
        raise TuiroError("EMAIL_ALREADY_REGISTERED", "An account with this email already exists.", 409)
    user = User(email=request.email.lower(), password_hash=hash_password(request.password), display_name=request.display_name)
    organization = Organization(name=request.organization_name, country_code=request.country_code.upper(), currency_code=request.currency_code.upper(), timezone=request.timezone)
    db.add_all([user, organization])
    db.flush()
    db.add(OrganizationMember(user_id=user.id, organization_id=organization.id, role=Role.OWNER.value))
    free_plan = db.scalar(select(SubscriptionPlan).where(SubscriptionPlan.name == "FREE"))
    if free_plan is None:
        free_plan = SubscriptionPlan(name="FREE", student_limit=20, features="{}")
        db.add(free_plan)
        db.flush()
    db.add(Subscription(organization_id=organization.id, plan_id=free_plan.id, status="TRIAL"))
    tokens = _tokens(db, user, organization.id, Role.OWNER.value)
    db.commit()
    return tokens


def login(db: Session, request: LoginRequest) -> TokenPair:
    user = db.scalar(select(User).where(User.email == request.email.lower()))
    if user is None or not verify_password(request.password, user.password_hash):
        raise TuiroError("INVALID_CREDENTIALS", "Email or password is incorrect.", 401)
    
    memberships = db.scalars(
        select(OrganizationMember).where(OrganizationMember.user_id == user.id)
    ).all()
    if not memberships:
        raise TuiroError("NO_ORGANIZATION", "This account is not linked to an organization.", 403)
        
    org_items = []
    for m in memberships:
        org = db.get(Organization, m.organization_id)
        if org:
            org_items.append(OrganizationItem(id=org.id, name=org.name, role=m.role))

    if request.organization_id is not None:
        target_mem = next((m for m in memberships if m.organization_id == request.organization_id), None)
        if target_mem is None:
            raise TuiroError("FORBIDDEN", "You are not a member of this organization.", 403)
        tokens = _tokens(db, user, target_mem.organization_id, target_mem.role)
        db.commit()
        return tokens
        
    if len(memberships) > 1:
        return TokenPair(
            access_token=None,
            refresh_token=None,
            token_type="bearer",
            organizations=org_items,
        )

    membership = memberships[0]
    tokens = _tokens(db, user, membership.organization_id, membership.role)
    db.commit()
    return tokens


def refresh(db: Session, raw_token: str) -> TokenPair:
    session = db.scalar(select(RefreshSession).where(RefreshSession.token_hash == hash_refresh_token(raw_token)))
    now = datetime.now(timezone.utc)
    expires_at = session.expires_at.replace(tzinfo=timezone.utc) if session and session.expires_at.tzinfo is None else session.expires_at if session else None
    if session is None or session.revoked_at is not None or expires_at <= now:
        raise TuiroError("INVALID_REFRESH_TOKEN", "Refresh token is invalid or expired.", 401)
    session.revoked_at = now
    user = db.get(User, session.user_id)
    if user is None:
        db.commit()
        raise TuiroError("INVALID_SESSION", "Session is no longer valid.", 401)

    if session.organization_id:
        membership = db.scalar(select(OrganizationMember).where(OrganizationMember.user_id == session.user_id, OrganizationMember.organization_id == session.organization_id))
    else:
        membership = db.scalar(select(OrganizationMember).where(OrganizationMember.user_id == session.user_id))

    if membership is None:
        db.commit()
        raise TuiroError("INVALID_SESSION", "Session is no longer valid.", 401)
    tokens = _tokens(db, user, membership.organization_id, membership.role)
    db.commit()
    return tokens


def switch_organization(db: Session, user_id: UUID, request: SwitchOrganizationRequest) -> TokenPair:
    membership = db.scalar(
        select(OrganizationMember)
        .where(OrganizationMember.user_id == user_id, OrganizationMember.organization_id == request.organization_id)
    )
    if membership is None:
        raise TuiroError("FORBIDDEN", "You are not a member of this organization.", 403)
    user = db.get(User, user_id)
    if user is None or not user.is_active:
        raise TuiroError("INVALID_SESSION", "Session is no longer valid.", 401)
    if request.refresh_token:
        old_session = db.scalar(select(RefreshSession).where(RefreshSession.token_hash == hash_refresh_token(request.refresh_token)))
        if old_session is not None:
            old_session.revoked_at = datetime.now(timezone.utc)
    tokens = _tokens(db, user, membership.organization_id, membership.role)
    db.commit()
    return tokens


def logout(db: Session, raw_token: str) -> None:
    session = db.scalar(select(RefreshSession).where(RefreshSession.token_hash == hash_refresh_token(raw_token)))
    if session is not None:
        session.revoked_at = datetime.now(timezone.utc)
        db.commit()
