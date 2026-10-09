from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import StreamingResponse
from io import BytesIO, StringIO
import csv
import json
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.dependencies import Principal, require_authenticated_user, require_roles
from app.core.errors import TuiroError
from app.core.permissions import (
    check_parent_student_access,
    check_student_self_access,
    check_teacher_class_access,
    get_parent_student_ids,
    get_student_self_id,
)
from app.core.timezone import get_org_now, get_org_today
from app.db import get_db
from app.models import AcademicTest, AttendanceRecord, AttendanceSession, AuditLog, ClassGroup, ClassStudent, ClassTeacher, GroupAttendanceRecord, GroupAttendanceSession, GroupMember, Homework, Organization, OrganizationMember, Payment, Receipt, ScheduleEntry, Student, StudentFee, StudentParent, Parent, Teacher, TestMark, User
from app.services.payment_provider import get_payment_provider
from app.services.notifications import send_notification
from app.services.receipts import build_receipt_pdf, generate_receipt_number

router = APIRouter()


class AttendanceRecordInput(BaseModel):
    student_id: UUID
    status: str = Field(pattern="^(PRESENT|ABSENT|LATE|EXCUSED)$")
    notes: str | None = None


class AttendanceSessionInput(BaseModel):
    class_id: UUID
    session_date: date
    teacher_id: UUID | None = None
    records: list[AttendanceRecordInput] = []


class FeeGenerationInput(BaseModel):
    billing_period: str = Field(min_length=1, max_length=30)
    amount: Decimal = Field(gt=0)
    due_date: date


class FeeCreateInput(FeeGenerationInput):
    student_id: UUID


class PaymentInput(BaseModel):
    fee_id: UUID
    amount: Decimal = Field(gt=0)
    payment_date: date = Field(default_factory=date.today)
    payment_method: str = "OTHER"
    transaction_reference: str | None = None
    notes: str | None = None


class CreateOrderInput(BaseModel):
    fee_id: UUID


class VerifyPaymentInput(BaseModel):
    fee_id: UUID
    order_id: str
    payment_id: str
    signature: str


class HomeworkInput(BaseModel):
    class_id: UUID
    title: str = Field(min_length=1, max_length=200)
    description: str | None = None
    due_date: date | None = None


class HomeworkUpdate(BaseModel):
    class_id: UUID | None = None
    title: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = None
    due_date: date | None = None


class TestInput(BaseModel):
    class_id: UUID
    name: str = Field(min_length=1, max_length=160)
    subject: str | None = None
    test_date: date
    maximum_marks: Decimal = Field(gt=0)


class TestUpdate(BaseModel):
    class_id: UUID | None = None
    name: str | None = Field(default=None, min_length=1, max_length=160)
    subject: str | None = None
    test_date: date | None = None
    maximum_marks: Decimal | None = Field(default=None, gt=0)


class MarkInput(BaseModel):
    student_id: UUID
    marks: Decimal = Field(ge=0)
    grade: str | None = None
    remarks: str | None = None


class ScheduleInput(BaseModel):
    class_id: UUID
    teacher_id: UUID | None = None
    day_of_week: int = Field(ge=0, le=6)
    start_time: str
    end_time: str
    room: str | None = None


class ScheduleUpdate(BaseModel):
    class_id: UUID | None = None
    teacher_id: UUID | None = None
    day_of_week: int | None = Field(default=None, ge=0, le=6)
    start_time: str | None = None
    end_time: str | None = None
    room: str | None = None


class AssignmentInput(BaseModel):
    record_id: UUID


class ParentLinkInput(BaseModel):
    parent_id: UUID
    is_primary: bool = False


def _org_record(db: Session, model, organization_id: UUID, record_id: UUID):
    record = db.scalar(select(model).where(model.id == record_id, model.organization_id == organization_id))
    if record is None:
        raise TuiroError("RESOURCE_NOT_FOUND", "The requested resource was not found.", 404)
    return record


def _student_name(db: Session, student_id: UUID) -> str:
    student = db.get(Student, student_id)
    return f"{student.first_name} {student.last_name}".strip() if student else "Student"


def _fee_payload(db: Session, fee: StudentFee, org_today: date | None = None) -> dict:
    if org_today is None:
        org = db.get(Organization, fee.organization_id)
        org_today = get_org_today(org)
    paid = db.scalar(select(func.coalesce(func.sum(Payment.amount), 0)).where(Payment.fee_id == fee.id)) or Decimal("0")
    outstanding = max(Decimal("0"), fee.amount_due - paid)
    status = "PAID" if outstanding == 0 else "PARTIAL" if paid else ("OVERDUE" if fee.due_date < org_today else "PENDING")
    if fee.status != status:
        fee.status = status
    return {"id": fee.id, "student_id": fee.student_id, "student_name": _student_name(db, fee.student_id), "billing_period": fee.billing_period, "amount": fee.amount, "amount_due": fee.amount_due, "paid_amount": paid, "outstanding_amount": outstanding, "due_date": fee.due_date, "status": status}


def _payment_payload(db: Session, payment: Payment) -> dict:
    fee = db.get(StudentFee, payment.fee_id)
    return {"id": payment.id, "fee_id": payment.fee_id, "student_id": payment.student_id, "student_name": _student_name(db, payment.student_id), "amount": payment.amount, "payment_date": payment.payment_date, "payment_method": payment.payment_method, "transaction_reference": payment.transaction_reference, "notes": payment.notes, "billing_period": fee.billing_period if fee else None, "created_at": payment.created_at}


@router.post("/attendance/sessions", status_code=201)
def create_attendance(request: AttendanceSessionInput, principal: Principal = Depends(require_roles("OWNER", "ADMIN", "TEACHER")), db: Session = Depends(get_db)):
    _org_record(db, ClassGroup, principal.organization_id, request.class_id)
    check_teacher_class_access(db, principal, request.class_id)
    existing = db.scalar(select(AttendanceSession).where(AttendanceSession.organization_id == principal.organization_id, AttendanceSession.class_id == request.class_id, AttendanceSession.session_date == request.session_date))
    session = existing or AttendanceSession(organization_id=principal.organization_id, class_id=request.class_id, session_date=request.session_date, teacher_id=request.teacher_id, created_by=principal.user.id)
    if existing is None:
        db.add(session)
        db.flush()
    else:
        db.query(AttendanceRecord).filter(AttendanceRecord.session_id == session.id).delete()
    for item in request.records:
        _org_record(db, Student, principal.organization_id, item.student_id)
        db.add(AttendanceRecord(session_id=session.id, student_id=item.student_id, status=item.status, notes=item.notes))
    db.add(AuditLog(organization_id=principal.organization_id, user_id=principal.user.id, action="attendance_saved", entity_type="attendance_session", entity_id=session.id))
    db.commit()
    return {"id": session.id, "class_id": session.class_id, "session_date": session.session_date, "records": len(request.records)}


@router.get("/attendance/sessions")
def list_attendance(session_date: date | None = None, principal: Principal = Depends(require_roles("OWNER", "ADMIN", "TEACHER")), db: Session = Depends(get_db)):
    query = select(AttendanceSession).where(AttendanceSession.organization_id == principal.organization_id).order_by(AttendanceSession.session_date.desc())
    if session_date:
        query = query.where(AttendanceSession.session_date == session_date)
    return db.scalars(query.limit(100)).all()


@router.get("/attendance/session")
def attendance_session(class_id: UUID, session_date: date, principal: Principal = Depends(require_roles("OWNER", "ADMIN", "TEACHER")), db: Session = Depends(get_db)):
    _org_record(db, ClassGroup, principal.organization_id, class_id)
    check_teacher_class_access(db, principal, class_id)
    session = db.scalar(select(AttendanceSession).where(AttendanceSession.organization_id == principal.organization_id, AttendanceSession.class_id == class_id, AttendanceSession.session_date == session_date))
    if session is None:
        return {"session": None, "records": []}
    records = db.scalars(select(AttendanceRecord).where(AttendanceRecord.session_id == session.id)).all()
    return {"session": session, "records": records}


@router.get("/attendance/student/{student_id}")
def student_attendance(student_id: UUID, principal: Principal = Depends(require_roles("OWNER", "ADMIN", "TEACHER", "PARENT", "STUDENT")), db: Session = Depends(get_db)):
    _org_record(db, Student, principal.organization_id, student_id)
    check_parent_student_access(db, principal, student_id)
    check_student_self_access(db, principal, student_id)
    return db.scalars(select(AttendanceRecord).join(AttendanceSession, AttendanceRecord.session_id == AttendanceSession.id).where(AttendanceSession.organization_id == principal.organization_id, AttendanceRecord.student_id == student_id)).all()


@router.get("/attendance/unified")
def unified_attendance(
    session_date: date | None = None,
    group_id: UUID | None = None,
    principal: Principal = Depends(require_roles("OWNER", "ADMIN", "TEACHER")),
    db: Session = Depends(get_db),
):
    """Consolidated attendance query returning sessions and records from both class and group models."""
    org_id = principal.organization_id

    # 1. Class sessions
    cq = select(AttendanceSession).where(AttendanceSession.organization_id == org_id)
    if session_date:
        cq = cq.where(AttendanceSession.session_date == session_date)
    if group_id:
        cq = cq.where(AttendanceSession.class_id == group_id)
    class_sessions = db.scalars(cq.order_by(AttendanceSession.session_date.desc()).limit(100)).all()

    # 2. Group sessions
    gq = select(GroupAttendanceSession).where(GroupAttendanceSession.organization_id == org_id)
    if session_date:
        gq = gq.where(GroupAttendanceSession.session_date == session_date)
    if group_id:
        gq = gq.where(GroupAttendanceSession.group_id == group_id)
    group_sessions = db.scalars(gq.order_by(GroupAttendanceSession.session_date.desc()).limit(100)).all()

    results = []
    seen_keys = set()

    for s in class_sessions:
        records = db.scalars(select(AttendanceRecord).where(AttendanceRecord.session_id == s.id)).all()
        key = (s.session_date, s.class_id)
        seen_keys.add(key)
        results.append({
            "id": str(s.id),
            "source": "class",
            "group_id": str(s.class_id),
            "session_date": str(s.session_date),
            "total_students": len(records),
            "present_count": sum(1 for r in records if r.status in ("PRESENT", "LATE")),
            "records": [{"student_id": str(r.student_id), "status": r.status, "notes": r.notes} for r in records],
        })

    for s in group_sessions:
        key = (s.session_date, s.group_id)
        if key in seen_keys:
            continue
        records = db.scalars(select(GroupAttendanceRecord).where(GroupAttendanceRecord.session_id == s.id)).all()
        results.append({
            "id": str(s.id),
            "source": "group",
            "group_id": str(s.group_id),
            "session_date": str(s.session_date),
            "total_students": len(records),
            "present_count": sum(1 for r in records if r.status in ("PRESENT", "LATE")),
            "records": [{"student_id": str(r.student_id), "status": r.status, "notes": r.notes} for r in records],
        })

    return results


@router.post("/fees/generate")
def generate_fees(request: FeeGenerationInput, principal: Principal = Depends(require_roles("OWNER", "ADMIN")), db: Session = Depends(get_db)):
    students = db.scalars(select(Student).where(Student.organization_id == principal.organization_id, Student.status == "ACTIVE")).all()
    created = 0
    for student in students:
        exists = db.scalar(select(StudentFee).where(StudentFee.organization_id == principal.organization_id, StudentFee.student_id == student.id, StudentFee.billing_period == request.billing_period))
        if exists is None:
            db.add(StudentFee(organization_id=principal.organization_id, student_id=student.id, billing_period=request.billing_period, amount=request.amount, amount_due=request.amount, due_date=request.due_date, status="DUE"))
            created += 1
    db.commit()
    return {"billing_period": request.billing_period, "created": created, "skipped": len(students) - created}


@router.post("/fees", status_code=201)
def create_fee(request: FeeCreateInput, principal: Principal = Depends(require_roles("OWNER", "ADMIN")), db: Session = Depends(get_db)):
    _org_record(db, Student, principal.organization_id, request.student_id)
    exists = db.scalar(select(StudentFee).where(StudentFee.organization_id == principal.organization_id, StudentFee.student_id == request.student_id, StudentFee.billing_period == request.billing_period))
    if exists:
        raise TuiroError("FEE_ALREADY_EXISTS", "A fee already exists for this student and billing period.", 409)
    fee = StudentFee(organization_id=principal.organization_id, student_id=request.student_id, amount=request.amount, amount_due=request.amount, billing_period=request.billing_period, due_date=request.due_date, status="PENDING")
    db.add(fee)
    db.commit()
    db.refresh(fee)
    return _fee_payload(db, fee)


@router.get("/fees")
def list_fees(
    status_filter: str | None = Query(None, alias="status"),
    student_id: UUID | None = Query(None, alias="student_id"),
    principal: Principal = Depends(require_roles("OWNER", "ADMIN", "PARENT", "STUDENT")),
    db: Session = Depends(get_db),
):
    query = select(StudentFee).where(StudentFee.organization_id == principal.organization_id).order_by(StudentFee.due_date)
    if principal.role == "PARENT":
        student_ids = get_parent_student_ids(db, principal)
        if student_id:
            if student_id not in student_ids:
                return []
            query = query.where(StudentFee.student_id == student_id)
        else:
            query = query.where(StudentFee.student_id.in_(student_ids))
    elif principal.role == "STUDENT":
        self_id = get_student_self_id(db, principal)
        if student_id and student_id != self_id:
            return []
        query = query.where(StudentFee.student_id == self_id)
    elif student_id:
        query = query.where(StudentFee.student_id == student_id)
    if status_filter:
        query = query.where(StudentFee.status == status_filter)
    fees = db.scalars(query.limit(200)).all()
    payload = [_fee_payload(db, fee) for fee in fees]
    return [item for item in payload if not status_filter or item["status"] == status_filter]


@router.get("/fees/pending")
def pending_fees(principal: Principal = Depends(require_roles("OWNER", "ADMIN", "PARENT", "STUDENT")), db: Session = Depends(get_db)):
    query = select(StudentFee).where(StudentFee.organization_id == principal.organization_id).order_by(StudentFee.due_date)
    if principal.role == "PARENT":
        student_ids = get_parent_student_ids(db, principal)
        query = query.where(StudentFee.student_id.in_(student_ids))
    elif principal.role == "STUDENT":
        student_id = get_student_self_id(db, principal)
        query = query.where(StudentFee.student_id == student_id)
    fees = db.scalars(query).all()
    payload = [_fee_payload(db, fee) for fee in fees]
    return [item for item in payload if item["status"] in {"PENDING", "PARTIAL", "OVERDUE"}]


@router.get("/fees/{fee_id}")
def get_fee(fee_id: UUID, principal: Principal = Depends(require_roles("OWNER", "ADMIN", "PARENT", "STUDENT")), db: Session = Depends(get_db)):
    fee = _org_record(db, StudentFee, principal.organization_id, fee_id)
    if principal.role == "PARENT":
        student_ids = get_parent_student_ids(db, principal)
        if fee.student_id not in student_ids:
            raise TuiroError("RESOURCE_NOT_FOUND", "The requested resource was not found.", 404)
    elif principal.role == "STUDENT":
        student_id = get_student_self_id(db, principal)
        if fee.student_id != student_id:
            raise TuiroError("RESOURCE_NOT_FOUND", "The requested resource was not found.", 404)
    return _fee_payload(db, fee)


def process_fee_payment(
    db: Session,
    organization_id: UUID,
    fee_id: UUID,
    amount: Decimal,
    payment_method: str,
    transaction_reference: str | None,
    recorded_by_user_id: UUID,
    payment_date: date | None = None,
    notes: str | None = None,
) -> dict:
    organization = db.get(Organization, organization_id)
    pay_date = payment_date or get_org_today(organization)

    fee = db.scalar(
        select(StudentFee)
        .where(StudentFee.id == fee_id, StudentFee.organization_id == organization_id)
        .with_for_update()
    )
    if fee is None:
        raise TuiroError("RESOURCE_NOT_FOUND", "The requested resource was not found.", 404)

    # Check for idempotent retry if transaction_reference is provided
    if transaction_reference:
        existing_payment = db.scalar(
            select(Payment).where(
                Payment.organization_id == organization_id,
                Payment.transaction_reference == transaction_reference,
            )
        )
        if existing_payment:
            existing_receipt = db.scalar(
                select(Receipt).where(Receipt.payment_id == existing_payment.id)
            )
            paid_sum = db.scalar(
                select(func.coalesce(func.sum(Payment.amount), 0)).where(Payment.fee_id == fee.id)
            ) or Decimal("0")
            return {
                "payment": _payment_payload(db, existing_payment),
                "receipt": existing_receipt,
                "fee_status": fee.status,
                "remaining": max(Decimal("0"), fee.amount_due - paid_sum),
            }

    paid = db.scalar(
        select(func.coalesce(func.sum(Payment.amount), 0)).where(Payment.fee_id == fee.id)
    ) or Decimal("0")
    outstanding = fee.amount_due - paid
    if amount > outstanding:
        raise TuiroError("PAYMENT_EXCEEDS_BALANCE", "Payment is greater than the outstanding balance.", 400)

    payment = Payment(
        organization_id=organization_id,
        fee_id=fee.id,
        student_id=fee.student_id,
        amount=amount,
        payment_date=pay_date,
        payment_method=payment_method,
        transaction_reference=transaction_reference,
        notes=notes,
        recorded_by=recorded_by_user_id,
    )
    db.add(payment)
    db.flush()

    new_paid = paid + amount
    fee.status = "PAID" if new_paid >= fee.amount_due else "PARTIAL"

    receipt_number = generate_receipt_number(db, organization_id)
    receipt = Receipt(
        organization_id=organization_id,
        payment_id=payment.id,
        receipt_number=receipt_number,
    )
    db.add(receipt)
    db.add(AuditLog(
        organization_id=organization_id,
        user_id=recorded_by_user_id,
        action="payment_created",
        entity_type="payment",
        entity_id=payment.id,
    ))
    db.commit()
    return {
        "payment": _payment_payload(db, payment),
        "receipt": receipt,
        "fee_status": fee.status,
        "remaining": max(Decimal("0"), fee.amount_due - new_paid),
    }


@router.get("/payments/config")
def payment_config(
    principal: Principal = Depends(require_roles("OWNER", "ADMIN", "TEACHER", "PARENT", "STUDENT")),
):
    provider = get_payment_provider()
    return provider.get_public_config()


@router.post("/payments/create-order")
def create_payment_order(
    request: CreateOrderInput,
    principal: Principal = Depends(require_roles("OWNER", "ADMIN", "PARENT", "STUDENT")),
    db: Session = Depends(get_db),
):
    provider = get_payment_provider()
    if not provider.is_configured():
        raise TuiroError("PAYMENTS_NOT_CONFIGURED", "Online payment provider is not configured.", 400)

    fee = _org_record(db, StudentFee, principal.organization_id, request.fee_id)
    if principal.role == "PARENT":
        student_ids = get_parent_student_ids(db, principal)
        if fee.student_id not in student_ids:
            raise TuiroError("RESOURCE_NOT_FOUND", "The requested resource was not found.", 404)
    elif principal.role == "STUDENT":
        student_id = get_student_self_id(db, principal)
        if fee.student_id != student_id:
            raise TuiroError("RESOURCE_NOT_FOUND", "The requested resource was not found.", 404)

    paid = db.scalar(select(func.coalesce(func.sum(Payment.amount), 0)).where(Payment.fee_id == fee.id)) or Decimal("0")
    remaining = fee.amount_due - paid
    if remaining <= Decimal("0"):
        raise TuiroError("FEE_ALREADY_PAID", "This fee is already fully settled.", 400)

    organization = db.get(Organization, principal.organization_id)
    currency = organization.currency_code if organization else "USD"

    order = provider.create_order(
        amount=remaining,
        currency=currency,
        receipt=f"FEE-{fee.id.hex[:12]}",
        notes={
            "fee_id": str(fee.id),
            "organization_id": str(principal.organization_id),
            "student_id": str(fee.student_id),
            "user_id": str(principal.user.id),
        },
    )
    return {
        "order_id": order["id"],
        "amount": remaining,
        "amount_subunit": order["amount"],
        "currency": currency,
        "key_id": provider.get_public_config().get("key_id"),
        "fee_id": fee.id,
    }


@router.post("/payments/verify", status_code=201)
def verify_payment(
    request: VerifyPaymentInput,
    principal: Principal = Depends(require_roles("OWNER", "ADMIN", "PARENT", "STUDENT")),
    db: Session = Depends(get_db),
):
    provider = get_payment_provider()
    if not provider.is_configured():
        raise TuiroError("PAYMENTS_NOT_CONFIGURED", "Online payment provider is not configured.", 400)

    if not provider.verify_signature(request.order_id, request.payment_id, request.signature):
        raise TuiroError("INVALID_SIGNATURE", "Payment signature verification failed.", 400)

    fee = _org_record(db, StudentFee, principal.organization_id, request.fee_id)
    if principal.role == "PARENT":
        student_ids = get_parent_student_ids(db, principal)
        if fee.student_id not in student_ids:
            raise TuiroError("RESOURCE_NOT_FOUND", "The requested resource was not found.", 404)
    elif principal.role == "STUDENT":
        student_id = get_student_self_id(db, principal)
        if fee.student_id != student_id:
            raise TuiroError("RESOURCE_NOT_FOUND", "The requested resource was not found.", 404)

    paid = db.scalar(select(func.coalesce(func.sum(Payment.amount), 0)).where(Payment.fee_id == fee.id)) or Decimal("0")
    remaining = max(Decimal("0"), fee.amount_due - paid)

    return process_fee_payment(
        db=db,
        organization_id=principal.organization_id,
        fee_id=fee.id,
        amount=remaining,
        payment_method="ONLINE",
        transaction_reference=request.payment_id,
        recorded_by_user_id=principal.user.id,
        notes=f"Razorpay Order ID: {request.order_id}",
    )


@router.post("/payments/webhook")
async def payment_webhook(
    request: Request,
    db: Session = Depends(get_db),
):
    provider = get_payment_provider()
    signature = request.headers.get("X-Razorpay-Signature", "")
    body_bytes = await request.body()

    if not provider.verify_webhook(body_bytes, signature):
        raise TuiroError("INVALID_SIGNATURE", "Invalid webhook signature.", 400)

    event_data = json.loads(body_bytes.decode("utf-8"))
    event_type = event_data.get("event")

    if event_type in ("payment.captured", "order.paid"):
        payload_entity = event_data.get("payload", {}).get("payment", {}).get("entity", {})
        if not payload_entity:
            payload_entity = event_data.get("payload", {}).get("order", {}).get("entity", {})

        notes = payload_entity.get("notes", {})
        fee_id_str = notes.get("fee_id")
        org_id_str = notes.get("organization_id")
        user_id_str = notes.get("user_id")

        if fee_id_str and org_id_str:
            fee_id = UUID(fee_id_str)
            org_id = UUID(org_id_str)
            payment_id = payload_entity.get("id") or event_data.get("payload", {}).get("payment", {}).get("entity", {}).get("id")
            amount_val = Decimal(str(payload_entity.get("amount", 0))) / Decimal("100")

            recorded_by = UUID(user_id_str) if user_id_str else None
            if not recorded_by:
                first_member = db.scalar(select(OrganizationMember).where(OrganizationMember.organization_id == org_id))
                recorded_by = first_member.user_id if first_member else None

            if recorded_by and payment_id:
                process_fee_payment(
                    db=db,
                    organization_id=org_id,
                    fee_id=fee_id,
                    amount=amount_val,
                    payment_method="ONLINE",
                    transaction_reference=payment_id,
                    recorded_by_user_id=recorded_by,
                    notes=f"Razorpay Webhook: {event_type}",
                )

    return {"status": "ok"}


@router.post("/payments", status_code=201)
def record_payment(request: PaymentInput, principal: Principal = Depends(require_roles("OWNER", "ADMIN")), db: Session = Depends(get_db)):
    if request.transaction_reference and db.scalar(select(Payment).where(Payment.organization_id == principal.organization_id, Payment.transaction_reference == request.transaction_reference)):
        raise TuiroError("DUPLICATE_PAYMENT", "This transaction reference has already been recorded.", 409)
    return process_fee_payment(
        db=db,
        organization_id=principal.organization_id,
        fee_id=request.fee_id,
        amount=request.amount,
        payment_method=request.payment_method,
        transaction_reference=request.transaction_reference,
        recorded_by_user_id=principal.user.id,
        payment_date=request.payment_date,
        notes=request.notes,
    )


@router.get("/payments")
def list_payments(principal: Principal = Depends(require_roles("OWNER", "ADMIN", "PARENT", "STUDENT")), db: Session = Depends(get_db)):
    query = select(Payment).where(Payment.organization_id == principal.organization_id).order_by(Payment.payment_date.desc()).limit(200)
    if principal.role == "PARENT":
        student_ids = get_parent_student_ids(db, principal)
        query = query.where(Payment.student_id.in_(student_ids))
    elif principal.role == "STUDENT":
        student_id = get_student_self_id(db, principal)
        query = query.where(Payment.student_id == student_id)
    return [_payment_payload(db, payment) for payment in db.scalars(query).all()]


@router.get("/payments/{payment_id}")
def get_payment(payment_id: UUID, principal: Principal = Depends(require_roles("OWNER", "ADMIN", "PARENT", "STUDENT")), db: Session = Depends(get_db)):
    payment = _org_record(db, Payment, principal.organization_id, payment_id)
    if principal.role == "PARENT":
        student_ids = get_parent_student_ids(db, principal)
        if payment.student_id not in student_ids:
            raise TuiroError("RESOURCE_NOT_FOUND", "The requested resource was not found.", 404)
    elif principal.role == "STUDENT":
        student_id = get_student_self_id(db, principal)
        if payment.student_id != student_id:
            raise TuiroError("RESOURCE_NOT_FOUND", "The requested resource was not found.", 404)
    return _payment_payload(db, payment)


@router.get("/receipts")
def list_receipts(principal: Principal = Depends(require_roles("OWNER", "ADMIN", "PARENT", "STUDENT")), db: Session = Depends(get_db)):
    query = select(Receipt).join(Payment, Payment.id == Receipt.payment_id).where(Receipt.organization_id == principal.organization_id).order_by(Receipt.issued_at.desc()).limit(200)
    if principal.role == "PARENT":
        student_ids = get_parent_student_ids(db, principal)
        query = query.where(Payment.student_id.in_(student_ids))
    elif principal.role == "STUDENT":
        student_id = get_student_self_id(db, principal)
        query = query.where(Payment.student_id == student_id)
    return db.scalars(query).all()


@router.get("/receipts/{receipt_id}")
def get_receipt(receipt_id: UUID, principal: Principal = Depends(require_roles("OWNER", "ADMIN", "PARENT", "STUDENT")), db: Session = Depends(get_db)):
    receipt = _org_record(db, Receipt, principal.organization_id, receipt_id)
    payment = db.get(Payment, receipt.payment_id)
    if principal.role == "PARENT":
        student_ids = get_parent_student_ids(db, principal)
        if not payment or payment.student_id not in student_ids:
            raise TuiroError("RESOURCE_NOT_FOUND", "The requested resource was not found.", 404)
    elif principal.role == "STUDENT":
        student_id = get_student_self_id(db, principal)
        if not payment or payment.student_id != student_id:
            raise TuiroError("RESOURCE_NOT_FOUND", "The requested resource was not found.", 404)
    return receipt


@router.get("/receipts/{receipt_id}/pdf")
def receipt_pdf(receipt_id: UUID, principal: Principal = Depends(require_roles("OWNER", "ADMIN", "PARENT", "STUDENT")), db: Session = Depends(get_db)):
    receipt = _org_record(db, Receipt, principal.organization_id, receipt_id)
    payment = db.get(Payment, receipt.payment_id)
    if principal.role == "PARENT":
        student_ids = get_parent_student_ids(db, principal)
        if not payment or payment.student_id not in student_ids:
            raise TuiroError("RESOURCE_NOT_FOUND", "The requested resource was not found.", 404)
    elif principal.role == "STUDENT":
        student_id = get_student_self_id(db, principal)
        if not payment or payment.student_id != student_id:
            raise TuiroError("RESOURCE_NOT_FOUND", "The requested resource was not found.", 404)
    fee = db.get(StudentFee, payment.fee_id) if payment else None
    student = db.get(Student, payment.student_id) if payment else None
    organization = db.get(Organization, principal.organization_id)
    if not payment or not fee or not student or not organization:
        raise TuiroError("RECEIPT_DATA_INCOMPLETE", "Receipt data is incomplete.", 409)
    content = build_receipt_pdf(organization, receipt, payment, fee, student)
    return StreamingResponse(BytesIO(content), media_type="application/pdf", headers={"Content-Disposition": f'attachment; filename="{receipt.receipt_number}.pdf"'})


@router.post("/receipts/{receipt_id}/send")
def send_receipt(receipt_id: UUID, principal: Principal = Depends(require_roles("OWNER", "ADMIN")), db: Session = Depends(get_db)):
    receipt = _org_record(db, Receipt, principal.organization_id, receipt_id)
    return {"receipt_id": receipt.id, "channel": "share", "status": "available", "pdf_url": f"/api/v1/receipts/{receipt.id}/pdf"}


@router.post("/notifications/fee-reminder/{fee_id}")
def fee_reminder(fee_id: UUID, principal: Principal = Depends(require_roles("OWNER", "ADMIN")), db: Session = Depends(get_db)):
    fee = _org_record(db, StudentFee, principal.organization_id, fee_id)
    message = f"Your tuition fee for {fee.billing_period} is due. Amount: {fee.amount_due}."
    notification = send_notification(
        db, principal.organization_id, recipient_contact="parent contact required",
        title="Fee reminder", channel="WHATSAPP", message=message,
        notification_type="FEE_REMINDER", idempotency_key=f"fee-reminder:{fee.id}:{fee.billing_period}",
    )
    return {"notification_id": notification.id, "channel": notification.channel.lower(), "message": message, "status": notification.status}


@router.post("/homework", status_code=201)
def create_homework(request: HomeworkInput, principal: Principal = Depends(require_roles("OWNER", "ADMIN", "TEACHER")), db: Session = Depends(get_db)):
    _org_record(db, ClassGroup, principal.organization_id, request.class_id)
    check_teacher_class_access(db, principal, request.class_id)
    record = Homework(organization_id=principal.organization_id, created_by=principal.user.id, **request.model_dump())
    db.add(record); db.commit(); db.refresh(record)
    return record


@router.get("/homework")
def list_homework(principal: Principal = Depends(require_roles("OWNER", "ADMIN", "TEACHER", "PARENT", "STUDENT")), db: Session = Depends(get_db)):
    return db.scalars(select(Homework).where(Homework.organization_id == principal.organization_id).order_by(Homework.due_date)).all()


@router.get("/homework/{homework_id}")
def get_homework(homework_id: UUID, principal: Principal = Depends(require_roles("OWNER", "ADMIN", "TEACHER", "PARENT", "STUDENT")), db: Session = Depends(get_db)):
    record = _org_record(db, Homework, principal.organization_id, homework_id)
    class_group = db.get(ClassGroup, record.class_id)
    return {
        "id": record.id,
        "class_id": record.class_id,
        "class_name": class_group.name if class_group else "Class",
        "title": record.title,
        "description": record.description,
        "due_date": record.due_date,
    }


@router.patch("/homework/{homework_id}")
def update_homework(homework_id: UUID, request: HomeworkUpdate, principal: Principal = Depends(require_roles("OWNER", "ADMIN", "TEACHER")), db: Session = Depends(get_db)):
    record = _org_record(db, Homework, principal.organization_id, homework_id)
    check_teacher_class_access(db, principal, record.class_id)
    data = request.model_dump(exclude_unset=True)
    if "class_id" in data and data["class_id"] is not None:
        _org_record(db, ClassGroup, principal.organization_id, data["class_id"])
        check_teacher_class_access(db, principal, data["class_id"])
    for key, value in data.items(): setattr(record, key, value)
    db.commit(); db.refresh(record)
    return record


@router.delete("/homework/{homework_id}", status_code=204)
def delete_homework(homework_id: UUID, principal: Principal = Depends(require_roles("OWNER", "ADMIN", "TEACHER")), db: Session = Depends(get_db)):
    record = _org_record(db, Homework, principal.organization_id, homework_id)
    check_teacher_class_access(db, principal, record.class_id)
    db.delete(record); db.commit()


@router.post("/tests", status_code=201)
def create_test(request: TestInput, principal: Principal = Depends(require_roles("OWNER", "ADMIN", "TEACHER")), db: Session = Depends(get_db)):
    _org_record(db, ClassGroup, principal.organization_id, request.class_id)
    check_teacher_class_access(db, principal, request.class_id)
    record = AcademicTest(organization_id=principal.organization_id, **request.model_dump())
    db.add(record); db.commit(); db.refresh(record)
    return record


@router.get("/tests")
def list_tests(principal: Principal = Depends(require_roles("OWNER", "ADMIN", "TEACHER", "PARENT", "STUDENT")), db: Session = Depends(get_db)):
    return db.scalars(select(AcademicTest).where(AcademicTest.organization_id == principal.organization_id).order_by(AcademicTest.test_date.desc())).all()


@router.get("/tests/{test_id}")
def get_test(test_id: UUID, principal: Principal = Depends(require_roles("OWNER", "ADMIN", "TEACHER", "PARENT", "STUDENT")), db: Session = Depends(get_db)):
    test = _org_record(db, AcademicTest, principal.organization_id, test_id)
    class_group = db.get(ClassGroup, test.class_id)
    return {
        "id": test.id,
        "class_id": test.class_id,
        "class_name": class_group.name if class_group else "Class",
        "name": test.name,
        "title": test.name,
        "subject": test.subject,
        "test_date": test.test_date,
        "maximum_marks": test.maximum_marks,
    }


@router.patch("/tests/{test_id}")
def update_test(test_id: UUID, request: TestUpdate, principal: Principal = Depends(require_roles("OWNER", "ADMIN", "TEACHER")), db: Session = Depends(get_db)):
    record = _org_record(db, AcademicTest, principal.organization_id, test_id)
    check_teacher_class_access(db, principal, record.class_id)
    data = request.model_dump(exclude_unset=True)
    if "class_id" in data and data["class_id"] is not None:
        _org_record(db, ClassGroup, principal.organization_id, data["class_id"])
        check_teacher_class_access(db, principal, data["class_id"])
    for key, value in data.items(): setattr(record, key, value)
    db.commit(); db.refresh(record)
    return record


@router.delete("/tests/{test_id}", status_code=204)
def delete_test(test_id: UUID, principal: Principal = Depends(require_roles("OWNER", "ADMIN", "TEACHER")), db: Session = Depends(get_db)):
    record = _org_record(db, AcademicTest, principal.organization_id, test_id)
    check_teacher_class_access(db, principal, record.class_id)
    db.delete(record); db.commit()


@router.post("/tests/{test_id}/marks", status_code=201)
def record_mark(test_id: UUID, request: MarkInput, principal: Principal = Depends(require_roles("OWNER", "ADMIN", "TEACHER")), db: Session = Depends(get_db)):
    test = _org_record(db, AcademicTest, principal.organization_id, test_id)
    check_teacher_class_access(db, principal, test.class_id)
    _org_record(db, Student, principal.organization_id, request.student_id)
    if request.marks > test.maximum_marks:
        raise TuiroError("MARKS_EXCEED_MAXIMUM", "Marks cannot exceed the maximum.", 400)
    record = db.scalar(select(TestMark).where(TestMark.organization_id == principal.organization_id, TestMark.test_id == test_id, TestMark.student_id == request.student_id))
    if record is None:
        record = TestMark(organization_id=principal.organization_id, test_id=test_id, **request.model_dump()); db.add(record)
    else:
        for key, value in request.model_dump().items(): setattr(record, key, value)
    db.commit(); db.refresh(record)
    return record


@router.get("/tests/{test_id}/marks")
def list_marks(test_id: UUID, principal: Principal = Depends(require_roles("OWNER", "ADMIN", "TEACHER", "PARENT", "STUDENT")), db: Session = Depends(get_db)):
    test = _org_record(db, AcademicTest, principal.organization_id, test_id)
    query = select(TestMark).where(TestMark.organization_id == principal.organization_id, TestMark.test_id == test.id)
    if principal.role == "PARENT":
        student_ids = get_parent_student_ids(db, principal)
        query = query.where(TestMark.student_id.in_(student_ids))
    elif principal.role == "STUDENT":
        student_id = get_student_self_id(db, principal)
        query = query.where(TestMark.student_id == student_id)
    marks = db.scalars(query).all()
    return [{"id": mark.id, "student_id": mark.student_id, "student_name": _student_name(db, mark.student_id), "marks": mark.marks, "maximum_marks": test.maximum_marks, "percentage": round(float(mark.marks / test.maximum_marks * 100), 2), "grade": mark.grade, "remarks": mark.remarks} for mark in marks]


@router.get("/students/{student_id}/tests")
def student_tests(student_id: UUID, principal: Principal = Depends(require_roles("OWNER", "ADMIN", "TEACHER", "PARENT", "STUDENT")), db: Session = Depends(get_db)):
    _org_record(db, Student, principal.organization_id, student_id)
    if principal.role == "PARENT":
        allowed = get_parent_student_ids(db, principal)
        if student_id not in allowed:
            raise TuiroError("RESOURCE_NOT_FOUND", "The requested resource was not found.", 404)
    elif principal.role == "STUDENT":
        if student_id != get_student_self_id(db, principal):
            raise TuiroError("RESOURCE_NOT_FOUND", "The requested resource was not found.", 404)

    marks = db.scalars(select(TestMark).where(TestMark.organization_id == principal.organization_id, TestMark.student_id == student_id)).all()
    results = []
    for mark in marks:
        test = db.get(AcademicTest, mark.test_id)
        if test:
            results.append({
                "id": mark.id,
                "test_id": test.id,
                "test_name": test.name,
                "test_title": test.name,
                "subject": test.subject,
                "test_date": test.test_date,
                "marks": mark.marks,
                "maximum_marks": test.maximum_marks,
                "percentage": round(float(mark.marks / test.maximum_marks * 100), 2) if test.maximum_marks else 0,
                "grade": mark.grade,
                "remarks": mark.remarks,
            })
    return results


@router.get("/schedule")
def list_schedule(principal: Principal = Depends(require_roles("OWNER", "ADMIN", "TEACHER", "PARENT", "STUDENT")), db: Session = Depends(get_db)):
    return db.scalars(select(ScheduleEntry).where(ScheduleEntry.organization_id == principal.organization_id).order_by(ScheduleEntry.day_of_week, ScheduleEntry.start_time)).all()


@router.post("/schedule", status_code=201)
def create_schedule(request: ScheduleInput, principal: Principal = Depends(require_roles("OWNER", "ADMIN")), db: Session = Depends(get_db)):
    _org_record(db, ClassGroup, principal.organization_id, request.class_id)
    record = ScheduleEntry(organization_id=principal.organization_id, **request.model_dump()); db.add(record); db.commit(); db.refresh(record)
    return record


@router.patch("/schedule/{schedule_id}")
def update_schedule(schedule_id: UUID, request: ScheduleUpdate, principal: Principal = Depends(require_roles("OWNER", "ADMIN")), db: Session = Depends(get_db)):
    record = _org_record(db, ScheduleEntry, principal.organization_id, schedule_id)
    data = request.model_dump(exclude_unset=True)
    if "class_id" in data and data["class_id"] is not None:
        _org_record(db, ClassGroup, principal.organization_id, data["class_id"])
    for key, value in data.items(): setattr(record, key, value)
    db.commit(); db.refresh(record)
    return record


@router.delete("/schedule/{schedule_id}", status_code=204)
def delete_schedule(schedule_id: UUID, principal: Principal = Depends(require_roles("OWNER", "ADMIN")), db: Session = Depends(get_db)):
    db.delete(_org_record(db, ScheduleEntry, principal.organization_id, schedule_id)); db.commit()


def _attendance_summary(db: Session, org_id: UUID, target_date: date | None = None) -> tuple[int, int]:
    class_q = select(
        AttendanceSession.session_date,
        AttendanceSession.class_id,
        AttendanceRecord.student_id,
        AttendanceRecord.status,
    ).join(AttendanceRecord, AttendanceRecord.session_id == AttendanceSession.id).where(AttendanceSession.organization_id == org_id)

    group_q = select(
        GroupAttendanceSession.session_date,
        GroupAttendanceSession.group_id,
        GroupAttendanceRecord.student_id,
        GroupAttendanceRecord.status,
    ).join(GroupAttendanceRecord, GroupAttendanceRecord.session_id == GroupAttendanceSession.id).where(GroupAttendanceSession.organization_id == org_id)

    if target_date is not None:
        class_q = class_q.where(AttendanceSession.session_date == target_date)
        group_q = group_q.where(GroupAttendanceSession.session_date == target_date)

    class_records = db.execute(class_q).all()
    group_records = db.execute(group_q).all()

    merged: dict[tuple[date, UUID, UUID], str] = {}
    for r in class_records:
        merged[(r.session_date, r.class_id, r.student_id)] = r.status
    for r in group_records:
        merged[(r.session_date, r.group_id, r.student_id)] = r.status

    total = len(merged)
    present = sum(1 for status in merged.values() if status in ("PRESENT", "LATE"))
    return total, present


@router.get("/dashboard")
def dashboard(principal: Principal = Depends(require_roles("OWNER", "ADMIN")), db: Session = Depends(get_db)):
    organization = db.get(Organization, principal.organization_id)
    students = db.scalar(select(func.count()).select_from(Student).where(Student.organization_id == principal.organization_id, Student.status == "ACTIVE")) or 0
    today = get_org_today(organization)
    classes = db.scalar(select(func.count()).select_from(ClassGroup).where(ClassGroup.organization_id == principal.organization_id, ClassGroup.status == "ACTIVE")) or 0
    today_schedules = db.scalars(select(ScheduleEntry).where(ScheduleEntry.organization_id == principal.organization_id, ScheduleEntry.day_of_week == today.weekday()).order_by(ScheduleEntry.start_time)).all()
    classes_today = len(today_schedules)
    attendance_total, attendance_present = _attendance_summary(db, principal.organization_id, target_date=today)
    pending_fees = db.scalars(select(StudentFee).where(StudentFee.organization_id == principal.organization_id).order_by(StudentFee.due_date)).all()
    pending_items = []
    pending_total = Decimal("0")
    for fee in pending_fees:
        fee_item = _fee_payload(db, fee, org_today=today)
        if fee_item["status"] == "PAID":
            continue
        remaining = fee_item["outstanding_amount"]
        pending_total += remaining
        if len(pending_items) < 5:
            pending_items.append({"id": fee.id, "student_name": fee_item["student_name"], "billing_period": fee.billing_period, "amount": remaining, "due_date": fee.due_date, "status": fee_item["status"]})
    collected = db.scalar(select(func.coalesce(func.sum(Payment.amount), 0)).where(Payment.organization_id == principal.organization_id, Payment.payment_date == today)) or Decimal("0")
    recent_payments = db.scalars(select(Payment).where(Payment.organization_id == principal.organization_id).order_by(Payment.created_at.desc()).limit(5)).all()
    recent_items = []
    for payment in recent_payments:
        recent_items.append(_payment_payload(db, payment))
    next_class = None
    current_time = get_org_now(organization).strftime("%H:%M")
    for entry in today_schedules:
        if entry.start_time >= current_time:
            class_group = db.get(ClassGroup, entry.class_id)
            teacher = db.get(Teacher, entry.teacher_id) if entry.teacher_id else None
            student_count = db.scalar(select(func.count()).select_from(ClassStudent).where(ClassStudent.organization_id == principal.organization_id, ClassStudent.class_id == entry.class_id)) or 0
            next_class = {"class_name": class_group.name if class_group else "Class", "subject": class_group.subject if class_group else None, "teacher_name": teacher.employee_number if teacher else None, "start_time": entry.start_time, "end_time": entry.end_time, "room": entry.room, "student_count": student_count}
            break
    return {"students": students, "active_classes": classes, "classes_today": classes_today, "attendance_percentage": round((attendance_present / attendance_total) * 100, 2) if attendance_total else 0, "pending_fees": pending_total, "todays_collections": collected, "next_class": next_class, "pending_fee_items": pending_items, "recent_payments": recent_items, "currency_code": organization.currency_code if organization else "USD", "currency": organization.currency_code if organization else "USD", "timezone": organization.timezone if organization else "Asia/Kolkata", "role": principal.role}


@router.post("/classes/{class_id}/students", status_code=201)
def assign_student(class_id: UUID, request: AssignmentInput, principal: Principal = Depends(require_roles("OWNER", "ADMIN")), db: Session = Depends(get_db)):
    _org_record(db, ClassGroup, principal.organization_id, class_id)
    _org_record(db, Student, principal.organization_id, request.record_id)
    existing = db.scalar(select(ClassStudent).where(ClassStudent.organization_id == principal.organization_id, ClassStudent.class_id == class_id, ClassStudent.student_id == request.record_id))
    gm = db.scalar(select(GroupMember).where(GroupMember.group_id == class_id, GroupMember.student_id == request.record_id))
    if gm:
        gm.removed_at = None
    else:
        db.add(GroupMember(organization_id=principal.organization_id, group_id=class_id, student_id=request.record_id))
    if existing:
        db.commit()
        return existing
    record = ClassStudent(organization_id=principal.organization_id, class_id=class_id, student_id=request.record_id); db.add(record); db.commit(); db.refresh(record); return record


@router.get("/classes/{class_id}/students")
def class_students(class_id: UUID, principal: Principal = Depends(require_roles("OWNER", "ADMIN", "TEACHER")), db: Session = Depends(get_db)):
    _org_record(db, ClassGroup, principal.organization_id, class_id)
    return db.scalars(select(Student).join(ClassStudent, ClassStudent.student_id == Student.id).where(ClassStudent.organization_id == principal.organization_id, ClassStudent.class_id == class_id, Student.organization_id == principal.organization_id, Student.status == "ACTIVE")).all()


@router.delete("/classes/{class_id}/students/{student_id}", status_code=204)
def remove_student_from_class(class_id: UUID, student_id: UUID, principal: Principal = Depends(require_roles("OWNER", "ADMIN")), db: Session = Depends(get_db)):
    link = db.scalar(select(ClassStudent).where(ClassStudent.organization_id == principal.organization_id, ClassStudent.class_id == class_id, ClassStudent.student_id == student_id))
    if link is None: raise TuiroError("ENROLLMENT_NOT_FOUND", "Class enrollment not found.", 404)
    db.delete(link)
    gm = db.scalar(select(GroupMember).where(GroupMember.group_id == class_id, GroupMember.student_id == student_id, GroupMember.removed_at.is_(None)))
    if gm:
        from datetime import datetime, timezone
        gm.removed_at = datetime.now(timezone.utc)
    db.commit()


@router.post("/classes/{class_id}/teachers", status_code=201)
def assign_teacher(class_id: UUID, request: AssignmentInput, principal: Principal = Depends(require_roles("OWNER", "ADMIN")), db: Session = Depends(get_db)):
    _org_record(db, ClassGroup, principal.organization_id, class_id)
    _org_record(db, Teacher, principal.organization_id, request.record_id)
    existing = db.scalar(select(ClassTeacher).where(ClassTeacher.organization_id == principal.organization_id, ClassTeacher.class_id == class_id, ClassTeacher.teacher_id == request.record_id))
    if existing: return existing
    record = ClassTeacher(organization_id=principal.organization_id, class_id=class_id, teacher_id=request.record_id); db.add(record); db.commit(); db.refresh(record); return record


@router.get("/classes/{class_id}/teachers")
def class_teachers(class_id: UUID, principal: Principal = Depends(require_roles("OWNER", "ADMIN", "TEACHER")), db: Session = Depends(get_db)):
    _org_record(db, ClassGroup, principal.organization_id, class_id)
    return db.scalars(select(Teacher).join(ClassTeacher, ClassTeacher.teacher_id == Teacher.id).where(ClassTeacher.organization_id == principal.organization_id, ClassTeacher.class_id == class_id, Teacher.organization_id == principal.organization_id)).all()


@router.delete("/classes/{class_id}/teachers/{teacher_id}", status_code=204)
def remove_teacher_from_class(class_id: UUID, teacher_id: UUID, principal: Principal = Depends(require_roles("OWNER", "ADMIN")), db: Session = Depends(get_db)):
    link = db.scalar(select(ClassTeacher).where(ClassTeacher.organization_id == principal.organization_id, ClassTeacher.class_id == class_id, ClassTeacher.teacher_id == teacher_id))
    if link is None: raise TuiroError("TEACHER_ASSIGNMENT_NOT_FOUND", "Teacher assignment not found.", 404)
    db.delete(link); db.commit()


@router.post("/students/{student_id}/parents", status_code=201)
def link_parent(student_id: UUID, request: ParentLinkInput, principal: Principal = Depends(require_roles("OWNER", "ADMIN")), db: Session = Depends(get_db)):
    _org_record(db, Student, principal.organization_id, student_id)
    _org_record(db, Parent, principal.organization_id, request.parent_id)
    existing = db.scalar(select(StudentParent).where(StudentParent.organization_id == principal.organization_id, StudentParent.student_id == student_id, StudentParent.parent_id == request.parent_id))
    if existing:
        existing.is_primary = request.is_primary
        db.commit(); db.refresh(existing); return existing
    record = StudentParent(organization_id=principal.organization_id, student_id=student_id, parent_id=request.parent_id, is_primary=request.is_primary)
    db.add(record); db.commit(); db.refresh(record); return record


@router.get("/students/{student_id}/parents")
def student_parents(student_id: UUID, principal: Principal = Depends(require_roles("OWNER", "ADMIN", "TEACHER", "PARENT", "STUDENT")), db: Session = Depends(get_db)):
    _org_record(db, Student, principal.organization_id, student_id)
    return db.scalars(select(Parent).join(StudentParent, StudentParent.parent_id == Parent.id).where(StudentParent.organization_id == principal.organization_id, StudentParent.student_id == student_id, Parent.organization_id == principal.organization_id)).all()


@router.get("/parents/{parent_id}/students")
def parent_students(parent_id: UUID, principal: Principal = Depends(require_roles("OWNER", "ADMIN", "PARENT")), db: Session = Depends(get_db)):
    parent = _org_record(db, Parent, principal.organization_id, parent_id)
    if principal.role == "PARENT" and parent.user_id != principal.user.id:
        raise TuiroError("RESOURCE_NOT_FOUND", "The requested resource was not found.", 404)
    return db.scalars(select(Student).join(StudentParent, StudentParent.student_id == Student.id).where(StudentParent.organization_id == principal.organization_id, StudentParent.parent_id == parent_id, Student.organization_id == principal.organization_id)).all()


@router.delete("/students/{student_id}/parents/{parent_id}", status_code=204)
def unlink_parent(student_id: UUID, parent_id: UUID, principal: Principal = Depends(require_roles("OWNER", "ADMIN")), db: Session = Depends(get_db)):
    link = db.scalar(select(StudentParent).where(StudentParent.organization_id == principal.organization_id, StudentParent.student_id == student_id, StudentParent.parent_id == parent_id))
    if link is None: raise TuiroError("LINK_NOT_FOUND", "Parent link not found.", 404)
    db.delete(link); db.commit()


@router.get("/reports/fees")
def fee_report(principal: Principal = Depends(require_roles("OWNER", "ADMIN")), db: Session = Depends(get_db)):
    collected = db.scalar(select(func.coalesce(func.sum(Payment.amount), 0)).where(Payment.organization_id == principal.organization_id)) or Decimal("0")
    pending = sum((_fee_payload(db, fee)["outstanding_amount"] for fee in db.scalars(select(StudentFee).where(StudentFee.organization_id == principal.organization_id)).all()), Decimal("0"))
    return {"collected_amount": collected, "pending_amount": pending, "payment_count": db.scalar(select(func.count()).select_from(Payment).where(Payment.organization_id == principal.organization_id)) or 0}


@router.get("/reports/attendance")
def attendance_report(principal: Principal = Depends(require_roles("OWNER", "ADMIN")), db: Session = Depends(get_db)):
    total, present = _attendance_summary(db, principal.organization_id)
    return {"total_records": total, "present_records": present, "attendance_percentage": round((present / total) * 100, 2) if total else 0}


def _csv_response(filename: str, headers: list[str], rows: list[list[object]]) -> StreamingResponse:
    output = StringIO()
    writer = csv.writer(output)
    writer.writerow(headers)
    writer.writerows(rows)
    return StreamingResponse(iter([output.getvalue().encode("utf-8")]), media_type="text/csv", headers={"Content-Disposition": f'attachment; filename="{filename}"'})


@router.get("/reports/fees/export.csv")
def export_fee_report(principal: Principal = Depends(require_roles("OWNER", "ADMIN")), db: Session = Depends(get_db)):
    fees = db.scalars(select(StudentFee).where(StudentFee.organization_id == principal.organization_id).order_by(StudentFee.due_date)).all()
    return _csv_response("tuiro-fees.csv", ["fee_id", "student_id", "billing_period", "amount_due", "due_date", "status"], [[fee.id, fee.student_id, fee.billing_period, fee.amount_due, fee.due_date, fee.status] for fee in fees])


@router.get("/reports/attendance/export.csv")
def export_attendance_report(principal: Principal = Depends(require_roles("OWNER", "ADMIN")), db: Session = Depends(get_db)):
    class_q = select(
        AttendanceSession.session_date,
        AttendanceSession.class_id,
        AttendanceRecord.student_id,
        AttendanceRecord.status,
    ).join(AttendanceRecord, AttendanceRecord.session_id == AttendanceSession.id).where(AttendanceSession.organization_id == principal.organization_id)

    group_q = select(
        GroupAttendanceSession.session_date,
        GroupAttendanceSession.group_id,
        GroupAttendanceRecord.student_id,
        GroupAttendanceRecord.status,
    ).join(GroupAttendanceRecord, GroupAttendanceRecord.session_id == GroupAttendanceSession.id).where(GroupAttendanceSession.organization_id == principal.organization_id)

    class_records = db.execute(class_q).all()
    group_records = db.execute(group_q).all()

    merged: dict[tuple[date, UUID, UUID], str] = {}
    for r in class_records:
        merged[(r.session_date, r.class_id, r.student_id)] = r.status
    for r in group_records:
        merged[(r.session_date, r.group_id, r.student_id)] = r.status

    rows = [[s_date, c_id, s_id, status] for (s_date, c_id, s_id), status in sorted(merged.items(), key=lambda x: x[0][0])]
    return _csv_response("tuiro-attendance.csv", ["date", "class_id", "student_id", "status"], rows)


@router.get("/reports/audit-logs")
def get_audit_logs(
    limit: int = 100,
    offset: int = 0,
    entity_type: str | None = None,
    principal: Principal = Depends(require_roles("OWNER", "ADMIN")),
    db: Session = Depends(get_db),
):
    query = select(AuditLog).where(AuditLog.organization_id == principal.organization_id).order_by(AuditLog.created_at.desc())
    if entity_type:
        query = query.where(AuditLog.entity_type == entity_type)
    logs = db.scalars(query.offset(offset).limit(min(limit, 200))).all()
    res = []
    for log in logs:
        user = db.get(User, log.user_id) if log.user_id else None
        res.append({
            "id": log.id,
            "action": log.action,
            "entity_type": log.entity_type,
            "entity_id": log.entity_id,
            "user_id": log.user_id,
            "user_name": user.display_name if user else "System",
            "created_at": log.created_at,
        })
    return res


@router.get("/reports/students/{student_id}/report-card")
def get_student_report_card(
    student_id: UUID,
    principal: Principal = Depends(require_roles("OWNER", "ADMIN", "TEACHER", "PARENT", "STUDENT")),
    db: Session = Depends(get_db),
):
    student = _org_record(db, Student, principal.organization_id, student_id)
    check_parent_student_access(db, principal, student_id)
    check_student_self_access(db, principal, student_id)

    marks_query = (
        select(TestMark, AcademicTest)
        .join(AcademicTest, TestMark.test_id == AcademicTest.id)
        .where(
            TestMark.organization_id == principal.organization_id,
            TestMark.student_id == student_id,
        )
        .order_by(AcademicTest.test_date.desc())
    )
    test_results = []
    total_obtained = Decimal("0")
    total_max = Decimal("0")

    for tm, t in db.execute(marks_query).all():
        pct = float(round((tm.marks / t.maximum_marks) * 100, 1)) if t.maximum_marks > 0 else 0.0
        total_obtained += tm.marks
        total_max += t.maximum_marks
        test_results.append({
            "test_id": t.id,
            "test_name": t.name,
            "subject": t.subject,
            "test_date": t.test_date,
            "maximum_marks": float(t.maximum_marks),
            "marks_obtained": float(tm.marks),
            "percentage": pct,
            "grade": tm.grade,
            "remarks": tm.remarks,
        })

    overall_percentage = float(round((total_obtained / total_max) * 100, 1)) if total_max > 0 else 0.0

    class_att = db.scalars(
        select(AttendanceRecord)
        .join(AttendanceSession, AttendanceRecord.session_id == AttendanceSession.id)
        .where(
            AttendanceSession.organization_id == principal.organization_id,
            AttendanceRecord.student_id == student_id,
        )
    ).all()
    group_att = db.scalars(
        select(GroupAttendanceRecord)
        .join(GroupAttendanceSession, GroupAttendanceRecord.session_id == GroupAttendanceSession.id)
        .where(
            GroupAttendanceSession.organization_id == principal.organization_id,
            GroupAttendanceRecord.student_id == student_id,
        )
    ).all()

    total_sessions = len(class_att) + len(group_att)
    present_sessions = sum(1 for a in class_att if a.status == "PRESENT") + sum(1 for a in group_att if a.status == "PRESENT")
    att_percentage = float(round((present_sessions / total_sessions) * 100, 1)) if total_sessions > 0 else 100.0

    return {
        "student": {
            "id": student.id,
            "first_name": student.first_name,
            "last_name": student.last_name,
            "student_number": student.student_number,
        },
        "tests": test_results,
        "summary": {
            "total_marks_obtained": float(total_obtained),
            "total_maximum_marks": float(total_max),
            "overall_percentage": overall_percentage,
            "total_sessions": total_sessions,
            "present_sessions": present_sessions,
            "attendance_percentage": att_percentage,
        },
    }


class SettingsInput(BaseModel):
    name: str | None = None
    org_type: str | None = Field(default=None, pattern="^(EDUCATION|CORPORATE)$")
    country_code: str | None = None
    currency_code: str | None = None
    currency: str | None = None
    timezone: str | None = None
    locale: str | None = None
    enabled_modules: list[str] | None = None
    settings: dict | None = None


def _org_settings_payload(organization: Organization) -> dict:
    try:
        modules = json.loads(organization.enabled_modules) if organization.enabled_modules else []
    except Exception:
        modules = []
    try:
        settings_dict = json.loads(organization.settings) if organization.settings else {}
    except Exception:
        settings_dict = {}

    return {
        "id": str(organization.id),
        "name": organization.name,
        "org_type": organization.org_type or "EDUCATION",
        "country_code": organization.country_code,
        "currency_code": organization.currency_code,
        "currency": organization.currency_code,
        "timezone": organization.timezone,
        "locale": organization.locale,
        "enabled_modules": modules,
        "settings": settings_dict,
        "created_at": organization.created_at,
    }


@router.patch("/settings")
def update_settings(request: SettingsInput, principal: Principal = Depends(require_roles("OWNER", "ADMIN")), db: Session = Depends(get_db)):
    organization = db.get(Organization, principal.organization_id)
    if organization is None:
        raise TuiroError("ORGANIZATION_NOT_FOUND", "Organization not found.", 404)
    data = request.model_dump(exclude_unset=True)
    if "currency" in data and "currency_code" not in data:
        data["currency_code"] = data.pop("currency")
    elif "currency" in data:
        data.pop("currency")

    if "currency_code" in data and data["currency_code"]:
        data["currency_code"] = data["currency_code"].upper()

    if "timezone" in data and data["timezone"]:
        try:
            from zoneinfo import ZoneInfo
            ZoneInfo(data["timezone"])
        except Exception:
            raise TuiroError("INVALID_TIMEZONE", f"Invalid timezone '{data['timezone']}'.", 422)

    if "enabled_modules" in data:
        organization.enabled_modules = json.dumps(data.pop("enabled_modules"))

    if "settings" in data:
        current_settings = {}
        if organization.settings:
            try:
                current_settings = json.loads(organization.settings)
            except Exception:
                current_settings = {}
        if isinstance(data["settings"], dict):
            current_settings.update(data["settings"])
            organization.settings = json.dumps(current_settings)
        data.pop("settings")

    for key, value in data.items():
        setattr(organization, key, value)

    db.commit()
    db.refresh(organization)
    return _org_settings_payload(organization)


@router.get("/settings")
def get_settings(principal: Principal = Depends(require_roles("OWNER", "ADMIN")), db: Session = Depends(get_db)):
    organization = db.get(Organization, principal.organization_id)
    if organization is None:
        raise TuiroError("ORGANIZATION_NOT_FOUND", "Organization not found.", 404)
    return _org_settings_payload(organization)


@router.get("/subscription")
def subscription_status(principal: Principal = Depends(require_roles("OWNER", "ADMIN")), db: Session = Depends(get_db)):
    from app.models import Subscription, SubscriptionPlan
    subscription = db.scalar(select(Subscription).where(Subscription.organization_id == principal.organization_id))
    if subscription is None:
        raise TuiroError("SUBSCRIPTION_NOT_FOUND", "Subscription not found.", 404)
    plan = db.get(SubscriptionPlan, subscription.plan_id)
    student_count = db.scalar(select(func.count()).select_from(Student).where(Student.organization_id == principal.organization_id, Student.status == "ACTIVE")) or 0
    return {"status": subscription.status, "plan": plan, "student_count": student_count, "student_limit": plan.student_limit if plan else None}


@router.get("/subscription/plans")
def subscription_plans(principal: Principal = Depends(require_roles("OWNER", "ADMIN")), db: Session = Depends(get_db)):
    from app.models import SubscriptionPlan
    return db.scalars(select(SubscriptionPlan).where(SubscriptionPlan.is_active.is_(True))).all()
