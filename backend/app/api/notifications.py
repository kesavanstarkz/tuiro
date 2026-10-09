"""Authenticated notification inbox and preference endpoints."""
from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.dependencies import Principal, require_authenticated_user, require_roles
from app.core.errors import TuiroError
from app.db import get_db
from app.models import OrganizationMember
from app.services import notifications

router = APIRouter()


class NotificationCreate(BaseModel):
    recipient_user_id: UUID | None = None
    recipient: str | None = Field(default=None, max_length=320)
    title: str = Field(min_length=1, max_length=200)
    message: str = Field(min_length=1)
    channel: str = Field(default="IN_APP", pattern="^(IN_APP|EMAIL|SMS|WHATSAPP)$")
    notification_type: str = Field(default="GENERAL", min_length=1, max_length=40)
    deep_link: str | None = Field(default=None, max_length=255)
    idempotency_key: str | None = Field(default=None, min_length=1, max_length=120)


class NotificationPreferencesUpdate(BaseModel):
    in_app_enabled: bool | None = None
    email_enabled: bool | None = None
    sms_enabled: bool | None = None
    whatsapp_enabled: bool | None = None


def _serialize(notification) -> dict:
    return {
        "id": notification.id,
        "recipient_user_id": notification.recipient_user_id,
        "recipient": notification.recipient,
        "title": notification.title,
        "message": notification.message,
        "channel": notification.channel,
        "notification_type": notification.notification_type,
        "deep_link": notification.deep_link,
        "status": notification.status,
        "is_read": notification.is_read,
        "read_at": notification.read_at,
        "created_at": notification.created_at,
    }


@router.get("/notifications")
def list_notifications(
    unread_only: bool = False,
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    principal: Principal = Depends(require_roles("OWNER", "ADMIN", "TEACHER", "PARENT", "STUDENT")),
    db: Session = Depends(get_db),
):
    return [_serialize(item) for item in notifications.list_user_notifications(
        db, principal.organization_id, principal.user.id, unread_only, limit, offset
    )]


@router.get("/notifications/unread-count")
def unread_count(principal: Principal = Depends(require_authenticated_user), db: Session = Depends(get_db)):
    return {"count": notifications.get_unread_count(db, principal.organization_id, principal.user.id)}


@router.post("/notifications", status_code=status.HTTP_201_CREATED)
def create_notification(
    request: NotificationCreate,
    principal: Principal = Depends(require_roles("OWNER", "ADMIN", "TEACHER")),
    db: Session = Depends(get_db),
):
    if request.recipient_user_id:
        member = db.scalar(select(OrganizationMember).where(
            OrganizationMember.organization_id == principal.organization_id,
            OrganizationMember.user_id == request.recipient_user_id,
        ))
        if member is None:
            raise TuiroError("RECIPIENT_NOT_FOUND", "Recipient not found.", 404)
    if not request.recipient_user_id and not request.recipient:
        raise TuiroError("RECIPIENT_REQUIRED", "A recipient user or contact is required.", 422)
    payload = request.model_dump()
    payload["recipient_contact"] = payload.pop("recipient")
    notification = notifications.send_notification(db, principal.organization_id, **payload)
    return _serialize(notification)


@router.post("/notifications/{notification_id}/read")
def mark_read(
    notification_id: UUID,
    principal: Principal = Depends(require_authenticated_user),
    db: Session = Depends(get_db),
):
    return _serialize(notifications.mark_as_read(db, principal.organization_id, principal.user.id, notification_id))


@router.post("/notifications/read-all")
def mark_all_read(principal: Principal = Depends(require_authenticated_user), db: Session = Depends(get_db)):
    return {"updated": notifications.mark_all_as_read(db, principal.organization_id, principal.user.id)}


@router.get("/notification-preferences")
def get_preferences(principal: Principal = Depends(require_authenticated_user), db: Session = Depends(get_db)):
    preference = notifications.get_user_preferences(db, principal.organization_id, principal.user.id)
    return {key: getattr(preference, key) for key in ("in_app_enabled", "email_enabled", "sms_enabled", "whatsapp_enabled")}


@router.patch("/notification-preferences")
def update_preferences(
    request: NotificationPreferencesUpdate,
    principal: Principal = Depends(require_authenticated_user),
    db: Session = Depends(get_db),
):
    preference = notifications.update_user_preferences(db, principal.organization_id, principal.user.id, **request.model_dump())
    return {key: getattr(preference, key) for key in ("in_app_enabled", "email_enabled", "sms_enabled", "whatsapp_enabled")}
