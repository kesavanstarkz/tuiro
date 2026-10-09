"""Tasks API (Work management, checklists, group tasks)."""
from __future__ import annotations

import json
from datetime import date, datetime
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.dependencies import Principal, require_authenticated_user
from app.core.errors import TuiroError
from app.db import get_db
from app.models import Group, Task, TaskChecklist, User

router = APIRouter(prefix="/tasks", tags=["tasks"])


class TaskCreate(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=5000)
    priority: str = Field(default="MEDIUM", pattern=r"^(LOW|MEDIUM|HIGH|URGENT)$")
    status: str = Field(default="TODO", pattern=r"^(TODO|IN_PROGRESS|REVIEW|DONE)$")
    group_id: UUID | None = None
    assignee_id: UUID | None = None
    due_date: date | None = None
    metadata: dict[str, object] = Field(default_factory=dict)


class TaskPatch(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None
    priority: str | None = Field(default=None, pattern=r"^(LOW|MEDIUM|HIGH|URGENT)$")
    status: str | None = Field(default=None, pattern=r"^(TODO|IN_PROGRESS|REVIEW|DONE)$")
    group_id: UUID | None = None
    assignee_id: UUID | None = None
    due_date: date | None = None
    metadata: dict[str, object] | None = None


class ChecklistItemCreate(BaseModel):
    title: str = Field(min_length=1, max_length=255)


def _task_payload(task: Task, user_map: dict[UUID, User] | None = None, group_name: str | None = None) -> dict:
    assignee = user_map.get(task.assignee_id) if user_map and task.assignee_id else None
    creator = user_map.get(task.created_by) if user_map else None
    return {
        "id": str(task.id),
        "title": task.title,
        "description": task.description,
        "status": task.status,
        "priority": task.priority,
        "group_id": str(task.group_id) if task.group_id else None,
        "group_name": group_name,
        "assignee_id": str(task.assignee_id) if task.assignee_id else None,
        "assignee_name": assignee.display_name if assignee else None,
        "created_by": str(task.created_by),
        "created_by_name": creator.display_name if creator else None,
        "due_date": str(task.due_date) if task.due_date else None,
        "metadata": json.loads(task.metadata_json or "{}"),
        "created_at": task.created_at.isoformat() if task.created_at else None,
        "updated_at": task.updated_at.isoformat() if task.updated_at else None,
    }


@router.post("", status_code=201)
def create_task(
    data: TaskCreate,
    principal: Principal = Depends(require_authenticated_user),
    db: Session = Depends(get_db),
):
    if data.group_id:
        group = db.scalar(select(Group).where(Group.id == data.group_id, Group.organization_id == principal.organization_id))
        if not group:
            raise TuiroError("GROUP_NOT_FOUND", "Specified group does not exist.", 404)

    if data.assignee_id:
        assignee = db.scalar(select(User).where(User.id == data.assignee_id))
        if not assignee:
            raise TuiroError("USER_NOT_FOUND", "Assignee user does not exist.", 404)

    task = Task(
        organization_id=principal.organization_id,
        title=data.title,
        description=data.description,
        priority=data.priority,
        status=data.status,
        group_id=data.group_id,
        assignee_id=data.assignee_id,
        created_by=principal.user.id,
        due_date=data.due_date,
        metadata_json=json.dumps(data.metadata),
    )
    db.add(task)
    db.commit()
    db.refresh(task)
    return _task_payload(task, {principal.user.id: principal.user})


@router.get("")
def list_tasks(
    status: str | None = None,
    priority: str | None = None,
    group_id: UUID | None = None,
    assignee_id: UUID | None = None,
    scope: str = Query(default="all", pattern=r"^(all|my)$"),
    principal: Principal = Depends(require_authenticated_user),
    db: Session = Depends(get_db),
):
    statement = select(Task).where(Task.organization_id == principal.organization_id)

    if scope == "my":
        statement = statement.where(Task.assignee_id == principal.user.id)
    if status:
        statement = statement.where(Task.status == status)
    if priority:
        statement = statement.where(Task.priority == priority)
    if group_id:
        statement = statement.where(Task.group_id == group_id)
    if assignee_id:
        statement = statement.where(Task.assignee_id == assignee_id)

    tasks = db.scalars(statement.order_by(Task.due_date.asc().nulls_last(), Task.created_at.desc())).all()

    # Pre-fetch users & groups
    user_ids = {t.assignee_id for t in tasks if t.assignee_id} | {t.created_by for t in tasks}
    user_map = {}
    if user_ids:
        users = db.scalars(select(User).where(User.id.in_(user_ids))).all()
        user_map = {u.id: u for u in users}

    group_ids = {t.group_id for t in tasks if t.group_id}
    group_map = {}
    if group_ids:
        groups = db.scalars(select(Group).where(Group.id.in_(group_ids))).all()
        group_map = {g.id: g.name for g in groups}

    return [_task_payload(t, user_map, group_map.get(t.group_id)) for t in tasks]


@router.get("/{task_id:uuid}")
def get_task(
    task_id: UUID,
    principal: Principal = Depends(require_authenticated_user),
    db: Session = Depends(get_db),
):
    task = db.scalar(select(Task).where(Task.id == task_id, Task.organization_id == principal.organization_id))
    if not task:
        raise TuiroError("TASK_NOT_FOUND", "Task not found.", 404)

    user_ids = {task.created_by}
    if task.assignee_id:
        user_ids.add(task.assignee_id)
    users = db.scalars(select(User).where(User.id.in_(user_ids))).all()
    user_map = {u.id: u for u in users}

    group_name = None
    if task.group_id:
        group = db.scalar(select(Group).where(Group.id == task.group_id))
        group_name = group.name if group else None

    payload = _task_payload(task, user_map, group_name)

    # Attach checklist items
    items = db.scalars(select(TaskChecklist).where(TaskChecklist.task_id == task_id).order_by(TaskChecklist.created_at.asc())).all()
    payload["checklist"] = [
        {"id": str(i.id), "title": i.title, "is_completed": i.is_completed}
        for i in items
    ]
    return payload


@router.patch("/{task_id:uuid}")
def update_task(
    task_id: UUID,
    data: TaskPatch,
    principal: Principal = Depends(require_authenticated_user),
    db: Session = Depends(get_db),
):
    task = db.scalar(select(Task).where(Task.id == task_id, Task.organization_id == principal.organization_id))
    if not task:
        raise TuiroError("TASK_NOT_FOUND", "Task not found.", 404)

    values = data.model_dump(exclude_unset=True)
    if "metadata" in values:
        values["metadata_json"] = json.dumps(values.pop("metadata"))

    for key, value in values.items():
        setattr(task, key, value)

    db.commit()
    db.refresh(task)
    return _task_payload(task)


@router.delete("/{task_id:uuid}", status_code=204)
def delete_task(
    task_id: UUID,
    principal: Principal = Depends(require_authenticated_user),
    db: Session = Depends(get_db),
):
    task = db.scalar(select(Task).where(Task.id == task_id, Task.organization_id == principal.organization_id))
    if not task:
        raise TuiroError("TASK_NOT_FOUND", "Task not found.", 404)
    db.delete(task)
    db.commit()


@router.post("/{task_id:uuid}/checklist", status_code=201)
def add_checklist_item(
    task_id: UUID,
    data: ChecklistItemCreate,
    principal: Principal = Depends(require_authenticated_user),
    db: Session = Depends(get_db),
):
    task = db.scalar(select(Task).where(Task.id == task_id, Task.organization_id == principal.organization_id))
    if not task:
        raise TuiroError("TASK_NOT_FOUND", "Task not found.", 404)

    item = TaskChecklist(task_id=task_id, title=data.title)
    db.add(item)
    db.commit()
    db.refresh(item)
    return {"id": str(item.id), "title": item.title, "is_completed": item.is_completed}


@router.post("/{task_id:uuid}/checklist/{item_id:uuid}/toggle")
def toggle_checklist_item(
    task_id: UUID,
    item_id: UUID,
    principal: Principal = Depends(require_authenticated_user),
    db: Session = Depends(get_db),
):
    task = db.scalar(select(Task).where(Task.id == task_id, Task.organization_id == principal.organization_id))
    if not task:
        raise TuiroError("TASK_NOT_FOUND", "Task not found.", 404)

    item = db.scalar(select(TaskChecklist).where(TaskChecklist.id == item_id, TaskChecklist.task_id == task_id))
    if not item:
        raise TuiroError("CHECKLIST_ITEM_NOT_FOUND", "Checklist item not found.", 404)

    item.is_completed = not item.is_completed
    db.commit()
    db.refresh(item)
    return {"id": str(item.id), "title": item.title, "is_completed": item.is_completed}
