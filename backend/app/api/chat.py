"""Realtime and Channels/Chat API.
Provides unified thread listing, message sending, and history retrieval.
"""
from __future__ import annotations

from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.dependencies import Principal, require_authenticated_user
from app.core.errors import TuiroError
from app.db import get_db
from app.models import ChatMessage, ChatParticipant, ChatThread, Group, OrganizationMember, User

router = APIRouter(prefix="/chat", tags=["chat"])


class ChatMessageInput(BaseModel):
    text: str = Field(min_length=1, max_length=10000)
    attachment: str | None = None


def _thread_payload(thread: ChatThread, db: Session, current_user_id: UUID) -> dict:
    title = "Chat"
    if thread.type == "GROUP" and thread.group_id:
        group = db.get(Group, thread.group_id)
        title = group.name if group else "Group Channel"
    elif thread.type == "DIRECT":
        other_participant_id = db.scalar(
            select(ChatParticipant.user_id).where(
                ChatParticipant.thread_id == thread.id,
                ChatParticipant.user_id != current_user_id,
            )
        )
        if other_participant_id:
            other_user = db.get(User, other_participant_id)
            title = other_user.display_name if other_user else "Direct Message"
        else:
            title = "Direct Message"

    last_msg = db.scalar(
        select(ChatMessage)
        .where(ChatMessage.thread_id == thread.id)
        .order_by(ChatMessage.timestamp.desc())
    )

    return {
        "id": str(thread.id),
        "type": thread.type,
        "title": title,
        "group_id": str(thread.group_id) if thread.group_id else None,
        "created_at": thread.created_at.isoformat() if thread.created_at else None,
        "last_message": {
            "text": last_msg.text,
            "timestamp": last_msg.timestamp.isoformat() if last_msg.timestamp else None,
            "sender_id": str(last_msg.sender_id),
        }
        if last_msg
        else None,
    }


@router.get("/threads")
def list_threads(
    principal: Principal = Depends(require_authenticated_user),
    db: Session = Depends(get_db),
):
    """List all group and direct channels accessible to the user."""
    # 1. Group threads for this organization
    group_threads = db.scalars(
        select(ChatThread).where(
            ChatThread.organization_id == principal.organization_id,
            ChatThread.type == "GROUP",
        )
    ).all()

    # 2. Direct threads where current user is a participant
    direct_threads = db.scalars(
        select(ChatThread)
        .join(ChatParticipant, ChatParticipant.thread_id == ChatThread.id)
        .where(
            ChatThread.organization_id == principal.organization_id,
            ChatThread.type == "DIRECT",
            ChatParticipant.user_id == principal.user.id,
        )
    ).all()

    all_threads = list({t.id: t for t in (group_threads + direct_threads)}.values())
    return [_thread_payload(t, db, principal.user.id) for t in all_threads]


@router.get("/threads/{thread_id:uuid}/messages")
def get_thread_messages(
    thread_id: UUID,
    limit: int = Query(default=50, ge=1, le=100),
    principal: Principal = Depends(require_authenticated_user),
    db: Session = Depends(get_db),
):
    thread = db.scalar(
        select(ChatThread).where(
            ChatThread.id == thread_id,
            ChatThread.organization_id == principal.organization_id,
        )
    )
    if not thread:
        raise TuiroError("THREAD_NOT_FOUND", "Chat thread not found.", 404)

    messages = db.scalars(
        select(ChatMessage)
        .where(ChatMessage.thread_id == thread_id)
        .order_by(ChatMessage.timestamp.asc())
        .limit(limit)
    ).all()

    sender_ids = {m.sender_id for m in messages}
    users = db.scalars(select(User).where(User.id.in_(sender_ids))).all() if sender_ids else []
    user_map = {u.id: u.display_name for u in users}

    return [
        {
            "id": str(m.id),
            "thread_id": str(m.thread_id),
            "sender_id": str(m.sender_id),
            "sender_name": user_map.get(m.sender_id, "User"),
            "text": m.text,
            "attachment": m.attachment,
            "timestamp": m.timestamp.isoformat() if m.timestamp else None,
        }
        for m in messages
    ]


@router.post("/threads/{thread_id:uuid}/messages", status_code=201)
def post_thread_message(
    thread_id: UUID,
    data: ChatMessageInput,
    principal: Principal = Depends(require_authenticated_user),
    db: Session = Depends(get_db),
):
    thread = db.scalar(
        select(ChatThread).where(
            ChatThread.id == thread_id,
            ChatThread.organization_id == principal.organization_id,
        )
    )
    if not thread:
        raise TuiroError("THREAD_NOT_FOUND", "Chat thread not found.", 404)

    msg = ChatMessage(
        thread_id=thread_id,
        sender_id=principal.user.id,
        text=data.text,
        attachment=data.attachment,
    )
    db.add(msg)
    db.commit()
    db.refresh(msg)

    return {
        "id": str(msg.id),
        "thread_id": str(msg.thread_id),
        "sender_id": str(msg.sender_id),
        "sender_name": principal.user.display_name,
        "text": msg.text,
        "attachment": msg.attachment,
        "timestamp": msg.timestamp.isoformat() if msg.timestamp else None,
    }
