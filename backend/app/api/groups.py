"""Group-first CMS endpoints.

Items are stored once against a group.  The student view is a projection over
active memberships, so removing a member immediately removes inherited work,
fees, and schedules without mutating historical records.
"""
from __future__ import annotations

import json
from datetime import date, datetime, timezone
from decimal import Decimal
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field, model_validator
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.dependencies import Principal, require_authenticated_user, require_roles
from app.core.permissions import check_teacher_class_access
from app.core.timezone import get_org_today
from app.core.errors import TuiroError
from app.db import get_db
from app.models import Assignment, AuditLog, ChatMessage, ChatParticipant, ChatThread, ClassGroup, ClassStudent, FeePayment, Group, GroupAttendanceRecord, GroupAttendanceSession, GroupFee, GroupMember, GroupSchedule, Organization, OrganizationMember, Parent, Payment, Receipt, Student, StudentFee, StudentParent, User
from app.services.receipts import generate_receipt_number

router = APIRouter(prefix="/groups", tags=["groups"])
ADMINS = ("OWNER", "ADMIN")
STAFF = ("OWNER", "ADMIN", "TEACHER")
ALL_ROLES = ("OWNER", "ADMIN", "TEACHER", "PARENT", "STUDENT")
PORTAL_READ = ("OWNER", "ADMIN", "PARENT", "STUDENT")
EDITORS = STAFF


class GroupInput(BaseModel):
    name: str = Field(min_length=1, max_length=160)


class ScheduleInput(BaseModel):
    day_of_week: int = Field(ge=0, le=6)
    start_time: str = Field(pattern=r"^([01]\d|2[0-3]):[0-5]\d$")
    end_time: str = Field(pattern=r"^([01]\d|2[0-3]):[0-5]\d$")
    subject: str | None = Field(default=None, max_length=120)


class AssignmentInput(BaseModel):
    group_id: UUID | None = None
    student_id: UUID | None = None
    title: str = Field(min_length=1, max_length=200)
    description: str | None = None
    due_date: date | None = None
    type: str = Field(pattern="^(assignment|test)$")
    attachments: list[str] = []
    overrides_id: UUID | None = None

    @model_validator(mode="after")
    def one_target(self):
        if bool(self.group_id) == bool(self.student_id):
            raise ValueError("Set exactly one of group_id or student_id")
        return self


class FeeInput(BaseModel):
    group_id: UUID | None = None
    student_id: UUID | None = None
    amount: Decimal = Field(gt=0)
    due_date: date
    status: str = Field(default="pending", pattern="^(pending|paid|overdue)$")
    overrides_id: UUID | None = None

    @model_validator(mode="after")
    def one_target(self):
        if bool(self.group_id) == bool(self.student_id):
            raise ValueError("Set exactly one of group_id or student_id")
        return self


class MessageInput(BaseModel):
    text: str = Field(min_length=1)
    attachment: str | None = None


class AttendanceRecordInput(BaseModel):
    student_id: UUID
    status: str = Field(pattern="^(PRESENT|ABSENT|LATE|EXCUSED)$")
    notes: str | None = None


class GroupAttendanceInput(BaseModel):
    session_date: date
    records: list[AttendanceRecordInput]


class FeePaymentInput(BaseModel):
    student_id: UUID
    amount_paid: Decimal = Field(gt=0)
    paid_on: date = Field(default_factory=date.today)


def _record(db: Session, model, org: UUID, record_id: UUID):
    value = db.scalar(select(model).where(model.id == record_id, model.organization_id == org))
    if value is None:
        raise TuiroError("RESOURCE_NOT_FOUND", "The requested resource was not found.", 404)
    return value


def _active_member(db: Session, org: UUID, group_id: UUID, student_id: UUID) -> bool:
    return db.scalar(select(GroupMember.id).where(GroupMember.organization_id == org, GroupMember.group_id == group_id, GroupMember.student_id == student_id, GroupMember.removed_at.is_(None))) is not None


def _can_view_student(db: Session, principal: Principal, student_id: UUID) -> bool:
    if principal.role in EDITORS:
        return True
    if principal.role == "STUDENT":
        return db.scalar(select(Student.id).where(Student.organization_id == principal.organization_id, Student.id == student_id, Student.user_id == principal.user.id)) is not None
    if principal.role == "PARENT":
        return db.scalar(select(StudentParent.id).join(Parent, Parent.id == StudentParent.parent_id).where(StudentParent.organization_id == principal.organization_id, StudentParent.student_id == student_id, Parent.user_id == principal.user.id)) is not None
    return False


def _require_student_access(db: Session, principal: Principal, student_id: UUID):
    _record(db, Student, principal.organization_id, student_id)
    if not _can_view_student(db, principal, student_id):
        raise TuiroError("FORBIDDEN", "You cannot view this student's data.", 403)


def _group_payload(db: Session, group: Group) -> dict:
    members = db.scalar(select(GroupMember).where(GroupMember.group_id == group.id, GroupMember.removed_at.is_(None)).count()) if False else None
    # SQLAlchemy's select has no portable count() shorthand; keep this explicit.
    member_count = db.scalar(select(func.count()).select_from(GroupMember).where(GroupMember.group_id == group.id, GroupMember.removed_at.is_(None))) or 0
    next_schedule = db.scalar(select(GroupSchedule).where(GroupSchedule.group_id == group.id).order_by(GroupSchedule.day_of_week, GroupSchedule.start_time))
    return {"id": group.id, "name": group.name, "created_by": group.created_by, "created_at": group.created_at, "student_count": member_count, "next_class": {"day_of_week": next_schedule.day_of_week, "start_time": next_schedule.start_time, "end_time": next_schedule.end_time, "subject": next_schedule.subject} if next_schedule else None}


@router.get("")
def list_groups(principal: Principal = Depends(require_roles(*ALL_ROLES)), db: Session = Depends(get_db)):
    groups = db.scalars(select(Group).where(Group.organization_id == principal.organization_id).order_by(Group.created_at.desc())).all()
    if principal.role == "STUDENT":
        groups = [g for g in groups if db.scalar(select(GroupMember.id).join(Student, Student.id == GroupMember.student_id).where(GroupMember.group_id == g.id, GroupMember.removed_at.is_(None), Student.user_id == principal.user.id))]
    elif principal.role == "PARENT":
        groups = [g for g in groups if db.scalar(select(GroupMember.id).join(StudentParent, StudentParent.student_id == GroupMember.student_id).join(Parent, Parent.id == StudentParent.parent_id).where(GroupMember.group_id == g.id, GroupMember.removed_at.is_(None), Parent.user_id == principal.user.id))]
    return [_group_payload(db, group) for group in groups]


@router.post("", status_code=201)
def create_group(request: GroupInput, principal: Principal = Depends(require_roles(*ADMINS)), db: Session = Depends(get_db)):
    group_id = uuid4()
    group = Group(id=group_id, organization_id=principal.organization_id, name=request.name, created_by=principal.user.id)
    db.add(group)
    # Ensure ClassGroup stays synchronized with the exact same id
    cg = ClassGroup(id=group_id, organization_id=principal.organization_id, name=request.name, status="ACTIVE")
    db.add(cg)
    db.commit()
    db.refresh(group)
    return _group_payload(db, group)


@router.get("/{group_id:uuid}")
def group_detail(group_id: UUID, principal: Principal = Depends(require_roles(*ALL_ROLES)), db: Session = Depends(get_db)):
    group = _record(db, Group, principal.organization_id, group_id)
    # Access is also established by an active child/student membership.
    visible = group in [] or principal.role in STAFF
    if principal.role not in STAFF:
        visible = any(_can_view_student(db, principal, member.student_id) for member in db.scalars(select(GroupMember).where(GroupMember.group_id == group_id, GroupMember.removed_at.is_(None))))
    if not visible:
        raise TuiroError("FORBIDDEN", "You cannot view this group.", 403)
    return _group_payload(db, group)


@router.get("/{group_id:uuid}/members")
def group_members(group_id: UUID, principal: Principal = Depends(require_roles(*STAFF)), db: Session = Depends(get_db)):
    group_detail(group_id, principal, db)
    return db.scalars(select(Student).join(GroupMember, GroupMember.student_id == Student.id).where(GroupMember.group_id == group_id, GroupMember.removed_at.is_(None))).all()


@router.get("/students/{group_id:uuid}")
def group_roster(group_id: UUID, principal: Principal = Depends(require_roles(*STAFF)), db: Session = Depends(get_db)):
    """Compatibility roster endpoint used by the attendance flow.

    An empty group is valid and intentionally returns `[]`; a malformed UUID is
    rejected by FastAPI with JSON 422 and an unknown UUID receives our JSON 404.
    """
    return group_members(group_id, principal, db)


@router.post("/{group_id:uuid}/members/{student_id:uuid}", status_code=201)
def add_member(group_id: UUID, student_id: UUID, principal: Principal = Depends(require_roles(*ADMINS)), db: Session = Depends(get_db)):
    _record(db, Group, principal.organization_id, group_id); _record(db, Student, principal.organization_id, student_id)
    member = db.scalar(select(GroupMember).where(GroupMember.group_id == group_id, GroupMember.student_id == student_id))
    if member:
        member.removed_at = None
    else:
        member = GroupMember(organization_id=principal.organization_id, group_id=group_id, student_id=student_id); db.add(member)
    # Synchronize ClassStudent
    cs = db.scalar(select(ClassStudent).where(ClassStudent.organization_id == principal.organization_id, ClassStudent.class_id == group_id, ClassStudent.student_id == student_id))
    if not cs:
        db.add(ClassStudent(organization_id=principal.organization_id, class_id=group_id, student_id=student_id))
    # Sync existing group fees to this student
    fees = db.scalars(select(GroupFee).where(GroupFee.organization_id == principal.organization_id, GroupFee.group_id == group_id)).all()
    for gf in fees:
        org = db.get(Organization, principal.organization_id)
        org_today = get_org_today(org)
        bp = f"GF-{gf.id.hex[:24]}"
        existing = db.scalar(select(StudentFee).where(StudentFee.organization_id == principal.organization_id, StudentFee.student_id == student_id, StudentFee.billing_period == bp))
        if not existing:
            db.add(StudentFee(
                organization_id=principal.organization_id,
                student_id=student_id,
                billing_period=bp,
                amount=gf.amount,
                amount_due=gf.amount,
                due_date=gf.due_date,
                status="PENDING" if gf.due_date >= org_today else "OVERDUE",
            ))
    db.commit(); db.refresh(member); return member


@router.delete("/{group_id:uuid}/members/{student_id:uuid}", status_code=204)
def remove_member(group_id: UUID, student_id: UUID, principal: Principal = Depends(require_roles(*ADMINS)), db: Session = Depends(get_db)):
    member = db.scalar(select(GroupMember).where(GroupMember.organization_id == principal.organization_id, GroupMember.group_id == group_id, GroupMember.student_id == student_id, GroupMember.removed_at.is_(None)))
    if member is None:
        raise TuiroError("MEMBERSHIP_NOT_FOUND", "Active group membership not found.", 404)
    member.removed_at = datetime.now(timezone.utc)
    cs = db.scalar(select(ClassStudent).where(ClassStudent.organization_id == principal.organization_id, ClassStudent.class_id == group_id, ClassStudent.student_id == student_id))
    if cs:
        db.delete(cs)
    db.commit()


@router.get("/{group_id:uuid}/schedule")
def schedules(group_id: UUID, principal: Principal = Depends(require_roles(*ALL_ROLES)), db: Session = Depends(get_db)):
    group_detail(group_id, principal, db)
    return db.scalars(select(GroupSchedule).where(GroupSchedule.group_id == group_id).order_by(GroupSchedule.day_of_week, GroupSchedule.start_time)).all()


@router.post("/{group_id:uuid}/schedule", status_code=201)
def create_schedule(group_id: UUID, request: ScheduleInput, principal: Principal = Depends(require_roles(*ADMINS)), db: Session = Depends(get_db)):
    _record(db, Group, principal.organization_id, group_id)
    if request.end_time <= request.start_time:
        raise TuiroError("INVALID_SCHEDULE", "End time must be after start time.", 422)
    item = GroupSchedule(organization_id=principal.organization_id, group_id=group_id, **request.model_dump()); db.add(item); db.commit(); db.refresh(item); return item


def _validate_target(db: Session, org: UUID, group_id: UUID | None, student_id: UUID | None):
    if group_id: _record(db, Group, org, group_id)
    if student_id: _record(db, Student, org, student_id)


@router.post("/assignments", status_code=201)
def create_assignment(request: AssignmentInput, principal: Principal = Depends(require_roles(*STAFF)), db: Session = Depends(get_db)):
    _validate_target(db, principal.organization_id, request.group_id, request.student_id)
    if request.group_id:
        check_teacher_class_access(db, principal, request.group_id)
    if request.overrides_id: _record(db, Assignment, principal.organization_id, request.overrides_id)
    item = Assignment(organization_id=principal.organization_id, created_by=principal.user.id, **request.model_dump(exclude={"attachments"}), attachments=json.dumps(request.attachments))
    db.add(item); db.commit(); db.refresh(item); return item


@router.get("/assignments")
def list_assignments(type: str | None = None, group_id: UUID | None = None, principal: Principal = Depends(require_roles(*ALL_ROLES)), db: Session = Depends(get_db)):
    query = select(Assignment).where(Assignment.organization_id == principal.organization_id)
    if type:
        query = query.where(Assignment.type == type)
    if group_id:
        query = query.where(Assignment.group_id == group_id)
    query = query.order_by(Assignment.created_at.desc())
    items = db.scalars(query).all()
    results = []
    for item in items:
        group = db.get(Group, item.group_id) if item.group_id else None
        student = db.get(Student, item.student_id) if item.student_id else None
        target_name = group.name if group else (f"{student.first_name} {student.last_name}" if student else "Unknown")
        results.append({
            "id": str(item.id),
            "title": item.title,
            "description": item.description,
            "due_date": item.due_date.isoformat() if item.due_date else None,
            "type": item.type,
            "group_id": str(item.group_id) if item.group_id else None,
            "student_id": str(item.student_id) if item.student_id else None,
            "target_name": target_name,
            "source": "Group" if item.group_id else "Individual",
            "created_at": item.created_at.isoformat() if item.created_at else None,
        })
    return results


@router.delete("/assignments/{assignment_id:uuid}", status_code=204)
def delete_assignment(assignment_id: UUID, principal: Principal = Depends(require_roles(*STAFF)), db: Session = Depends(get_db)):
    item = _record(db, Assignment, principal.organization_id, assignment_id)
    if item.group_id:
        check_teacher_class_access(db, principal, item.group_id)
    db.delete(item)
    db.commit()


def _sync_group_fee_to_student_fees(db: Session, org_id: UUID, group_fee: GroupFee):
    org = db.get(Organization, org_id)
    org_today = get_org_today(org)
    student_ids = [group_fee.student_id] if group_fee.student_id else list(db.scalars(select(GroupMember.student_id).where(GroupMember.group_id == group_fee.group_id, GroupMember.removed_at.is_(None))))
    bp = f"GF-{group_fee.id.hex[:24]}"
    for sid in student_ids:
        existing = db.scalar(select(StudentFee).where(StudentFee.organization_id == org_id, StudentFee.student_id == sid, StudentFee.billing_period == bp))
        if not existing:
            sf = StudentFee(
                organization_id=org_id,
                student_id=sid,
                billing_period=bp,
                amount=group_fee.amount,
                amount_due=group_fee.amount,
                due_date=group_fee.due_date,
                status="PENDING" if group_fee.due_date >= org_today else "OVERDUE",
            )
            db.add(sf)


@router.post("/fees", status_code=201)
def create_fee(request: FeeInput, principal: Principal = Depends(require_roles(*ADMINS)), db: Session = Depends(get_db)):
    _validate_target(db, principal.organization_id, request.group_id, request.student_id)
    if request.overrides_id: _record(db, GroupFee, principal.organization_id, request.overrides_id)
    item = GroupFee(organization_id=principal.organization_id, created_by=principal.user.id, **request.model_dump())
    db.add(item)
    db.flush()
    _sync_group_fee_to_student_fees(db, principal.organization_id, item)
    db.commit()
    db.refresh(item)
    return item


def _fee_status(fee: GroupFee, payment: FeePayment | None, org_today: date | None = None) -> str:
    if payment and payment.amount_paid >= fee.amount:
        return "PAID"
    today_val = org_today if org_today is not None else date.today()
    return "OVERDUE" if fee.due_date < today_val else "PENDING"


def _fee_rows(db: Session, org: UUID):
    org_rec = db.get(Organization, org)
    org_today = get_org_today(org_rec)
    fees = db.scalars(select(GroupFee).where(GroupFee.organization_id == org)).all()
    rows = []
    for fee in fees:
        student_ids = [fee.student_id] if fee.student_id else list(db.scalars(select(GroupMember.student_id).where(GroupMember.group_id == fee.group_id, GroupMember.removed_at.is_(None))))
        for student_id in student_ids:
            payment = db.scalar(select(FeePayment).where(FeePayment.fee_id == fee.id, FeePayment.student_id == student_id))
            student = db.get(Student, student_id)
            status = _fee_status(fee, payment, org_today)
            rows.append({"fee_id": fee.id, "student_id": student_id, "student_name": f"{student.first_name} {student.last_name}".strip() if student else "Student", "group_id": fee.group_id, "amount": fee.amount, "amount_paid": payment.amount_paid if payment else Decimal("0"), "outstanding_amount": max(Decimal("0"), fee.amount - (payment.amount_paid if payment else 0)), "due_date": fee.due_date, "status": status, "source": "Group" if fee.group_id else "Individual"})
    return rows


@router.get("/fees/needs-attention")
def group_fee_needs_attention(principal: Principal = Depends(require_roles(*ADMINS)), db: Session = Depends(get_db)):
    rows = _fee_rows(db, principal.organization_id)
    return [row for row in rows if row["status"] != "PAID"]


@router.post("/fees/{fee_id:uuid}/payments", status_code=201)
def pay_group_fee(fee_id: UUID, request: FeePaymentInput, principal: Principal = Depends(require_roles(*ADMINS)), db: Session = Depends(get_db)):
    fee = db.scalar(select(GroupFee).where(GroupFee.id == fee_id, GroupFee.organization_id == principal.organization_id).with_for_update())
    if fee is None:
        raise TuiroError("RESOURCE_NOT_FOUND", "The requested resource was not found.", 404)
    _record(db, Student, principal.organization_id, request.student_id)
    if fee.group_id and not _active_member(db, principal.organization_id, fee.group_id, request.student_id):
        raise TuiroError("FEE_NOT_APPLICABLE", "This group fee does not apply to this student.", 409)

    org = db.get(Organization, principal.organization_id)
    org_today = get_org_today(org)

    # 1. Ensure matching StudentFee exists
    bp = f"GF-{fee.id.hex[:24]}"
    student_fee = db.scalar(select(StudentFee).where(StudentFee.organization_id == principal.organization_id, StudentFee.student_id == request.student_id, StudentFee.billing_period == bp).with_for_update())
    if student_fee is None:
        student_fee = StudentFee(
            organization_id=principal.organization_id,
            student_id=request.student_id,
            billing_period=bp,
            amount=fee.amount,
            amount_due=fee.amount,
            due_date=fee.due_date,
            status="PENDING" if fee.due_date >= org_today else "OVERDUE",
        )
        db.add(student_fee)
        db.flush()

    # 2. Get or create FeePayment
    payment = db.scalar(select(FeePayment).where(FeePayment.fee_id == fee_id, FeePayment.student_id == request.student_id))
    if payment is None:
        payment = FeePayment(fee_id=fee_id, student_id=request.student_id, amount_paid=Decimal("0"), status="PENDING")
        db.add(payment)
        db.flush()

    current_paid = payment.amount_paid or Decimal("0")
    remaining = max(Decimal("0"), fee.amount - current_paid)
    if request.amount_paid > remaining:
        raise TuiroError("PAYMENT_EXCEEDS_BALANCE", "Payment is greater than the outstanding balance.", 400)

    payment.amount_paid = current_paid + request.amount_paid
    payment.paid_on = request.paid_on or org_today
    payment.status = _fee_status(fee, payment, org_today)

    # 3. Create real Payment
    real_payment = Payment(
        organization_id=principal.organization_id,
        fee_id=student_fee.id,
        student_id=request.student_id,
        amount=request.amount_paid,
        payment_date=request.paid_on or org_today,
        payment_method="CASH",
        notes=f"Group fee payment for {fee_id}",
        recorded_by=principal.user.id,
    )
    db.add(real_payment)
    db.flush()

    # 4. Update StudentFee status
    total_sf_paid = db.scalar(select(func.coalesce(func.sum(Payment.amount), 0)).where(Payment.fee_id == student_fee.id)) or Decimal("0")
    if total_sf_paid >= student_fee.amount_due:
        student_fee.status = "PAID"
    elif total_sf_paid > 0:
        student_fee.status = "PARTIAL"
    else:
        student_fee.status = "OVERDUE" if student_fee.due_date < org_today else "PENDING"

    # 5. Update GroupFee status if applicable
    if fee.student_id:
        fee.status = payment.status
    else:
        active_member_ids = list(db.scalars(select(GroupMember.student_id).where(GroupMember.group_id == fee.group_id, GroupMember.removed_at.is_(None))))
        paid_count = db.scalar(select(func.count()).select_from(FeePayment).where(FeePayment.fee_id == fee.id, FeePayment.status == "PAID", FeePayment.student_id.in_(active_member_ids))) or 0
        if active_member_ids and paid_count >= len(active_member_ids):
            fee.status = "PAID"

    # 6. Create real Receipt
    receipt_number = generate_receipt_number(db, principal.organization_id)
    receipt = Receipt(
        organization_id=principal.organization_id,
        payment_id=real_payment.id,
        receipt_number=receipt_number,
    )
    db.add(receipt)
    db.add(AuditLog(organization_id=principal.organization_id, user_id=principal.user.id, action="payment_created", entity_type="payment", entity_id=real_payment.id))

    db.commit()
    db.refresh(payment)
    return payment


@router.post("/{group_id:uuid}/attendance", status_code=201)
def save_group_attendance(group_id: UUID, request: GroupAttendanceInput, principal: Principal = Depends(require_roles(*STAFF)), db: Session = Depends(get_db)):
    _record(db, Group, principal.organization_id, group_id)
    check_teacher_class_access(db, principal, group_id)
    active_ids = set(db.scalars(select(GroupMember.student_id).where(GroupMember.group_id == group_id, GroupMember.removed_at.is_(None))))
    if {record.student_id for record in request.records} - active_ids:
        raise TuiroError("INVALID_ROSTER", "Attendance may only be saved for active group members.", 422)
    session = db.scalar(select(GroupAttendanceSession).where(GroupAttendanceSession.organization_id == principal.organization_id, GroupAttendanceSession.group_id == group_id, GroupAttendanceSession.session_date == request.session_date))
    if session is None:
        session = GroupAttendanceSession(organization_id=principal.organization_id, group_id=group_id, session_date=request.session_date, created_by=principal.user.id); db.add(session); db.flush()
    else:
        db.query(GroupAttendanceRecord).filter(GroupAttendanceRecord.session_id == session.id).delete()
    db.add_all([GroupAttendanceRecord(session_id=session.id, **record.model_dump()) for record in request.records])
    db.commit(); return {"id": session.id, "group_id": group_id, "session_date": request.session_date, "records": len(request.records)}


@router.get("/{group_id:uuid}/attendance")
def group_attendance(group_id: UUID, session_date: date = Query(...), principal: Principal = Depends(require_roles(*STAFF)), db: Session = Depends(get_db)):
    group_detail(group_id, principal, db)
    session = db.scalar(select(GroupAttendanceSession).where(GroupAttendanceSession.organization_id == principal.organization_id, GroupAttendanceSession.group_id == group_id, GroupAttendanceSession.session_date == session_date))
    return {"session": session, "records": [] if session is None else db.scalars(select(GroupAttendanceRecord).where(GroupAttendanceRecord.session_id == session.id)).all()}


@router.get("/{group_id:uuid}/attendance/history")
def group_attendance_history(group_id: UUID, principal: Principal = Depends(require_roles(*STAFF)), db: Session = Depends(get_db)):
    """Daily roll-up for a group; individual facts remain in attendance records."""
    group_detail(group_id, principal, db)
    sessions = db.scalars(select(GroupAttendanceSession).where(GroupAttendanceSession.organization_id == principal.organization_id, GroupAttendanceSession.group_id == group_id).order_by(GroupAttendanceSession.session_date.desc())).all()
    return [{"id": session.id, "session_date": session.session_date, "records": db.scalar(select(func.count()).select_from(GroupAttendanceRecord).where(GroupAttendanceRecord.session_id == session.id)) or 0} for session in sessions]


@router.get("/students/{student_id:uuid}/attendance")
def student_group_attendance(student_id: UUID, principal: Principal = Depends(require_roles(*ALL_ROLES)), db: Session = Depends(get_db)):
    _require_student_access(db, principal, student_id)
    return db.scalars(select(GroupAttendanceRecord).join(GroupAttendanceSession, GroupAttendanceSession.id == GroupAttendanceRecord.session_id).where(GroupAttendanceSession.organization_id == principal.organization_id, GroupAttendanceRecord.student_id == student_id).order_by(GroupAttendanceSession.session_date.desc())).all()


def _merged(db: Session, org: UUID, student_id: UUID):
    org_rec = db.get(Organization, org)
    org_today = get_org_today(org_rec)
    group_ids = list(db.scalars(select(GroupMember.group_id).where(GroupMember.organization_id == org, GroupMember.student_id == student_id, GroupMember.removed_at.is_(None))))
    assignments = list(db.scalars(select(Assignment).where(Assignment.organization_id == org, (Assignment.student_id == student_id) | (Assignment.group_id.in_(group_ids) if group_ids else False))))
    fees = list(db.scalars(select(GroupFee).where(GroupFee.organization_id == org, (GroupFee.student_id == student_id) | (GroupFee.group_id.in_(group_ids) if group_ids else False))))
    assignment_overrides = {a.overrides_id for a in assignments if a.student_id == student_id and a.overrides_id}
    fee_overrides = {f.overrides_id for f in fees if f.student_id == student_id and f.overrides_id}
    fee_items = []
    for f in fees:
        if f.id in fee_overrides and f.group_id:
            continue
        fp = db.scalar(select(FeePayment).where(FeePayment.fee_id == f.id, FeePayment.student_id == student_id))
        st = _fee_status(f, fp, org_today)
        fee_items.append({
            "id": f.id,
            "amount": f.amount,
            "due_date": f.due_date,
            "status": st,
            "source": "Individual" if f.student_id else "Group",
            "overrides_id": f.overrides_id,
        })
    return {
        "assignments": [{"id": a.id, "title": a.title, "description": a.description, "due_date": a.due_date, "type": a.type, "attachments": json.loads(a.attachments), "source": "Individual" if a.student_id else "Group", "group_name": _record(db, Group, org, a.group_id).name if a.group_id else None, "overrides_id": a.overrides_id} for a in assignments if not (a.id in assignment_overrides and a.group_id)],
        "fees": fee_items,
        "schedule": list(db.scalars(select(GroupSchedule).where(GroupSchedule.organization_id == org, GroupSchedule.group_id.in_(group_ids) if group_ids else False).order_by(GroupSchedule.day_of_week, GroupSchedule.start_time))),
    }


@router.get("/students/{student_id}/view")
def student_merged_view(student_id: UUID, principal: Principal = Depends(require_roles(*PORTAL_READ)), db: Session = Depends(get_db)):
    _require_student_access(db, principal, student_id)
    return _merged(db, principal.organization_id, student_id)


@router.post("/{group_id:uuid}/chat", status_code=201)
def post_group_message(group_id: UUID, request: MessageInput, principal: Principal = Depends(require_roles(*ALL_ROLES)), db: Session = Depends(get_db)):
    _record(db, Group, principal.organization_id, group_id)
    if principal.role == "STUDENT" and not db.scalar(select(GroupMember.id).join(Student, Student.id == GroupMember.student_id).where(GroupMember.group_id == group_id, GroupMember.removed_at.is_(None), Student.user_id == principal.user.id)):
        raise TuiroError("FORBIDDEN", "You are not an active member of this group.", 403)
    thread = db.scalar(select(ChatThread).where(ChatThread.organization_id == principal.organization_id, ChatThread.group_id == group_id))
    if thread is None:
        thread = ChatThread(organization_id=principal.organization_id, type="GROUP", group_id=group_id); db.add(thread); db.flush()
    message = ChatMessage(thread_id=thread.id, sender_id=principal.user.id, text=request.text, attachment=request.attachment)
    db.add(message); db.commit(); db.refresh(message); return message


@router.get("/{group_id:uuid}/chat")
def group_messages(group_id: UUID, principal: Principal = Depends(require_roles(*ALL_ROLES)), db: Session = Depends(get_db)):
    group_detail(group_id, principal, db)
    if principal.role == "PARENT":
        raise TuiroError("FORBIDDEN", "Parents do not have chat access.", 403)
    thread = db.scalar(select(ChatThread).where(ChatThread.organization_id == principal.organization_id, ChatThread.group_id == group_id))
    return [] if thread is None else db.scalars(select(ChatMessage).where(ChatMessage.thread_id == thread.id).order_by(ChatMessage.timestamp)).all()


def _find_direct_thread(db: Session, org: UUID, first_user_id: UUID, second_user_id: UUID) -> ChatThread | None:
    candidate_threads = db.scalars(select(ChatThread).join(ChatParticipant).where(ChatThread.organization_id == org, ChatThread.type == "DIRECT", ChatParticipant.user_id == first_user_id)).all()
    for thread in candidate_threads:
        participants = set(db.scalars(select(ChatParticipant.user_id).where(ChatParticipant.thread_id == thread.id)))
        if participants == {first_user_id, second_user_id}:
            return thread
    return None


def _direct_thread(db: Session, org: UUID, first_user_id: UUID, second_user_id: UUID) -> ChatThread:
    thread = _find_direct_thread(db, org, first_user_id, second_user_id)
    if thread:
        return thread
    thread = ChatThread(organization_id=org, type="DIRECT")
    db.add(thread); db.flush()
    db.add_all([ChatParticipant(thread_id=thread.id, user_id=first_user_id), ChatParticipant(thread_id=thread.id, user_id=second_user_id)])
    return thread


@router.post("/chats/direct/{participant_id:uuid}", status_code=201)
def post_direct_message(participant_id: UUID, request: MessageInput, principal: Principal = Depends(require_roles(*ALL_ROLES)), db: Session = Depends(get_db)):
    participant = db.scalar(select(OrganizationMember).where(OrganizationMember.organization_id == principal.organization_id, OrganizationMember.user_id == participant_id))
    if participant_id == principal.user.id or participant is None or participant.role not in ALL_ROLES:
        raise TuiroError("RESOURCE_NOT_FOUND", "The requested participant was not found.", 404)
    thread = _direct_thread(db, principal.organization_id, principal.user.id, participant_id)
    message = ChatMessage(thread_id=thread.id, sender_id=principal.user.id, text=request.text, attachment=request.attachment)
    db.add(message); db.commit(); db.refresh(message); return message


@router.get("/chats/direct/{participant_id:uuid}")
def direct_messages(participant_id: UUID, principal: Principal = Depends(require_roles(*ALL_ROLES)), db: Session = Depends(get_db)):
    participant = db.scalar(select(OrganizationMember).where(OrganizationMember.organization_id == principal.organization_id, OrganizationMember.user_id == participant_id))
    if participant_id == principal.user.id or participant is None or participant.role not in ALL_ROLES:
        raise TuiroError("RESOURCE_NOT_FOUND", "The requested participant was not found.", 404)
    thread = _find_direct_thread(db, principal.organization_id, principal.user.id, participant_id)
    if thread is None:
        return []
    return db.scalars(select(ChatMessage).where(ChatMessage.thread_id == thread.id).order_by(ChatMessage.timestamp)).all()
