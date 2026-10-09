"""Canonical v2 group APIs.

The v1 class and group routes remain intentionally untouched as compatibility
adapters for the Expo client.  Both routes write the same ``groups`` records;
this API is the only new code path that reads ``group_memberships``.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.dependencies import Principal, require_roles
from app.core.errors import TuiroError
from app.db import get_db
from app.models import Group, GroupMember, GroupMembership, Student

router = APIRouter(prefix="/groups", tags=["groups-v2"])
ADMINS = ("OWNER", "ADMIN")
STAFF = ("OWNER", "ADMIN", "TEACHER")


class GroupCreate(BaseModel):
    name: str = Field(min_length=1, max_length=160)
    kind: str = Field(default="team", pattern=r"^[a-z][a-z0-9_]{0,39}$")
    description: str | None = Field(default=None, max_length=5000)
    parent_group_id: UUID | None = None
    metadata: dict[str, str] = Field(default_factory=dict)


class MembershipCreate(BaseModel):
    member_type: str = Field(default="student", pattern=r"^(student|teacher|employee|user)$")
    member_id: UUID
    member_role: str = Field(default="member", pattern=r"^(member|admin|coordinator)$")


def _group(db: Session, organization_id: UUID, group_id: UUID) -> Group:
    group = db.scalar(select(Group).where(Group.id == group_id, Group.organization_id == organization_id))
    if group is None:
        raise TuiroError("GROUP_NOT_FOUND", "The requested group was not found.", 404)
    return group


def _payload(group: Group) -> dict:
    return {
        "id": str(group.id), "name": group.name, "kind": group.kind,
        "description": group.description, "status": group.status,
        "parent_group_id": str(group.parent_group_id) if group.parent_group_id else None,
        "metadata": json.loads(group.metadata_json or "{}"),
    }


@router.get("")
def list_groups(kind: str | None = None, include_archived: bool = False, principal: Principal = Depends(require_roles(*STAFF)), db: Session = Depends(get_db)):
    statement = select(Group).where(Group.organization_id == principal.organization_id)
    if kind:
        statement = statement.where(Group.kind == kind)
    if not include_archived:
        statement = statement.where(Group.status == "ACTIVE")
    return [_payload(row) for row in db.scalars(statement.order_by(Group.name)).all()]


@router.post("", status_code=201)
def create_group(request: GroupCreate, principal: Principal = Depends(require_roles(*ADMINS)), db: Session = Depends(get_db)):
    if request.parent_group_id:
        _group(db, principal.organization_id, request.parent_group_id)
    group = Group(organization_id=principal.organization_id, created_by=principal.user.id, name=request.name,
                  kind=request.kind, description=request.description, parent_group_id=request.parent_group_id,
                  metadata_json=json.dumps(request.metadata))
    db.add(group); db.commit(); db.refresh(group)
    return _payload(group)


@router.get("/{group_id:uuid}")
def get_group(group_id: UUID, principal: Principal = Depends(require_roles(*STAFF)), db: Session = Depends(get_db)):
    return _payload(_group(db, principal.organization_id, group_id))


@router.get("/{group_id:uuid}/members")
def list_members(group_id: UUID, include_removed: bool = False, principal: Principal = Depends(require_roles(*STAFF)), db: Session = Depends(get_db)):
    _group(db, principal.organization_id, group_id)
    statement = select(GroupMembership).where(GroupMembership.organization_id == principal.organization_id, GroupMembership.group_id == group_id)
    if not include_removed:
        statement = statement.where(GroupMembership.removed_at.is_(None))
    return [{"id": str(m.id), "member_type": m.member_type, "member_id": str(m.member_id), "member_role": m.member_role,
             "joined_at": m.joined_at, "removed_at": m.removed_at} for m in db.scalars(statement).all()]


@router.post("/{group_id:uuid}/members", status_code=201)
def add_member(group_id: UUID, request: MembershipCreate, principal: Principal = Depends(require_roles(*ADMINS)), db: Session = Depends(get_db)):
    _group(db, principal.organization_id, group_id)
    if request.member_type == "student" and not db.scalar(select(Student.id).where(Student.id == request.member_id, Student.organization_id == principal.organization_id)):
        raise TuiroError("STUDENT_NOT_FOUND", "The requested student was not found.", 404)
    membership = db.scalar(select(GroupMembership).where(GroupMembership.group_id == group_id, GroupMembership.member_type == request.member_type, GroupMembership.member_id == request.member_id))
    if membership:
        membership.removed_at = None; membership.member_role = request.member_role; membership.added_by = principal.user.id
    else:
        membership = GroupMembership(organization_id=principal.organization_id, group_id=group_id, **request.model_dump(), added_by=principal.user.id)
        db.add(membership)
    # Preserve the existing education projection until the mobile client moves.
    if request.member_type == "student":
        legacy = db.scalar(select(GroupMember).where(GroupMember.group_id == group_id, GroupMember.student_id == request.member_id))
        if legacy:
            legacy.removed_at = None
        else:
            db.add(GroupMember(organization_id=principal.organization_id, group_id=group_id, student_id=request.member_id))
    db.commit(); db.refresh(membership)
    return {"id": str(membership.id), "member_type": membership.member_type, "member_id": str(membership.member_id), "member_role": membership.member_role}


@router.delete("/{group_id:uuid}/members/{membership_id:uuid}", status_code=204)
def remove_member(group_id: UUID, membership_id: UUID, principal: Principal = Depends(require_roles(*ADMINS)), db: Session = Depends(get_db)):
    _group(db, principal.organization_id, group_id)
    membership = db.scalar(select(GroupMembership).where(GroupMembership.id == membership_id, GroupMembership.group_id == group_id, GroupMembership.organization_id == principal.organization_id, GroupMembership.removed_at.is_(None)))
    if membership is None:
        raise TuiroError("MEMBERSHIP_NOT_FOUND", "Active group membership not found.", 404)
    membership.removed_at = datetime.now(timezone.utc)
    if membership.member_type == "student":
        legacy = db.scalar(select(GroupMember).where(GroupMember.group_id == group_id, GroupMember.student_id == membership.member_id, GroupMember.removed_at.is_(None)))
        if legacy:
            legacy.removed_at = membership.removed_at
    db.commit()
