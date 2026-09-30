"""send_fee_reminders.py – F-2 scheduled fee reminder command.

Usage (cron-safe):
    python -m app.commands.send_fee_reminders [--dry-run]

Cron example (daily 08:00):
    0 8 * * * cd /app && python -m app.commands.send_fee_reminders

Per-organization settings stored in organizations.settings JSON:
    {
        "reminders_enabled": true,       # default true
        "remind_days_before": [7, 3, 1], # default [7, 3, 1]
        "reminder_repeat_days": 0        # 0 = only once per milestone day
    }
"""
from __future__ import annotations

import argparse
import json
import logging
import sys
from abc import ABC, abstractmethod
from datetime import date, datetime, timezone
from typing import Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.db import SessionLocal
from app.models import FeeReminderLog, Notification, Organization, Student, StudentFee

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

_DEFAULT_SETTINGS = {
    "reminders_enabled": True,
    "remind_days_before": [7, 3, 1],
    "reminder_repeat_days": 0,
}


# ---------------------------------------------------------------------------
# Notification channel interface
# ---------------------------------------------------------------------------

class NotificationChannel(ABC):
    @property
    @abstractmethod
    def channel_name(self) -> str:
        pass

    @abstractmethod
    def send(self, organization_id: UUID, recipient: str, message: str) -> None:
        pass


class InAppNotificationChannel(NotificationChannel):
    """Stores a Notification row (default channel)."""

    def __init__(self, db):
        self._db = db

    @property
    def channel_name(self) -> str:
        return "IN_APP"

    def send(self, organization_id: UUID, recipient: str, message: str) -> None:
        notif = Notification(
            organization_id=organization_id,
            recipient=recipient,
            channel=self.channel_name,
            message=message,
            notification_type="FEE_REMINDER",
            status="SENT",
            sent_at=datetime.now(timezone.utc),
        )
        self._db.add(notif)


class WhatsAppMockChannel(NotificationChannel):
    """Mock WhatsApp adapter – logs only, does not hit a real API."""

    @property
    def channel_name(self) -> str:
        return "WHATSAPP"

    def send(self, organization_id: UUID, recipient: str, message: str) -> None:
        logger.info("[WhatsApp mock] org=%s to=%s msg=%s", organization_id, recipient, message[:80])


# ---------------------------------------------------------------------------
# Core reminder logic
# ---------------------------------------------------------------------------

def _org_settings(org: Organization) -> dict:
    try:
        raw = json.loads(org.settings or "{}")
    except (ValueError, TypeError):
        raw = {}
    return {**_DEFAULT_SETTINGS, **raw}


def _student_name(db, student_id: UUID) -> str:
    s = db.get(Student, student_id)
    return f"{s.first_name} {s.last_name}".strip() if s else "Student"


def _build_message(student_name: str, fee: StudentFee, days_left: int) -> str:
    if days_left < 0:
        return (
            f"Dear {student_name}, your fee of {fee.amount_due} "
            f"(period: {fee.billing_period}) is OVERDUE since {fee.due_date}. "
            "Please clear it as soon as possible."
        )
    if days_left == 0:
        return (
            f"Dear {student_name}, your fee of {fee.amount_due} "
            f"(period: {fee.billing_period}) is due TODAY."
        )
    return (
        f"Dear {student_name}, your fee of {fee.amount_due} "
        f"(period: {fee.billing_period}) is due in {days_left} day(s) on {fee.due_date}."
    )


def run_reminders(dry_run: bool = False) -> int:
    """Send reminders for fees that are due soon or overdue.

    Returns the number of reminders sent.
    """
    db = SessionLocal()
    total_sent = 0

    try:
        today = date.today()
        orgs = db.scalars(select(Organization)).all()

        for org in orgs:
            settings = _org_settings(org)
            if not settings.get("reminders_enabled", True):
                continue

            remind_days: list = settings.get("remind_days_before", [7, 3, 1])

            channel = InAppNotificationChannel(db)

            # Fees that are PENDING, PARTIAL, OVERDUE, or DUE
            fees = db.scalars(
                select(StudentFee).where(
                    StudentFee.organization_id == org.id,
                    StudentFee.status.in_(["PENDING", "PARTIAL", "OVERDUE", "DUE"]),
                )
            ).all()

            for fee in fees:
                days_left = (fee.due_date - today).days

                # Decide if today is a reminder day
                should_remind = (days_left in remind_days) or (days_left < 0)
                if not should_remind:
                    continue

                # Dedup: never send the same reminder for the same (fee, date)
                already_sent = db.scalar(
                    select(FeeReminderLog).where(
                        FeeReminderLog.organization_id == org.id,
                        FeeReminderLog.fee_id == fee.id,
                        FeeReminderLog.sent_date == today,
                    )
                )
                if already_sent:
                    continue

                student_name = _student_name(db, fee.student_id)
                message = _build_message(student_name, fee, days_left)
                recipient = str(fee.student_id)

                if dry_run:
                    logger.info(
                        "[dry-run] Would remind: student=%s fee=%s days_left=%d",
                        student_name, fee.id, days_left,
                    )
                else:
                    channel.send(org.id, recipient, message)
                    db.add(FeeReminderLog(
                        organization_id=org.id,
                        fee_id=fee.id,
                        sent_date=today,
                        channel=channel.channel_name,
                    ))
                    total_sent += 1

            if not dry_run:
                try:
                    db.commit()
                except IntegrityError:
                    db.rollback()
                    logger.warning(
                        "Duplicate reminder log for org %s (concurrent run?), skipping.", org.id
                    )

    finally:
        db.close()

    logger.info("Fee reminders done. sent=%d dry_run=%s", total_sent, dry_run)
    return total_sent


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Send fee reminders")
    parser.add_argument("--dry-run", action="store_true", help="Log what would be sent without writing")
    args = parser.parse_args()
    run_reminders(dry_run=args.dry_run)
    sys.exit(0)
