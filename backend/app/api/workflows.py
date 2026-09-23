from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from uuid import UUID
from urllib.parse import quote

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from io import BytesIO, StringIO
import csv
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.dependencies import Principal, require_authenticated_user, require_roles
from app.core.errors import TuiroError
from app.db import get_db
from app.models import AcademicTest, AttendanceRecord, AttendanceSession, AuditLog, ClassGroup, ClassStudent, ClassTeacher, Homework, Notification, Organization, Payment, Receipt, ScheduleEntry, Student, StudentFee, StudentParent, Parent, Teacher, TestMark
from app.services.receipts import build_receipt_pdf

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


class HomeworkInput(BaseModel):
    class_id: UUID
    title: str = Field(min_length=1, max_length=200)
    description: str | None = None
    due_date: date | None = None


class TestInput(BaseModel):
    class_id: UUID
    name: str = Field(min_length=1, max_length=160)
    subject: str | None = None
    test_date: date
    maximum_marks: Decimal = Field(gt=0)


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


class NotificationInput(BaseModel):
    recipient: str = Field(min_length=1, max_length=320)
    channel: str = "WHATSAPP"
    message: str = Field(min_length=1)
    notification_type: str = "GENERAL"


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


def _fee_payload(db: Session, fee: StudentFee) -> dict:
    paid = db.scalar(select(func.coalesce(func.sum(Payment.amount), 0)).where(Payment.fee_id == fee.id)) or Decimal("0")
    outstanding = max(Decimal("0"), fee.amount_due - paid)
    status = "PAID" if outstanding == 0 else "PARTIAL" if paid else ("OVERDUE" if fee.due_date < date.today() else "PENDING")
    if fee.status != status:
        fee.status = status
    return {"id": fee.id, "student_id": fee.student_id, "student_name": _student_name(db, fee.student_id), "billing_period": fee.billing_period, "amount": fee.amount, "amount_due": fee.amount_due, "paid_amount": paid, "outstanding_amount": outstanding, "due_date": fee.due_date, "status": status}


def _payment_payload(db: Session, payment: Payment) -> dict:
    fee = db.get(StudentFee, payment.fee_id)
    return {"id": payment.id, "fee_id": payment.fee_id, "student_id": payment.student_id, "student_name": _student_name(db, payment.student_id), "amount": payment.amount, "payment_date": payment.payment_date, "payment_method": payment.payment_method, "transaction_reference": payment.transaction_reference, "notes": payment.notes, "billing_period": fee.billing_period if fee else None, "created_at": payment.created_at}


@router.post("/attendance/sessions", status_code=201)
def create_attendance(request: AttendanceSessionInput, principal: Principal = Depends(require_roles("OWNER", "ADMIN", "TEACHER")), db: Session = Depends(get_db)):
    _org_record(db, ClassGroup, principal.organization_id, request.class_id)
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
def list_attendance(session_date: date | None = None, principal: Principal = Depends(require_authenticated_user), db: Session = Depends(get_db)):
    query = select(AttendanceSession).where(AttendanceSession.organization_id == principal.organization_id).order_by(AttendanceSession.session_date.desc())
    if session_date:
        query = query.where(AttendanceSession.session_date == session_date)
    return db.scalars(query.limit(100)).all()


@router.get("/attendance/session")
def attendance_session(class_id: UUID, session_date: date, principal: Principal = Depends(require_authenticated_user), db: Session = Depends(get_db)):
    session = db.scalar(select(AttendanceSession).where(AttendanceSession.organization_id == principal.organization_id, AttendanceSession.class_id == class_id, AttendanceSession.session_date == session_date))
    if session is None:
        return {"session": None, "records": []}
    records = db.scalars(select(AttendanceRecord).where(AttendanceRecord.session_id == session.id)).all()
    return {"session": session, "records": records}


@router.get("/attendance/student/{student_id}")
def student_attendance(student_id: UUID, principal: Principal = Depends(require_authenticated_user), db: Session = Depends(get_db)):
    _org_record(db, Student, principal.organization_id, student_id)
    return db.scalars(select(AttendanceRecord).join(AttendanceSession, AttendanceRecord.session_id == AttendanceSession.id).where(AttendanceSession.organization_id == principal.organization_id, AttendanceRecord.student_id == student_id)).all()


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
def list_fees(status_filter: str | None = Query(None, alias="status"), principal: Principal = Depends(require_authenticated_user), db: Session = Depends(get_db)):
    query = select(StudentFee).where(StudentFee.organization_id == principal.organization_id).order_by(StudentFee.due_date)
    if status_filter:
        query = query.where(StudentFee.status == status_filter)
    fees = db.scalars(query.limit(200)).all()
    payload = [_fee_payload(db, fee) for fee in fees]
    db.commit()
    return [item for item in payload if not status_filter or item["status"] == status_filter]


@router.get("/fees/pending")
def pending_fees(principal: Principal = Depends(require_authenticated_user), db: Session = Depends(get_db)):
    fees = db.scalars(select(StudentFee).where(StudentFee.organization_id == principal.organization_id).order_by(StudentFee.due_date)).all()
    payload = [_fee_payload(db, fee) for fee in fees]
    db.commit()
    return [item for item in payload if item["status"] in {"PENDING", "PARTIAL", "OVERDUE"}]


@router.post("/payments", status_code=201)
def record_payment(request: PaymentInput, principal: Principal = Depends(require_roles("OWNER", "ADMIN")), db: Session = Depends(get_db)):
    fee = _org_record(db, StudentFee, principal.organization_id, request.fee_id)
    if request.transaction_reference and db.scalar(select(Payment).where(Payment.transaction_reference == request.transaction_reference)):
        raise TuiroError("DUPLICATE_PAYMENT", "This transaction reference has already been recorded.", 409)
    paid = db.scalar(select(func.coalesce(func.sum(Payment.amount), 0)).where(Payment.fee_id == fee.id)) or Decimal("0")
    outstanding = fee.amount_due - paid
    if request.amount > outstanding:
        raise TuiroError("PAYMENT_EXCEEDS_BALANCE", "Payment is greater than the outstanding balance.", 400)
    payment = Payment(organization_id=principal.organization_id, fee_id=fee.id, student_id=fee.student_id, amount=request.amount, payment_date=request.payment_date, payment_method=request.payment_method, transaction_reference=request.transaction_reference, notes=request.notes, recorded_by=principal.user.id)
    db.add(payment)
    db.flush()
    new_paid = paid + request.amount
    fee.status = "PAID" if new_paid == fee.amount_due else "PARTIAL"
    receipt_number = f"TUIRO-{datetime.now(timezone.utc).year}-{db.query(Receipt).filter(Receipt.organization_id == principal.organization_id).count() + 1:06d}"
    receipt = Receipt(organization_id=principal.organization_id, payment_id=payment.id, receipt_number=receipt_number)
    db.add(receipt)
    db.add(AuditLog(organization_id=principal.organization_id, user_id=principal.user.id, action="payment_created", entity_type="payment", entity_id=payment.id))
    db.commit()
    return {"payment": _payment_payload(db, payment), "receipt": receipt, "fee_status": fee.status, "remaining": fee.amount_due - new_paid}


@router.get("/payments")
def list_payments(principal: Principal = Depends(require_authenticated_user), db: Session = Depends(get_db)):
    return [_payment_payload(db, payment) for payment in db.scalars(select(Payment).where(Payment.organization_id == principal.organization_id).order_by(Payment.payment_date.desc()).limit(200)).all()]


@router.get("/receipts")
def list_receipts(principal: Principal = Depends(require_authenticated_user), db: Session = Depends(get_db)):
    return db.scalars(select(Receipt).where(Receipt.organization_id == principal.organization_id).order_by(Receipt.issued_at.desc()).limit(200)).all()


@router.get("/receipts/{receipt_id}")
def get_receipt(receipt_id: UUID, principal: Principal = Depends(require_authenticated_user), db: Session = Depends(get_db)):
    return _org_record(db, Receipt, principal.organization_id, receipt_id)


@router.get("/receipts/{receipt_id}/pdf")
def receipt_pdf(receipt_id: UUID, principal: Principal = Depends(require_authenticated_user), db: Session = Depends(get_db)):
    receipt = _org_record(db, Receipt, principal.organization_id, receipt_id)
    payment = db.get(Payment, receipt.payment_id)
    fee = db.get(StudentFee, payment.fee_id) if payment else None
    student = db.get(Student, payment.student_id) if payment else None
    organization = db.get(Organization, principal.organization_id)
    if not payment or not fee or not student or not organization:
        raise TuiroError("RECEIPT_DATA_INCOMPLETE", "Receipt data is incomplete.", 409)
    content = build_receipt_pdf(organization, receipt, payment, fee, student)
    return StreamingResponse(BytesIO(content), media_type="application/pdf", headers={"Content-Disposition": f'attachment; filename="{receipt.receipt_number}.pdf"'})


@router.post("/receipts/{receipt_id}/send")
def send_receipt(receipt_id: UUID, principal: Principal = Depends(require_authenticated_user), db: Session = Depends(get_db)):
    receipt = _org_record(db, Receipt, principal.organization_id, receipt_id)
    return {"receipt_id": receipt.id, "channel": "share", "status": "available", "pdf_url": f"/api/v1/receipts/{receipt.id}/pdf"}


@router.post("/notifications/fee-reminder/{fee_id}")
def fee_reminder(fee_id: UUID, principal: Principal = Depends(require_authenticated_user), db: Session = Depends(get_db)):
    fee = _org_record(db, StudentFee, principal.organization_id, fee_id)
    message = f"Your tuition fee for {fee.billing_period} is due. Amount: {fee.amount_due}."
    notification = Notification(organization_id=principal.organization_id, recipient="parent contact required", channel="WHATSAPP", message=message, notification_type="FEE_REMINDER", status="PENDING")
    db.add(notification); db.commit()
    return {"notification_id": notification.id, "channel": "whatsapp_share", "url": f"https://wa.me/?text={quote(message)}", "message": message, "status": notification.status}


@router.get("/notifications")
def notification_history(principal: Principal = Depends(require_authenticated_user), db: Session = Depends(get_db)):
    return db.scalars(select(Notification).where(Notification.organization_id == principal.organization_id).order_by(Notification.created_at.desc()).limit(200)).all()


@router.post("/notifications", status_code=201)
def create_notification(request: NotificationInput, principal: Principal = Depends(require_roles("OWNER", "ADMIN", "TEACHER")), db: Session = Depends(get_db)):
    # Delivery is deliberately not claimed here: a provider adapter must be configured
    # before messages can transition from PENDING to SENT.
    notification = Notification(organization_id=principal.organization_id, **request.model_dump(), status="PENDING", failure_reason="Delivery provider not configured")
    db.add(notification)
    db.commit()
    db.refresh(notification)
    return notification


@router.post("/homework", status_code=201)
def create_homework(request: HomeworkInput, principal: Principal = Depends(require_roles("OWNER", "ADMIN", "TEACHER")), db: Session = Depends(get_db)):
    _org_record(db, ClassGroup, principal.organization_id, request.class_id)
    record = Homework(organization_id=principal.organization_id, created_by=principal.user.id, **request.model_dump())
    db.add(record); db.commit(); db.refresh(record)
    return record


@router.get("/homework")
def list_homework(principal: Principal = Depends(require_authenticated_user), db: Session = Depends(get_db)):
    return db.scalars(select(Homework).where(Homework.organization_id == principal.organization_id).order_by(Homework.due_date)).all()


@router.patch("/homework/{homework_id}")
def update_homework(homework_id: UUID, request: HomeworkInput, principal: Principal = Depends(require_roles("OWNER", "ADMIN", "TEACHER")), db: Session = Depends(get_db)):
    record = _org_record(db, Homework, principal.organization_id, homework_id)
    _org_record(db, ClassGroup, principal.organization_id, request.class_id)
    for key, value in request.model_dump().items(): setattr(record, key, value)
    db.commit(); db.refresh(record)
    return record


@router.delete("/homework/{homework_id}", status_code=204)
def delete_homework(homework_id: UUID, principal: Principal = Depends(require_roles("OWNER", "ADMIN", "TEACHER")), db: Session = Depends(get_db)):
    db.delete(_org_record(db, Homework, principal.organization_id, homework_id)); db.commit()


@router.post("/tests", status_code=201)
def create_test(request: TestInput, principal: Principal = Depends(require_roles("OWNER", "ADMIN", "TEACHER")), db: Session = Depends(get_db)):
    _org_record(db, ClassGroup, principal.organization_id, request.class_id)
    record = AcademicTest(organization_id=principal.organization_id, **request.model_dump())
    db.add(record); db.commit(); db.refresh(record)
    return record


@router.get("/tests")
def list_tests(principal: Principal = Depends(require_authenticated_user), db: Session = Depends(get_db)):
    return db.scalars(select(AcademicTest).where(AcademicTest.organization_id == principal.organization_id).order_by(AcademicTest.test_date.desc())).all()


@router.patch("/tests/{test_id}")
def update_test(test_id: UUID, request: TestInput, principal: Principal = Depends(require_roles("OWNER", "ADMIN", "TEACHER")), db: Session = Depends(get_db)):
    record = _org_record(db, AcademicTest, principal.organization_id, test_id)
    _org_record(db, ClassGroup, principal.organization_id, request.class_id)
    for key, value in request.model_dump().items(): setattr(record, key, value)
    db.commit(); db.refresh(record)
    return record


@router.delete("/tests/{test_id}", status_code=204)
def delete_test(test_id: UUID, principal: Principal = Depends(require_roles("OWNER", "ADMIN", "TEACHER")), db: Session = Depends(get_db)):
    db.delete(_org_record(db, AcademicTest, principal.organization_id, test_id)); db.commit()


@router.post("/tests/{test_id}/marks", status_code=201)
def record_mark(test_id: UUID, request: MarkInput, principal: Principal = Depends(require_roles("OWNER", "ADMIN", "TEACHER")), db: Session = Depends(get_db)):
    test = _org_record(db, AcademicTest, principal.organization_id, test_id)
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
def list_marks(test_id: UUID, principal: Principal = Depends(require_authenticated_user), db: Session = Depends(get_db)):
    test = _org_record(db, AcademicTest, principal.organization_id, test_id)
    marks = db.scalars(select(TestMark).where(TestMark.organization_id == principal.organization_id, TestMark.test_id == test.id)).all()
    return [{"id": mark.id, "student_id": mark.student_id, "student_name": _student_name(db, mark.student_id), "marks": mark.marks, "maximum_marks": test.maximum_marks, "percentage": round(float(mark.marks / test.maximum_marks * 100), 2), "grade": mark.grade, "remarks": mark.remarks} for mark in marks]


@router.get("/schedule")
def list_schedule(principal: Principal = Depends(require_authenticated_user), db: Session = Depends(get_db)):
    return db.scalars(select(ScheduleEntry).where(ScheduleEntry.organization_id == principal.organization_id).order_by(ScheduleEntry.day_of_week, ScheduleEntry.start_time)).all()


@router.post("/schedule", status_code=201)
def create_schedule(request: ScheduleInput, principal: Principal = Depends(require_roles("OWNER", "ADMIN")), db: Session = Depends(get_db)):
    _org_record(db, ClassGroup, principal.organization_id, request.class_id)
    record = ScheduleEntry(organization_id=principal.organization_id, **request.model_dump()); db.add(record); db.commit(); db.refresh(record)
    return record


@router.patch("/schedule/{schedule_id}")
def update_schedule(schedule_id: UUID, request: ScheduleInput, principal: Principal = Depends(require_roles("OWNER", "ADMIN")), db: Session = Depends(get_db)):
    record = _org_record(db, ScheduleEntry, principal.organization_id, schedule_id)
    _org_record(db, ClassGroup, principal.organization_id, request.class_id)
    for key, value in request.model_dump().items(): setattr(record, key, value)
    db.commit(); db.refresh(record)
    return record


@router.delete("/schedule/{schedule_id}", status_code=204)
def delete_schedule(schedule_id: UUID, principal: Principal = Depends(require_roles("OWNER", "ADMIN")), db: Session = Depends(get_db)):
    db.delete(_org_record(db, ScheduleEntry, principal.organization_id, schedule_id)); db.commit()


@router.get("/dashboard")
def dashboard(principal: Principal = Depends(require_authenticated_user), db: Session = Depends(get_db)):
    from datetime import datetime

    organization = db.get(Organization, principal.organization_id)
    students = db.scalar(select(func.count()).select_from(Student).where(Student.organization_id == principal.organization_id, Student.status == "ACTIVE")) or 0
    today = date.today()
    classes = db.scalar(select(func.count()).select_from(ClassGroup).where(ClassGroup.organization_id == principal.organization_id, ClassGroup.status == "ACTIVE")) or 0
    today_schedules = db.scalars(select(ScheduleEntry).where(ScheduleEntry.organization_id == principal.organization_id, ScheduleEntry.day_of_week == today.weekday()).order_by(ScheduleEntry.start_time)).all()
    classes_today = len(today_schedules)
    attendance_total = db.scalar(select(func.count()).select_from(AttendanceRecord).join(AttendanceSession).where(AttendanceSession.organization_id == principal.organization_id, AttendanceSession.session_date == today)) or 0
    attendance_present = db.scalar(select(func.count()).select_from(AttendanceRecord).join(AttendanceSession).where(AttendanceSession.organization_id == principal.organization_id, AttendanceSession.session_date == today, AttendanceRecord.status.in_(["PRESENT", "LATE"]))) or 0
    pending_fees = db.scalars(select(StudentFee).where(StudentFee.organization_id == principal.organization_id).order_by(StudentFee.due_date)).all()
    pending_items = []
    pending_total = Decimal("0")
    for fee in pending_fees:
        fee_item = _fee_payload(db, fee)
        if fee_item["status"] == "PAID":
            continue
        remaining = fee_item["outstanding_amount"]
        pending_total += remaining
        if len(pending_items) < 5:
            pending_items.append({"id": fee.id, "student_name": fee_item["student_name"], "billing_period": fee.billing_period, "amount": remaining, "due_date": fee.due_date, "status": fee_item["status"]})
    collected = db.scalar(select(func.coalesce(func.sum(Payment.amount), 0)).where(Payment.organization_id == principal.organization_id, Payment.payment_date == date.today())) or Decimal("0")
    recent_payments = db.scalars(select(Payment).where(Payment.organization_id == principal.organization_id).order_by(Payment.created_at.desc()).limit(5)).all()
    recent_items = []
    for payment in recent_payments:
        recent_items.append(_payment_payload(db, payment))
    next_class = None
    current_time = datetime.now().strftime("%H:%M")
    for entry in today_schedules:
        if entry.start_time >= current_time:
            class_group = db.get(ClassGroup, entry.class_id)
            teacher = db.get(Teacher, entry.teacher_id) if entry.teacher_id else None
            student_count = db.scalar(select(func.count()).select_from(ClassStudent).where(ClassStudent.organization_id == principal.organization_id, ClassStudent.class_id == entry.class_id)) or 0
            next_class = {"class_name": class_group.name if class_group else "Class", "subject": class_group.subject if class_group else None, "teacher_name": teacher.employee_number if teacher else None, "start_time": entry.start_time, "end_time": entry.end_time, "room": entry.room, "student_count": student_count}
            break
    db.commit()
    return {"students": students, "active_classes": classes, "classes_today": classes_today, "attendance_percentage": round((attendance_present / attendance_total) * 100, 2) if attendance_total else 0, "pending_fees": pending_total, "todays_collections": collected, "next_class": next_class, "pending_fee_items": pending_items, "recent_payments": recent_items, "currency_code": organization.currency_code if organization else "USD", "role": principal.role}


@router.post("/classes/{class_id}/students", status_code=201)
def assign_student(class_id: UUID, request: AssignmentInput, principal: Principal = Depends(require_roles("OWNER", "ADMIN")), db: Session = Depends(get_db)):
    _org_record(db, ClassGroup, principal.organization_id, class_id)
    _org_record(db, Student, principal.organization_id, request.record_id)
    existing = db.scalar(select(ClassStudent).where(ClassStudent.organization_id == principal.organization_id, ClassStudent.class_id == class_id, ClassStudent.student_id == request.record_id))
    if existing: return existing
    record = ClassStudent(organization_id=principal.organization_id, class_id=class_id, student_id=request.record_id); db.add(record); db.commit(); db.refresh(record); return record


@router.get("/classes/{class_id}/students")
def class_students(class_id: UUID, principal: Principal = Depends(require_authenticated_user), db: Session = Depends(get_db)):
    _org_record(db, ClassGroup, principal.organization_id, class_id)
    return db.scalars(select(Student).join(ClassStudent, ClassStudent.student_id == Student.id).where(ClassStudent.organization_id == principal.organization_id, ClassStudent.class_id == class_id, Student.organization_id == principal.organization_id, Student.status == "ACTIVE")).all()


@router.delete("/classes/{class_id}/students/{student_id}", status_code=204)
def remove_student_from_class(class_id: UUID, student_id: UUID, principal: Principal = Depends(require_roles("OWNER", "ADMIN")), db: Session = Depends(get_db)):
    link = db.scalar(select(ClassStudent).where(ClassStudent.organization_id == principal.organization_id, ClassStudent.class_id == class_id, ClassStudent.student_id == student_id))
    if link is None: raise TuiroError("ENROLLMENT_NOT_FOUND", "Class enrollment not found.", 404)
    db.delete(link); db.commit()


@router.post("/classes/{class_id}/teachers", status_code=201)
def assign_teacher(class_id: UUID, request: AssignmentInput, principal: Principal = Depends(require_roles("OWNER", "ADMIN")), db: Session = Depends(get_db)):
    _org_record(db, ClassGroup, principal.organization_id, class_id)
    _org_record(db, Teacher, principal.organization_id, request.record_id)
    existing = db.scalar(select(ClassTeacher).where(ClassTeacher.organization_id == principal.organization_id, ClassTeacher.class_id == class_id, ClassTeacher.teacher_id == request.record_id))
    if existing: return existing
    record = ClassTeacher(organization_id=principal.organization_id, class_id=class_id, teacher_id=request.record_id); db.add(record); db.commit(); db.refresh(record); return record


@router.get("/classes/{class_id}/teachers")
def class_teachers(class_id: UUID, principal: Principal = Depends(require_authenticated_user), db: Session = Depends(get_db)):
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
def student_parents(student_id: UUID, principal: Principal = Depends(require_authenticated_user), db: Session = Depends(get_db)):
    _org_record(db, Student, principal.organization_id, student_id)
    return db.scalars(select(Parent).join(StudentParent, StudentParent.parent_id == Parent.id).where(StudentParent.organization_id == principal.organization_id, StudentParent.student_id == student_id, Parent.organization_id == principal.organization_id)).all()


@router.get("/parents/{parent_id}/students")
def parent_students(parent_id: UUID, principal: Principal = Depends(require_authenticated_user), db: Session = Depends(get_db)):
    _org_record(db, Parent, principal.organization_id, parent_id)
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
def attendance_report(principal: Principal = Depends(require_authenticated_user), db: Session = Depends(get_db)):
    total = db.scalar(select(func.count()).select_from(AttendanceRecord).join(AttendanceSession).where(AttendanceSession.organization_id == principal.organization_id)) or 0
    present = db.scalar(select(func.count()).select_from(AttendanceRecord).join(AttendanceSession).where(AttendanceSession.organization_id == principal.organization_id, AttendanceRecord.status.in_(["PRESENT", "LATE"]))) or 0
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
    records = db.execute(select(AttendanceSession.session_date, AttendanceSession.class_id, AttendanceRecord.student_id, AttendanceRecord.status).join(AttendanceRecord, AttendanceRecord.session_id == AttendanceSession.id).where(AttendanceSession.organization_id == principal.organization_id).order_by(AttendanceSession.session_date)).all()
    return _csv_response("tuiro-attendance.csv", ["date", "class_id", "student_id", "status"], [list(record) for record in records])


class SettingsInput(BaseModel):
    name: str | None = None
    country_code: str | None = None
    currency_code: str | None = None
    timezone: str | None = None
    locale: str | None = None


@router.patch("/settings")
def update_settings(request: SettingsInput, principal: Principal = Depends(require_roles("OWNER", "ADMIN")), db: Session = Depends(get_db)):
    organization = db.get(Organization, principal.organization_id)
    if organization is None: raise TuiroError("ORGANIZATION_NOT_FOUND", "Organization not found.", 404)
    for key, value in request.model_dump(exclude_none=True).items(): setattr(organization, key, value)
    db.commit(); db.refresh(organization); return organization


@router.get("/settings")
def get_settings(principal: Principal = Depends(require_authenticated_user), db: Session = Depends(get_db)):
    organization = db.get(Organization, principal.organization_id)
    return organization


@router.get("/subscription")
def subscription_status(principal: Principal = Depends(require_authenticated_user), db: Session = Depends(get_db)):
    from app.models import Subscription, SubscriptionPlan
    subscription = db.scalar(select(Subscription).where(Subscription.organization_id == principal.organization_id))
    if subscription is None:
        raise TuiroError("SUBSCRIPTION_NOT_FOUND", "Subscription not found.", 404)
    plan = db.get(SubscriptionPlan, subscription.plan_id)
    student_count = db.scalar(select(func.count()).select_from(Student).where(Student.organization_id == principal.organization_id, Student.status == "ACTIVE")) or 0
    return {"status": subscription.status, "plan": plan, "student_count": student_count, "student_limit": plan.student_limit if plan else None}


@router.get("/subscription/plans")
def subscription_plans(db: Session = Depends(get_db)):
    from app.models import SubscriptionPlan
    return db.scalars(select(SubscriptionPlan).where(SubscriptionPlan.is_active.is_(True))).all()
