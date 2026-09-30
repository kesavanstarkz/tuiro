from __future__ import annotations

from datetime import date, datetime
from typing import Optional
from zoneinfo import ZoneInfo

from app.models import Organization

DEFAULT_TIMEZONE = "Asia/Kolkata"


def get_org_timezone(organization: Optional[Organization]) -> ZoneInfo:
    tz_str = organization.timezone if organization and organization.timezone else DEFAULT_TIMEZONE
    try:
        return ZoneInfo(tz_str)
    except Exception:
        return ZoneInfo(DEFAULT_TIMEZONE)


def get_org_now(organization: Optional[Organization]) -> datetime:
    tz = get_org_timezone(organization)
    return datetime.now(tz)


def get_org_today(organization: Optional[Organization]) -> date:
    return get_org_now(organization).date()
