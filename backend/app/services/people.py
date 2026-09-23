from __future__ import annotations

from collections.abc import Sequence
from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.errors import TuiroError
from app.models import ClassGroup, Parent, Student, Subscription, SubscriptionPlan, Teacher


def _model(kind: str):
    return {"students": Student, "parents": Parent, "classes": ClassGroup, "teachers": Teacher}[kind]


def list_records(db: Session, organization_id: UUID, kind: str, search: str | None, limit: int, offset: int) -> Sequence:
    model = _model(kind)
    query = select(model).where(model.organization_id == organization_id).offset(offset).limit(min(limit, 100))
    if search and kind == "students":
        query = query.where(or_(Student.first_name.ilike(f"%{search}%"), Student.last_name.ilike(f"%{search}%"), Student.student_number.ilike(f"%{search}%")))
    elif search and kind == "parents":
        query = query.where(or_(Parent.name.ilike(f"%{search}%"), Parent.phone.ilike(f"%{search}%")))
    elif search and kind == "classes":
        query = query.where(or_(ClassGroup.name.ilike(f"%{search}%"), ClassGroup.subject.ilike(f"%{search}%")))
    return db.scalars(query).all()


def get_record(db: Session, organization_id: UUID, kind: str, record_id: UUID):
    record = db.scalar(select(_model(kind)).where(_model(kind).id == record_id, _model(kind).organization_id == organization_id))
    if record is None:
        raise TuiroError(f"{kind[:-1].upper()}_NOT_FOUND", "The requested record was not found.", 404)
    return record


def create_record(db: Session, organization_id: UUID, kind: str, values: dict):
    model = _model(kind)
    if kind == "students":
        student_number = values["student_number"].strip()
        values["student_number"] = student_number
        duplicate = db.scalar(select(Student.id).where(Student.organization_id == organization_id, Student.student_number == student_number))
        if duplicate:
            raise TuiroError("STUDENT_NUMBER_ALREADY_EXISTS", "That student number is already in use. Choose a unique number.", 409)
        subscription = db.scalar(select(Subscription).where(Subscription.organization_id == organization_id))
        if subscription:
            plan = db.get(SubscriptionPlan, subscription.plan_id)
            current = db.scalar(select(func.count()).select_from(Student).where(Student.organization_id == organization_id, Student.status == "ACTIVE")) or 0
            if plan and plan.student_limit is not None and current >= plan.student_limit:
                raise TuiroError("STUDENT_LIMIT_REACHED", "You have reached your student limit. Upgrade your plan to add more students.", 409)
    record = model(organization_id=organization_id, **values)
    db.add(record)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        if kind == "students":
            raise TuiroError("STUDENT_NUMBER_ALREADY_EXISTS", "That student number is already in use. Choose a unique number.", 409) from exc
        raise TuiroError("DUPLICATE_RECORD", "A record with those details already exists.", 409) from exc
    db.refresh(record)
    return record


def update_record(db: Session, organization_id: UUID, kind: str, record_id: UUID, values: dict):
    record = get_record(db, organization_id, kind, record_id)
    if kind == "students":
        student_number = values["student_number"].strip()
        values["student_number"] = student_number
        duplicate = db.scalar(select(Student.id).where(Student.organization_id == organization_id, Student.student_number == student_number, Student.id != record_id))
        if duplicate:
            raise TuiroError("STUDENT_NUMBER_ALREADY_EXISTS", "That student number is already in use. Choose a unique number.", 409)
    for key, value in values.items():
        setattr(record, key, value)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        if kind == "students":
            raise TuiroError("STUDENT_NUMBER_ALREADY_EXISTS", "That student number is already in use. Choose a unique number.", 409) from exc
        raise TuiroError("DUPLICATE_RECORD", "A record with those details already exists.", 409) from exc
    db.refresh(record)
    return record


def delete_record(db: Session, organization_id: UUID, kind: str, record_id: UUID) -> None:
    record = get_record(db, organization_id, kind, record_id)
    if kind == "students":
        record.status = "WITHDRAWN"
        db.commit()
        return
    db.delete(record)
    db.commit()
