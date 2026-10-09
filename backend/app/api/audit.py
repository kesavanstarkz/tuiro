"""Audit Logs API Router."""
from __future__ import annotations

from typing import Any
from uuid import UUID
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.dependencies import Principal, require_roles
from app.db import get_db
from app.services import audit

router = APIRouter()


@router.get("/audit-logs")
def list_audit_logs(
    action: str | None = Query(default=None),
    entity_type: str | None = Query(default=None),
    user_id: UUID | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    principal: Principal = Depends(require_roles("OWNER", "ADMIN")),
    db: Session = Depends(get_db),
) -> list[dict[str, Any]]:
    return audit.query_audit_logs(
        db,
        organization_id=principal.organization_id,
        entity_type=entity_type,
        action=action,
        user_id=user_id,
        limit=limit,
        offset=offset,
    )
