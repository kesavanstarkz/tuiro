"""Audit logging service for security and financial changes."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any
from uuid import UUID, uuid4
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import AuditLog, User


def record_audit_event(
    db: Session,
    organization_id: UUID,
    action: str,
    entity_type: str,
    user_id: UUID | None = None,
    entity_id: UUID | None = None,
    metadata: dict[str, Any] | None = None,
    before: dict[str, Any] | None = None,
    after: dict[str, Any] | None = None,
    request_id: str | None = None,
) -> AuditLog:
    meta = metadata.copy() if metadata else {}
    if before is not None:
        meta["before"] = before
    if after is not None:
        meta["after"] = after
    if request_id:
        meta["request_id"] = request_id

    entry = AuditLog(
        id=uuid4(),
        organization_id=organization_id,
        user_id=user_id,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        metadata_json=json.dumps(meta),
        created_at=datetime.now(timezone.utc),
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return entry


def query_audit_logs(
    db: Session,
    organization_id: UUID,
    entity_type: str | None = None,
    action: str | None = None,
    user_id: UUID | None = None,
    limit: int = 100,
    offset: int = 0,
) -> list[dict[str, Any]]:
    stmt = (
        select(AuditLog)
        .where(AuditLog.organization_id == organization_id)
        .order_by(AuditLog.created_at.desc())
    )
    if entity_type:
        stmt = stmt.where(AuditLog.entity_type == entity_type)
    if action:
        stmt = stmt.where(AuditLog.action == action)
    if user_id:
        stmt = stmt.where(AuditLog.user_id == user_id)

    records = db.scalars(stmt.offset(offset).limit(min(limit, 200))).all()
    results = []
    for r in records:
        user = db.get(User, r.user_id) if r.user_id else None
        try:
            meta = json.loads(r.metadata_json) if r.metadata_json else {}
        except Exception:
            meta = {}
        results.append(
            {
                "id": str(r.id),
                "action": r.action,
                "entity_type": r.entity_type,
                "entity_id": str(r.entity_id) if r.entity_id else None,
                "user_id": str(r.user_id) if r.user_id else None,
                "user_name": user.display_name if user else "System",
                "user_email": user.email if user else None,
                "metadata": meta,
                "created_at": r.created_at.isoformat() if r.created_at else None,
            }
        )
    return results
