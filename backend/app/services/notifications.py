"""Notification service: In-app delivery, preferences, and idempotency."""
from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID, uuid4
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.errors import TuiroError
from app.models import Notification, NotificationPreference


def send_notification(
    db: Session,
    organization_id: UUID,
    title: str,
    message: str,
    recipient_user_id: UUID | None = None,
    recipient_contact: str | None = None,
    channel: str = "IN_APP",
    notification_type: str = "GENERAL",
    deep_link: str | None = None,
    idempotency_key: str | None = None,
) -> Notification:
    """Creates a notification idempotently per organization."""
    if idempotency_key:
        existing = db.scalar(
            select(Notification).where(
                Notification.organization_id == organization_id,
                Notification.idempotency_key == idempotency_key,
            )
        )
        if existing:
            return existing

    # Preferences suppress delivery but retain an auditable record of the event.
    # This also makes idempotent retries return the same notification.
    suppressed = False
    if recipient_user_id:
        pref = db.scalar(
            select(NotificationPreference).where(
                NotificationPreference.organization_id == organization_id,
                NotificationPreference.user_id == recipient_user_id,
            )
        )
        if pref and not pref.in_app_enabled and channel == "IN_APP":
            suppressed = True

    notification = Notification(
        id=uuid4(),
        organization_id=organization_id,
        recipient_user_id=recipient_user_id,
        recipient=recipient_contact or (str(recipient_user_id) if recipient_user_id else "system"),
        channel=channel,
        title=title,
        message=message,
        notification_type=notification_type,
        deep_link=deep_link,
        idempotency_key=idempotency_key,
        status="SUPPRESSED" if suppressed else ("SENT" if channel == "IN_APP" else "PENDING"),
        sent_at=datetime.now(timezone.utc) if channel == "IN_APP" and not suppressed else None,
        is_read=False,
        created_at=datetime.now(timezone.utc),
    )
    db.add(notification)
    db.commit()
    db.refresh(notification)
    return notification


def list_user_notifications(
    db: Session,
    organization_id: UUID,
    user_id: UUID,
    unread_only: bool = False,
    limit: int = 50,
    offset: int = 0,
) -> list[Notification]:
    stmt = (
        select(Notification)
        .where(
            Notification.organization_id == organization_id,
            (Notification.recipient_user_id == user_id) | (Notification.recipient_user_id.is_(None)),
        )
        .order_by(Notification.created_at.desc())
    )
    if unread_only:
        stmt = stmt.where(Notification.is_read.is_(False))

    return list(db.scalars(stmt.offset(offset).limit(min(limit, 100))).all())


def get_unread_count(db: Session, organization_id: UUID, user_id: UUID) -> int:
    return db.scalar(
        select(func.count())
        .select_from(Notification)
        .where(
            Notification.organization_id == organization_id,
            (Notification.recipient_user_id == user_id) | (Notification.recipient_user_id.is_(None)),
            Notification.is_read.is_(False),
        )
    ) or 0


def mark_as_read(db: Session, organization_id: UUID, user_id: UUID, notification_id: UUID) -> Notification:
    notif = db.get(Notification, notification_id)
    if (
        notif is None
        or notif.organization_id != organization_id
        or (notif.recipient_user_id is not None and notif.recipient_user_id != user_id)
    ):
        raise TuiroError("NOTIFICATION_NOT_FOUND", "Notification not found.", 404)

    notif.is_read = True
    notif.read_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(notif)
    return notif


def mark_all_as_read(db: Session, organization_id: UUID, user_id: UUID) -> int:
    notifs = db.scalars(
        select(Notification).where(
            Notification.organization_id == organization_id,
            (Notification.recipient_user_id == user_id) | (Notification.recipient_user_id.is_(None)),
            Notification.is_read.is_(False),
        )
    ).all()
    count = len(notifs)
    now = datetime.now(timezone.utc)
    for n in notifs:
        n.is_read = True
        n.read_at = now
    db.commit()
    return count


def get_user_preferences(db: Session, organization_id: UUID, user_id: UUID) -> NotificationPreference:
    pref = db.scalar(
        select(NotificationPreference).where(
            NotificationPreference.organization_id == organization_id,
            NotificationPreference.user_id == user_id,
        )
    )
    if not pref:
        pref = NotificationPreference(
            id=uuid4(),
            organization_id=organization_id,
            user_id=user_id,
            in_app_enabled=True,
            email_enabled=True,
            sms_enabled=False,
            whatsapp_enabled=False,
        )
        db.add(pref)
        db.commit()
        db.refresh(pref)
    return pref


def update_user_preferences(
    db: Session,
    organization_id: UUID,
    user_id: UUID,
    in_app_enabled: bool | None = None,
    email_enabled: bool | None = None,
    sms_enabled: bool | None = None,
    whatsapp_enabled: bool | None = None,
) -> NotificationPreference:
    pref = get_user_preferences(db, organization_id, user_id)
    if in_app_enabled is not None:
        pref.in_app_enabled = in_app_enabled
    if email_enabled is not None:
        pref.email_enabled = email_enabled
    if sms_enabled is not None:
        pref.sms_enabled = sms_enabled
    if whatsapp_enabled is not None:
        pref.whatsapp_enabled = whatsapp_enabled

    db.commit()
    db.refresh(pref)
    return pref
