"""Group-first CMS endpoints.

Items are stored once against a group.  The student view is a projection over
active memberships, so removing a member immediately removes inherited work,
fees, and schedules without mutating historical records.
"""
from __future__ import annotations

import json
from datetime import date, datetime, timezone
from decimal import Decimal
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field, model_validator
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.dependencies import Principal, require_authenticated_user, require_roles
from app.core.errors import TuiroError
from app.db import get_db
from app.models import Assignment, ChatMessage, ChatParticipant, ChatThread, ClassGroup, ClassStudent, FeePayment, Group, GroupAttendanceRecord, GroupAttendanceSession, GroupFee, GroupMember, GroupSchedule, OrganizationMember, Parent, Student, StudentParent, User

router = APIRouter(prefix="/groups", tags=["groups"])
EDITORS = ("OWNER", "ADMIN", "TEACHER")


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
def list_groups(principal: Principal = Depends(require_authenticated_user), db: Session = Depends(get_db)):
    groups = db.scalars(select(Group).where(Group.organization_id == principal.organization_id).order_by(Group.created_at.desc())).all()
    if principal.role == "STUDENT":
        groups = [g for g in groups if db.scalar(select(GroupMember.id).join(Student, Student.id == GroupMember.student_id).where(GroupMember.group_id == g.id, GroupMember.removed_at.is_(None), Student.user_id == principal.user.id))]
    elif principal.role == "PARENT":
        groups = [g for g in groups if db.scalar(select(GroupMember.id).join(StudentParent, StudentParent.student_id == GroupMember.student_id).join(Parent, Parent.id == StudentParent.parent_id).where(GroupMember.group_id == g.id, GroupMember.removed_at.is_(None), Parent.user_id == principal.user.id))]
    return [_group_payload(db, group) for group in groups]


@router.post("", status_code=201)
def create_group(request: GroupInput, principal: Principal = Depends(require_roles(*EDITORS)), db: Session = Depends(get_db)):
    group = Group(organization_id=principal.organization_id, name=request.name, created_by=principal.user.id)
    db.add(group)
    # Ensure ClassGroup stays synchronized
    cg = db.scalar(select(ClassGroup).where(ClassGroup.id == group.id))
    if not cg:
        cg = ClassGroup(id=group.id, organization_id=principal.organization_id, name=request.name, status="ACTIVE")
        db.add(cg)
    db.commit(); db.refresh(group)
    return _group_payload(db, group)


@router.get("/{group_id:uuid}")
def group_detail(group_id: UUID, principal: Principal = Depends(require_authenticated_user), db: Session = Depends(get_db)):
    group = _record(db, Group, principal.organization_id, group_id)
    # Access is also established by an active child/student membership.
    visible = group in [] or principal.role in EDITORS
    if principal.role not in EDITORS:
        visible = any(_can_view_student(db, principal, member.student_id) for member in db.scalars(select(GroupMember).where(GroupMember.group_id == group_id, GroupMember.removed_at.is_(None))))
    if not visible:
        raise TuiroError("FORBIDDEN", "You cannot view this group.", 403)
    return _group_payload(db, group)


@router.get("/{group_id:uuid}/members")
def group_members(group_id: UUID, principal: Principal = Depends(require_authenticated_user), db: Session = Depends(get_db)):
    group_detail(group_id, principal, db)
    return db.scalars(select(Student).join(GroupMember, GroupMember.student_id == Student.id).where(GroupMember.group_id == group_id, GroupMember.removed_at.is_(None))).all()


@router.get("/students/{group_id:uuid}")
def group_roster(group_id: UUID, principal: Principal = Depends(require_authenticated_user), db: Session = Depends(get_db)):
    """Compatibility roster endpoint used by the attendance flow.

    An empty group is valid and intentionally returns `[]`; a malformed UUID is
    rejected by FastAPI with JSON 422 and an unknown UUID receives our JSON 404.
    """
    return group_members(group_id, principal, db)


@router.post("/{group_id:uuid}/members/{student_id:uuid}", status_code=201)
def add_member(group_id: UUID, student_id: UUID, principal: Principal = Depends(require_roles(*EDITORS)), db: Session = Depends(get_db)):
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
    db.commit(); db.refresh(member); return member


@router.delete("/{group_id:uuid}/members/{student_id:uuid}", status_code=204)
def remove_member(group_id: UUID, student_id: UUID, principal: Principal = Depends(require_roles(*EDITORS)), db: Session = Depends(get_db)):
    member = db.scalar(select(GroupMember).where(GroupMember.organization_id == principal.organization_id, GroupMember.group_id == group_id, GroupMember.student_id == student_id, GroupMember.removed_at.is_(None)))
    if member is None:
        raise TuiroError("MEMBERSHIP_NOT_FOUND", "Active group membership not found.", 404)
    member.removed_at = datetime.now(timezone.utc)
    cs = db.scalar(select(ClassStudent).where(ClassStudent.organization_id == principal.organization_id, ClassStudent.class_id == group_id, ClassStudent.student_id == student_id))
    if cs:
        db.delete(cs)
    db.commit()


@router.get("/{group_id:uuid}/schedule")
def schedules(group_id: UUID, principal: Principal = Depends(require_authenticated_user), db: Session = Depends(get_db)):
    group_detail(group_id, principal, db)
    return db.scalars(select(GroupSchedule).where(GroupSchedule.group_id == group_id).order_by(GroupSchedule.day_of_week, GroupSchedule.start_time)).all()


@router.post("/{group_id:uuid}/schedule", status_code=201)
def create_schedule(group_id: UUID, request: ScheduleInput, principal: Principal = Depends(require_roles(*EDITORS)), db: Session = Depends(get_db)):
    _record(db, Group, principal.organization_id, group_id)
    if request.end_time <= request.start_time:
        raise TuiroError("INVALID_SCHEDULE", "End time must be after start time.", 422)
    item = GroupSchedule(organization_id=principal.organization_id, group_id=group_id, **request.model_dump()); db.add(item); db.commit(); db.refresh(item); return item


def _validate_target(db: Session, org: UUID, group_id: UUID | None, student_id: UUID | None):
    if group_id: _record(db, Group, org, group_id)
    if student_id: _record(db, Student, org, student_id)


@router.post("/assignments", status_code=201)
def create_assignment(request: AssignmentInput, principal: Principal = Depends(require_roles(*EDITORS)), db: Session = Depends(get_db)):
    _validate_target(db, principal.organization_id, request.group_id, request.student_id)
    if request.overrides_id: _record(db, Assignment, principal.organization_id, request.overrides_id)
    item = Assignment(organization_id=principal.organization_id, created_by=principal.user.id, **request.model_dump(exclude={"attachments"}), attachments=json.dumps(request.attachments))
    db.add(item); db.commit(); db.refresh(item); return item


@router.get("/assignments")
def list_assignments(type: str | None = None, group_id: UUID | None = None, principal: Principal = Depends(require_authenticated_user), db: Session = Depends(get_db)):
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
def delete_assignment(assignment_id: UUID, principal: Principal = Depends(require_roles(*EDITORS)), db: Session = Depends(get_db)):
    item = _record(db, Assignment, principal.organization_id, assignment_id)
    db.delete(item)
    db.commit()


@router.post("/fees", status_code=201)
def create_fee(request: FeeInput, principal: Principal = Depends(require_roles(*EDITORS)), db: Session = Depends(get_db)):
    _validate_target(db, principal.organization_id, request.group_id, request.student_id)
    if request.overrides_id: _record(db, GroupFee, principal.organization_id, request.overrides_id)
    item = GroupFee(organization_id=principal.organization_id, created_by=principal.user.id, **request.model_dump())
    db.add(item); db.commit(); db.refresh(item); return item


def _fee_status(fee: GroupFee, payment: FeePayment | None) -> str:
    if payment and payment.amount_paid >= fee.amount:
        return "PAID"
    return "OVERDUE" if fee.due_date < date.today() else "PENDING"


def _fee_rows(db: Session, org: UUID):
    fees = db.scalars(select(GroupFee).where(GroupFee.organization_id == org)).all()
    rows = []
    for fee in fees:
        student_ids = [fee.student_id] if fee.student_id else list(db.scalars(select(GroupMember.student_id).where(GroupMember.group_id == fee.group_id, GroupMember.removed_at.is_(None))))
        for student_id in student_ids:
            payment = db.scalar(select(FeePayment).where(FeePayment.fee_id == fee.id, FeePayment.student_id == student_id))
            student = db.get(Student, student_id)
            status = _fee_status(fee, payment)
            rows.append({"fee_id": fee.id, "student_id": student_id, "student_name": f"{student.first_name} {student.last_name}".strip() if student else "Student", "group_id": fee.group_id, "amount": fee.amount, "amount_paid": payment.amount_paid if payment else Decimal("0"), "outstanding_amount": max(Decimal("0"), fee.amount - (payment.amount_paid if payment else 0)), "due_date": fee.due_date, "status": status, "source": "Group" if fee.group_id else "Individual"})
    return rows


@router.get("/fees/needs-attention")
def group_fee_needs_attention(principal: Principal = Depends(require_authenticated_user), db: Session = Depends(get_db)):
    rows = _fee_rows(db, principal.organization_id)
    if principal.role not in EDITORS:
        rows = [row for row in rows if _can_view_student(db, principal, row["student_id"])]
    return [row for row in rows if row["status"] != "PAID"]


@router.post("/fees/{fee_id:uuid}/payments", status_code=201)
def pay_group_fee(fee_id: UUID, request: FeePaymentInput, principal: Principal = Depends(require_roles(*EDITORS)), db: Session = Depends(get_db)):
    fee = _record(db, GroupFee, principal.organization_id, fee_id)
    _record(db, Student, principal.organization_id, request.student_id)
    if fee.group_id and not _active_member(db, principal.organization_id, fee.group_id, request.student_id):
        raise TuiroError("FEE_NOT_APPLICABLE", "This group fee does not apply to this student.", 409)
    payment = db.scalar(select(FeePayment).where(FeePayment.fee_id == fee_id, FeePayment.student_id == request.student_id))
    if payment is None:
        payment = FeePayment(fee_id=fee_id, student_id=request.student_id, amount_paid=0, status="PENDING"); db.add(payment)
    payment.amount_paid = min(fee.amount, payment.amount_paid + request.amount_paid)
    payment.paid_on = request.paid_on
    payment.status = _fee_status(fee, payment)
    db.commit(); db.refresh(payment); return payment


@router.post("/{group_id:uuid}/attendance", status_code=201)
def save_group_attendance(group_id: UUID, request: GroupAttendanceInput, principal: Principal = Depends(require_roles(*EDITORS)), db: Session = Depends(get_db)):
    _record(db, Group, principal.organization_id, group_id)
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
def group_attendance(group_id: UUID, session_date: date = Query(...), principal: Principal = Depends(require_authenticated_user), db: Session = Depends(get_db)):
    group_detail(group_id, principal, db)
    session = db.scalar(select(GroupAttendanceSession).where(GroupAttendanceSession.organization_id == principal.organization_id, GroupAttendanceSession.group_id == group_id, GroupAttendanceSession.session_date == session_date))
    return {"session": session, "records": [] if session is None else db.scalars(select(GroupAttendanceRecord).where(GroupAttendanceRecord.session_id == session.id)).all()}


@router.get("/{group_id:uuid}/attendance/history")
def group_attendance_history(group_id: UUID, principal: Principal = Depends(require_authenticated_user), db: Session = Depends(get_db)):
    """Daily roll-up for a group; individual facts remain in attendance records."""
    group_detail(group_id, principal, db)
    sessions = db.scalars(select(GroupAttendanceSession).where(GroupAttendanceSession.organization_id == principal.organization_id, GroupAttendanceSession.group_id == group_id).order_by(GroupAttendanceSession.session_date.desc())).all()
    return [{"id": session.id, "session_date": session.session_date, "records": db.scalar(select(func.count()).select_from(GroupAttendanceRecord).where(GroupAttendanceRecord.session_id == session.id)) or 0} for session in sessions]


@router.get("/students/{student_id:uuid}/attendance")
def student_group_attendance(student_id: UUID, principal: Principal = Depends(require_authenticated_user), db: Session = Depends(get_db)):
    _require_student_access(db, principal, student_id)
    return db.scalars(select(GroupAttendanceRecord).join(GroupAttendanceSession, GroupAttendanceSession.id == GroupAttendanceRecord.session_id).where(GroupAttendanceSession.organization_id == principal.organization_id, GroupAttendanceRecord.student_id == student_id).order_by(GroupAttendanceSession.session_date.desc())).all()


def _merged(db: Session, org: UUID, student_id: UUID):
    group_ids = list(db.scalars(select(GroupMember.group_id).where(GroupMember.organization_id == org, GroupMember.student_id == student_id, GroupMember.removed_at.is_(None))))
    assignments = list(db.scalars(select(Assignment).where(Assignment.organization_id == org, (Assignment.student_id == student_id) | (Assignment.group_id.in_(group_ids) if group_ids else False))))
    fees = list(db.scalars(select(GroupFee).where(GroupFee.organization_id == org, (GroupFee.student_id == student_id) | (GroupFee.group_id.in_(group_ids) if group_ids else False))))
    assignment_overrides = {a.overrides_id for a in assignments if a.student_id == student_id and a.overrides_id}
    fee_overrides = {f.overrides_id for f in fees if f.student_id == student_id and f.overrides_id}
    return {
        "assignments": [{"id": a.id, "title": a.title, "description": a.description, "due_date": a.due_date, "type": a.type, "attachments": json.loads(a.attachments), "source": "Individual" if a.student_id else "Group", "group_name": _record(db, Group, org, a.group_id).name if a.group_id else None, "overrides_id": a.overrides_id} for a in assignments if not (a.id in assignment_overrides and a.group_id)],
        "fees": [{"id": f.id, "amount": f.amount, "due_date": f.due_date, "status": f.status, "source": "Individual" if f.student_id else "Group", "overrides_id": f.overrides_id} for f in fees if not (f.id in fee_overrides and f.group_id)],
        "schedule": list(db.scalars(select(GroupSchedule).where(GroupSchedule.organization_id == org, GroupSchedule.group_id.in_(group_ids) if group_ids else False).order_by(GroupSchedule.day_of_week, GroupSchedule.start_time))),
    }


@router.get("/students/{student_id}/view")
def student_merged_view(student_id: UUID, principal: Principal = Depends(require_authenticated_user), db: Session = Depends(get_db)):
    _require_student_access(db, principal, student_id)
    return _merged(db, principal.organization_id, student_id)


@router.post("/{group_id:uuid}/chat", status_code=201)
def post_group_message(group_id: UUID, request: MessageInput, principal: Principal = Depends(require_roles(*EDITORS, "STUDENT")), db: Session = Depends(get_db)):
    _record(db, Group, principal.organization_id, group_id)
    if principal.role == "STUDENT" and not db.scalar(select(GroupMember.id).join(Student, Student.id == GroupMember.student_id).where(GroupMember.group_id == group_id, GroupMember.removed_at.is_(None), Student.user_id == principal.user.id)):
        raise TuiroError("FORBIDDEN", "You are not an active member of this group.", 403)
    thread = db.scalar(select(ChatThread).where(ChatThread.organization_id == principal.organization_id, ChatThread.group_id == group_id))
    if thread is None:
        thread = ChatThread(organization_id=principal.organization_id, type="GROUP", group_id=group_id); db.add(thread); db.flush()
    message = ChatMessage(thread_id=thread.id, sender_id=principal.user.id, text=request.text, attachment=request.attachment)
    db.add(message); db.commit(); db.refresh(message); return message


@router.get("/{group_id:uuid}/chat")
def group_messages(group_id: UUID, principal: Principal = Depends(require_authenticated_user), db: Session = Depends(get_db)):
    group_detail(group_id, principal, db)
    if principal.role == "PARENT":
        raise TuiroError("FORBIDDEN", "Parents do not have chat access.", 403)
    thread = db.scalar(select(ChatThread).where(ChatThread.organization_id == principal.organization_id, ChatThread.group_id == group_id))
    return [] if thread is None else db.scalars(select(ChatMessage).where(ChatMessage.thread_id == thread.id).order_by(ChatMessage.timestamp)).all()


def _direct_thread(db: Session, org: UUID, first_user_id: UUID, second_user_id: UUID) -> ChatThread:
    candidate_threads = db.scalars(select(ChatThread).join(ChatParticipant).where(ChatThread.organization_id == org, ChatThread.type == "DIRECT", ChatParticipant.user_id == first_user_id)).all()
    for thread in candidate_threads:
        participants = set(db.scalars(select(ChatParticipant.user_id).where(ChatParticipant.thread_id == thread.id)))
        if participants == {first_user_id, second_user_id}:
            return thread
    thread = ChatThread(organization_id=org, type="DIRECT")
    db.add(thread); db.flush()
    db.add_all([ChatParticipant(thread_id=thread.id, user_id=first_user_id), ChatParticipant(thread_id=thread.id, user_id=second_user_id)])
    return thread


@router.post("/chats/direct/{participant_id:uuid}", status_code=201)
def post_direct_message(participant_id: UUID, request: MessageInput, principal: Principal = Depends(require_roles(*EDITORS, "STUDENT")), db: Session = Depends(get_db)):
    participant = db.scalar(select(OrganizationMember).where(OrganizationMember.organization_id == principal.organization_id, OrganizationMember.user_id == participant_id))
    if participant_id == principal.user.id or participant is None or participant.role not in {*EDITORS, "STUDENT"}:
        raise TuiroError("RESOURCE_NOT_FOUND", "The requested participant was not found.", 404)
    thread = _direct_thread(db, principal.organization_id, principal.user.id, participant_id)
    message = ChatMessage(thread_id=thread.id, sender_id=principal.user.id, text=request.text, attachment=request.attachment)
    db.add(message); db.commit(); db.refresh(message); return message


@router.get("/chats/direct/{participant_id:uuid}")
def direct_messages(participant_id: UUID, principal: Principal = Depends(require_roles(*EDITORS, "STUDENT")), db: Session = Depends(get_db)):
    thread = _direct_thread(db, principal.organization_id, principal.user.id, participant_id)
    db.commit()  # persist a newly opened thread even when it has no messages
    return db.scalars(select(ChatMessage).where(ChatMessage.thread_id == thread.id).order_by(ChatMessage.timestamp)).all()
