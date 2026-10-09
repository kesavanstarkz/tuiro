"""Requests and Approval Engine API."""
from __future__ import annotations

import json
from datetime import date, datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.core.dependencies import Principal, require_authenticated_user, require_roles
from app.core.errors import TuiroError
from app.db import get_db
from app.models import Notification, Request, RequestComment, User

router = APIRouter(prefix="/requests", tags=["requests"])

APPROVER_ROLES = ("OWNER", "ADMIN", "SUPER_ADMIN")


class RequestCreate(BaseModel):
    request_type: str = Field(default="LEAVE", pattern=r"^[A-Z0-9_]{2,50}$")
    title: str = Field(min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=5000)
    start_date: date | None = None
    end_date: date | None = None
    metadata: dict[str, object] = Field(default_factory=dict)


class RequestDecision(BaseModel):
    status: str = Field(pattern=r"^(APPROVED|REJECTED)$")
    decision_reason: str | None = Field(default=None, max_length=2000)


class CommentCreate(BaseModel):
    comment: str = Field(min_length=1, max_length=5000)


def _request_payload(req: Request, user_map: dict[UUID, User] | None = None) -> dict:
    requester = user_map.get(req.requester_id) if user_map else None
    decider = user_map.get(req.decided_by) if user_map and req.decided_by else None
    return {
        "id": str(req.id),
        "request_type": req.request_type,
        "title": req.title,
        "description": req.description,
        "start_date": str(req.start_date) if req.start_date else None,
        "end_date": str(req.end_date) if req.end_date else None,
        "status": req.status,
        "decision_reason": req.decision_reason,
        "decided_by": str(req.decided_by) if req.decided_by else None,
        "decided_by_name": decider.display_name if decider else None,
        "decided_at": req.decided_at.isoformat() if req.decided_at else None,
        "requester_id": str(req.requester_id),
        "requester_name": requester.display_name if requester else None,
        "requester_email": requester.email if requester else None,
        "metadata": json.loads(req.metadata_json or "{}"),
        "created_at": req.created_at.isoformat() if req.created_at else None,
        "updated_at": req.updated_at.isoformat() if req.updated_at else None,
    }


@router.post("", status_code=201)
def create_request(
    data: RequestCreate,
    principal: Principal = Depends(require_authenticated_user),
    db: Session = Depends(get_db),
):
    req = Request(
        organization_id=principal.organization_id,
        requester_id=principal.user.id,
        request_type=data.request_type,
        title=data.title,
        description=data.description,
        start_date=data.start_date,
        end_date=data.end_date,
        status="PENDING",
        metadata_json=json.dumps(data.metadata),
    )
    db.add(req)
    db.commit()
    db.refresh(req)
    return _request_payload(req, {principal.user.id: principal.user})


@router.get("")
def list_requests(
    scope: str = Query(default="my", pattern=r"^(my|pending|all)$"),
    status: str | None = None,
    request_type: str | None = None,
    principal: Principal = Depends(require_authenticated_user),
    db: Session = Depends(get_db),
):
    is_approver = principal.role in APPROVER_ROLES

    statement = select(Request).where(Request.organization_id == principal.organization_id)

    if scope == "my" or not is_approver:
        statement = statement.where(Request.requester_id == principal.user.id)
    elif scope == "pending":
        statement = statement.where(Request.status == "PENDING")

    if status:
        statement = statement.where(Request.status == status)
    if request_type:
        statement = statement.where(Request.request_type == request_type)

    requests = db.scalars(statement.order_by(Request.created_at.desc())).all()

    # Pre-fetch user display names
    user_ids = {r.requester_id for r in requests} | {r.decided_by for r in requests if r.decided_by}
    user_map = {}
    if user_ids:
        users = db.scalars(select(User).where(User.id.in_(user_ids))).all()
        user_map = {u.id: u for u in users}

    return [_request_payload(r, user_map) for r in requests]


@router.get("/{request_id:uuid}")
def get_request(
    request_id: UUID,
    principal: Principal = Depends(require_authenticated_user),
    db: Session = Depends(get_db),
):
    req = db.scalar(
        select(Request).where(
            Request.id == request_id,
            Request.organization_id == principal.organization_id,
        )
    )
    if not req:
        raise TuiroError("REQUEST_NOT_FOUND", "The requested approval item was not found.", 404)

    # Permission: requester or approver role
    if req.requester_id != principal.user.id and principal.role not in APPROVER_ROLES:
        raise TuiroError("FORBIDDEN", "You do not have access to this request.", 403)

    user_ids = {req.requester_id}
    if req.decided_by:
        user_ids.add(req.decided_by)
    users = db.scalars(select(User).where(User.id.in_(user_ids))).all()
    user_map = {u.id: u for u in users}

    payload = _request_payload(req, user_map)

    # Attach comments
    comments = db.scalars(
        select(RequestComment)
        .where(RequestComment.request_id == request_id)
        .order_by(RequestComment.created_at.asc())
    ).all()
    comment_user_ids = {c.user_id for c in comments}
    if comment_user_ids:
        c_users = db.scalars(select(User).where(User.id.in_(comment_user_ids))).all()
        for u in c_users:
            user_map[u.id] = u

    payload["comments"] = [
        {
            "id": str(c.id),
            "user_id": str(c.user_id),
            "user_name": user_map.get(c.user_id).display_name if user_map.get(c.user_id) else "Unknown",
            "comment": c.comment,
            "created_at": c.created_at.isoformat() if c.created_at else None,
        }
        for c in comments
    ]
    return payload


@router.post("/{request_id:uuid}/decide")
def decide_request(
    request_id: UUID,
    data: RequestDecision,
    principal: Principal = Depends(require_roles(*APPROVER_ROLES)),
    db: Session = Depends(get_db),
):
    req = db.scalar(
        select(Request).where(
            Request.id == request_id,
            Request.organization_id == principal.organization_id,
        )
    )
    if not req:
        raise TuiroError("REQUEST_NOT_FOUND", "The requested approval item was not found.", 404)

    if req.status != "PENDING":
        raise TuiroError("ALREADY_DECIDED", f"Request has already been {req.status.lower()}.", 400)

    req.status = data.status
    req.decision_reason = data.decision_reason
    req.decided_by = principal.user.id
    req.decided_at = datetime.now(timezone.utc)

    # Notify requester
    notification = Notification(
        organization_id=principal.organization_id,
        recipient_user_id=req.requester_id,
        recipient=principal.user.email,
        channel="IN_APP",
        title=f"Request {data.status.capitalize()}: {req.title}",
        message=f"Your request was {data.status.lower()} by {principal.user.display_name}."
        + (f" Reason: {data.decision_reason}" if data.decision_reason else ""),
        notification_type="APPROVAL_DECISION",
        deep_link=f"/requests/{req.id}",
    )
    db.add(notification)
    db.commit()
    db.refresh(req)

    return _request_payload(req, {principal.user.id: principal.user})


@router.post("/{request_id:uuid}/cancel")
def cancel_request(
    request_id: UUID,
    principal: Principal = Depends(require_authenticated_user),
    db: Session = Depends(get_db),
):
    req = db.scalar(
        select(Request).where(
            Request.id == request_id,
            Request.organization_id == principal.organization_id,
        )
    )
    if not req:
        raise TuiroError("REQUEST_NOT_FOUND", "The requested approval item was not found.", 404)

    if req.requester_id != principal.user.id and principal.role not in APPROVER_ROLES:
        raise TuiroError("FORBIDDEN", "Only the requester or an administrator can cancel a request.", 403)

    if req.status != "PENDING":
        raise TuiroError("CANNOT_CANCEL", f"Cannot cancel a request that is already {req.status.lower()}.", 400)

    req.status = "CANCELLED"
    db.commit()
    db.refresh(req)
    return _request_payload(req, {principal.user.id: principal.user})


@router.post("/{request_id:uuid}/comments", status_code=201)
def add_comment(
    request_id: UUID,
    data: CommentCreate,
    principal: Principal = Depends(require_authenticated_user),
    db: Session = Depends(get_db),
):
    req = db.scalar(
        select(Request).where(
            Request.id == request_id,
            Request.organization_id == principal.organization_id,
        )
    )
    if not req:
        raise TuiroError("REQUEST_NOT_FOUND", "The requested approval item was not found.", 404)

    if req.requester_id != principal.user.id and principal.role not in APPROVER_ROLES:
        raise TuiroError("FORBIDDEN", "You do not have access to comment on this request.", 403)

    comment = RequestComment(
        request_id=request_id,
        user_id=principal.user.id,
        comment=data.comment,
    )
    db.add(comment)
    db.commit()
    db.refresh(comment)

    return {
        "id": str(comment.id),
        "user_id": str(comment.user_id),
        "user_name": principal.user.display_name,
        "comment": comment.comment,
        "created_at": comment.created_at.isoformat() if comment.created_at else None,
    }
