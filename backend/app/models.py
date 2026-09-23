from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from typing import Optional
from uuid import UUID, uuid4

from sqlalchemy import Boolean, CheckConstraint, Date, DateTime, ForeignKey, Index, Integer, Numeric, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


class Role(str, Enum):
    SUPER_ADMIN = "SUPER_ADMIN"
    OWNER = "OWNER"
    ADMIN = "ADMIN"
    TEACHER = "TEACHER"
    PARENT = "PARENT"
    STUDENT = "STUDENT"


class User(Base):
    __tablename__ = "users"
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    display_name: Mapped[str] = mapped_column(String(160))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    memberships: Mapped[list["OrganizationMember"]] = relationship(back_populates="user", cascade="all, delete-orphan")


class Organization(Base):
    __tablename__ = "organizations"
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String(200))
    country_code: Mapped[str] = mapped_column(String(2), default="XX")
    currency_code: Mapped[str] = mapped_column(String(3), default="USD")
    timezone: Mapped[str] = mapped_column(String(80), default="UTC")
    locale: Mapped[str] = mapped_column(String(20), default="en")
    settings: Mapped[str] = mapped_column(Text, default="{}")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    memberships: Mapped[list["OrganizationMember"]] = relationship(back_populates="organization", cascade="all, delete-orphan")


class OrganizationMember(Base):
    __tablename__ = "organization_members"
    __table_args__ = (UniqueConstraint("organization_id", "user_id"),)
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    organization_id: Mapped[UUID] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"), index=True)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    role: Mapped[str] = mapped_column(String(30), default=Role.OWNER.value)
    permissions: Mapped[str] = mapped_column(Text, default="{}")
    user: Mapped[User] = relationship(back_populates="memberships")
    organization: Mapped[Organization] = relationship(back_populates="memberships")


class RefreshSession(Base):
    __tablename__ = "refresh_sessions"
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    revoked_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class AuditLog(Base):
    __tablename__ = "audit_logs"
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    organization_id: Mapped[UUID] = mapped_column(ForeignKey("organizations.id"), index=True)
    user_id: Mapped[Optional[UUID]] = mapped_column(ForeignKey("users.id"), index=True)
    action: Mapped[str] = mapped_column(String(80))
    entity_type: Mapped[str] = mapped_column(String(80))
    entity_id: Mapped[Optional[UUID]] = mapped_column(index=True)
    metadata_json: Mapped[str] = mapped_column(Text, default="{}")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Student(Base):
    __tablename__ = "students"
    __table_args__ = (UniqueConstraint("organization_id", "student_number"), Index("ix_students_org_name", "organization_id", "last_name", "first_name"))
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    # Optional account links let the API enforce student/parent scoped views.
    user_id: Mapped[Optional[UUID]] = mapped_column(ForeignKey("users.id"), unique=True, nullable=True, index=True)
    organization_id: Mapped[UUID] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"), index=True)
    student_number: Mapped[str] = mapped_column(String(80))
    first_name: Mapped[str] = mapped_column(String(100))
    last_name: Mapped[str] = mapped_column(String(100), default="")
    profile_photo: Mapped[Optional[str]] = mapped_column(String(500))
    school: Mapped[Optional[str]] = mapped_column(String(200))
    grade: Mapped[Optional[str]] = mapped_column(String(80))
    address: Mapped[Optional[str]] = mapped_column(Text)
    joining_date: Mapped[Optional[date]] = mapped_column(Date)
    status: Mapped[str] = mapped_column(String(30), default="ACTIVE", index=True)
    notes: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class Parent(Base):
    __tablename__ = "parents"
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    user_id: Mapped[Optional[UUID]] = mapped_column(ForeignKey("users.id"), unique=True, nullable=True, index=True)
    organization_id: Mapped[UUID] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(160))
    phone: Mapped[Optional[str]] = mapped_column(String(40), index=True)
    email: Mapped[Optional[str]] = mapped_column(String(320))
    address: Mapped[Optional[str]] = mapped_column(Text)
    relationship: Mapped[Optional[str]] = mapped_column(String(60))
    status: Mapped[str] = mapped_column(String(30), default="ACTIVE")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class StudentParent(Base):
    __tablename__ = "student_parents"
    __table_args__ = (UniqueConstraint("student_id", "parent_id"),)
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    organization_id: Mapped[UUID] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"), index=True)
    student_id: Mapped[UUID] = mapped_column(ForeignKey("students.id", ondelete="CASCADE"), index=True)
    parent_id: Mapped[UUID] = mapped_column(ForeignKey("parents.id", ondelete="CASCADE"), index=True)
    is_primary: Mapped[bool] = mapped_column(Boolean, default=False)


class Teacher(Base):
    __tablename__ = "teachers"
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    organization_id: Mapped[UUID] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"), index=True)
    user_id: Mapped[Optional[UUID]] = mapped_column(ForeignKey("users.id"), index=True)
    employee_number: Mapped[Optional[str]] = mapped_column(String(80))
    specialization: Mapped[Optional[str]] = mapped_column(String(160))
    joining_date: Mapped[Optional[date]] = mapped_column(Date)
    status: Mapped[str] = mapped_column(String(30), default="ACTIVE")


class ClassGroup(Base):
    __tablename__ = "classes"
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    organization_id: Mapped[UUID] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(160))
    subject: Mapped[Optional[str]] = mapped_column(String(120))
    description: Mapped[Optional[str]] = mapped_column(Text)
    fee_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0)
    status: Mapped[str] = mapped_column(String(30), default="ACTIVE")


class ClassStudent(Base):
    __tablename__ = "class_students"
    __table_args__ = (UniqueConstraint("class_id", "student_id"),)
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    organization_id: Mapped[UUID] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"), index=True)
    class_id: Mapped[UUID] = mapped_column(ForeignKey("classes.id", ondelete="CASCADE"), index=True)
    student_id: Mapped[UUID] = mapped_column(ForeignKey("students.id", ondelete="CASCADE"), index=True)
    enrolled_on: Mapped[date] = mapped_column(Date, default=date.today)


class ClassTeacher(Base):
    __tablename__ = "class_teachers"
    __table_args__ = (UniqueConstraint("class_id", "teacher_id"),)
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    organization_id: Mapped[UUID] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"), index=True)
    class_id: Mapped[UUID] = mapped_column(ForeignKey("classes.id", ondelete="CASCADE"), index=True)
    teacher_id: Mapped[UUID] = mapped_column(ForeignKey("teachers.id", ondelete="CASCADE"), index=True)
    is_primary: Mapped[bool] = mapped_column(Boolean, default=False)


# Group-centric domain.  These tables deliberately do not fan out records to
# students: membership is evaluated when a student's view is requested.
class Group(Base):
    __tablename__ = "groups"
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    organization_id: Mapped[UUID] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(160))
    created_by: Mapped[UUID] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class GroupMember(Base):
    __tablename__ = "group_members"
    __table_args__ = (UniqueConstraint("group_id", "student_id"),)
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    organization_id: Mapped[UUID] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"), index=True)
    group_id: Mapped[UUID] = mapped_column(ForeignKey("groups.id", ondelete="CASCADE"), index=True)
    student_id: Mapped[UUID] = mapped_column(ForeignKey("students.id", ondelete="CASCADE"), index=True)
    joined_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    removed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)


class GroupSchedule(Base):
    __tablename__ = "group_schedules"
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    organization_id: Mapped[UUID] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"), index=True)
    group_id: Mapped[UUID] = mapped_column(ForeignKey("groups.id", ondelete="CASCADE"), index=True)
    day_of_week: Mapped[int] = mapped_column(Integer)
    start_time: Mapped[str] = mapped_column(String(10))
    end_time: Mapped[str] = mapped_column(String(10))
    subject: Mapped[Optional[str]] = mapped_column(String(120))


class Assignment(Base):
    __tablename__ = "assignments"
    __table_args__ = (
        CheckConstraint("(group_id IS NOT NULL AND student_id IS NULL) OR (group_id IS NULL AND student_id IS NOT NULL)", name="assignment_exactly_one_target"),
        Index("ix_assignments_org_target", "organization_id", "group_id", "student_id"),
    )
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    organization_id: Mapped[UUID] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"), index=True)
    group_id: Mapped[Optional[UUID]] = mapped_column(ForeignKey("groups.id", ondelete="CASCADE"), nullable=True)
    student_id: Mapped[Optional[UUID]] = mapped_column(ForeignKey("students.id", ondelete="CASCADE"), nullable=True)
    title: Mapped[str] = mapped_column(String(200))
    description: Mapped[Optional[str]] = mapped_column(Text)
    due_date: Mapped[Optional[date]] = mapped_column(Date, index=True)
    type: Mapped[str] = mapped_column(String(20))
    attachments: Mapped[str] = mapped_column(Text, default="[]")
    # Overrides use this to replace one inherited item instead of duplicating it.
    overrides_id: Mapped[Optional[UUID]] = mapped_column(ForeignKey("assignments.id"), nullable=True, index=True)
    created_by: Mapped[UUID] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class GroupFee(Base):
    __tablename__ = "fees"
    __table_args__ = (
        CheckConstraint("(group_id IS NOT NULL AND student_id IS NULL) OR (group_id IS NULL AND student_id IS NOT NULL)", name="fee_exactly_one_target"),
        Index("ix_group_fees_org_target", "organization_id", "group_id", "student_id"),
    )
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    organization_id: Mapped[UUID] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"), index=True)
    group_id: Mapped[Optional[UUID]] = mapped_column(ForeignKey("groups.id", ondelete="CASCADE"), nullable=True)
    student_id: Mapped[Optional[UUID]] = mapped_column(ForeignKey("students.id", ondelete="CASCADE"), nullable=True)
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    due_date: Mapped[date] = mapped_column(Date, index=True)
    status: Mapped[str] = mapped_column(String(20), default="PENDING")
    overrides_id: Mapped[Optional[UUID]] = mapped_column(ForeignKey("fees.id"), nullable=True, index=True)
    created_by: Mapped[UUID] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class FeePayment(Base):
    """A student's settlement for a shared or individual fee definition."""
    __tablename__ = "fee_payments"
    __table_args__ = (UniqueConstraint("fee_id", "student_id"),)
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    fee_id: Mapped[UUID] = mapped_column(ForeignKey("fees.id", ondelete="CASCADE"), index=True)
    student_id: Mapped[UUID] = mapped_column(ForeignKey("students.id", ondelete="CASCADE"), index=True)
    status: Mapped[str] = mapped_column(String(20), default="PENDING")
    paid_on: Mapped[Optional[date]] = mapped_column(Date)
    amount_paid: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0)


class GroupAttendanceSession(Base):
    __tablename__ = "group_attendance_sessions"
    __table_args__ = (UniqueConstraint("organization_id", "group_id", "session_date"),)
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    organization_id: Mapped[UUID] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"), index=True)
    group_id: Mapped[UUID] = mapped_column(ForeignKey("groups.id", ondelete="CASCADE"), index=True)
    session_date: Mapped[date] = mapped_column(Date, index=True)
    created_by: Mapped[UUID] = mapped_column(ForeignKey("users.id"))


class GroupAttendanceRecord(Base):
    __tablename__ = "group_attendance_records"
    __table_args__ = (UniqueConstraint("session_id", "student_id"),)
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    session_id: Mapped[UUID] = mapped_column(ForeignKey("group_attendance_sessions.id", ondelete="CASCADE"), index=True)
    student_id: Mapped[UUID] = mapped_column(ForeignKey("students.id", ondelete="CASCADE"), index=True)
    status: Mapped[str] = mapped_column(String(20))
    notes: Mapped[Optional[str]] = mapped_column(Text)


class ChatThread(Base):
    __tablename__ = "chat_threads"
    __table_args__ = (CheckConstraint("(type = 'GROUP' AND group_id IS NOT NULL) OR (type = 'DIRECT' AND group_id IS NULL)", name="valid_thread_target"),)
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    organization_id: Mapped[UUID] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"), index=True)
    type: Mapped[str] = mapped_column(String(12))
    group_id: Mapped[Optional[UUID]] = mapped_column(ForeignKey("groups.id", ondelete="CASCADE"), nullable=True, unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class ChatParticipant(Base):
    __tablename__ = "chat_participants"
    __table_args__ = (UniqueConstraint("thread_id", "user_id"),)
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    thread_id: Mapped[UUID] = mapped_column(ForeignKey("chat_threads.id", ondelete="CASCADE"), index=True)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)


class ChatMessage(Base):
    __tablename__ = "chat_messages"
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    thread_id: Mapped[UUID] = mapped_column(ForeignKey("chat_threads.id", ondelete="CASCADE"), index=True)
    sender_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"))
    text: Mapped[str] = mapped_column(Text)
    attachment: Mapped[Optional[str]] = mapped_column(Text)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class AttendanceSession(Base):
    __tablename__ = "attendance_sessions"
    __table_args__ = (UniqueConstraint("organization_id", "class_id", "session_date"),)
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    organization_id: Mapped[UUID] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"), index=True)
    class_id: Mapped[UUID] = mapped_column(ForeignKey("classes.id", ondelete="CASCADE"), index=True)
    session_date: Mapped[date] = mapped_column(Date, index=True)
    teacher_id: Mapped[Optional[UUID]] = mapped_column(ForeignKey("teachers.id"))
    created_by: Mapped[UUID] = mapped_column(ForeignKey("users.id"))


class AttendanceRecord(Base):
    __tablename__ = "attendance_records"
    __table_args__ = (UniqueConstraint("session_id", "student_id"),)
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    session_id: Mapped[UUID] = mapped_column(ForeignKey("attendance_sessions.id", ondelete="CASCADE"), index=True)
    student_id: Mapped[UUID] = mapped_column(ForeignKey("students.id", ondelete="CASCADE"), index=True)
    status: Mapped[str] = mapped_column(String(20))
    notes: Mapped[Optional[str]] = mapped_column(Text)


class StudentFee(Base):
    __tablename__ = "student_fees"
    __table_args__ = (UniqueConstraint("organization_id", "student_id", "billing_period"), Index("ix_fees_org_status", "organization_id", "status"))
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    organization_id: Mapped[UUID] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"), index=True)
    student_id: Mapped[UUID] = mapped_column(ForeignKey("students.id", ondelete="CASCADE"), index=True)
    billing_period: Mapped[str] = mapped_column(String(30))
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    discount: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0)
    fine: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0)
    amount_due: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    due_date: Mapped[date] = mapped_column(Date, index=True)
    status: Mapped[str] = mapped_column(String(20), default="DUE", index=True)


class Payment(Base):
    __tablename__ = "payments"
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    organization_id: Mapped[UUID] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"), index=True)
    fee_id: Mapped[UUID] = mapped_column(ForeignKey("student_fees.id"), index=True)
    student_id: Mapped[UUID] = mapped_column(ForeignKey("students.id"), index=True)
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    payment_date: Mapped[date] = mapped_column(Date, index=True)
    payment_method: Mapped[str] = mapped_column(String(30))
    transaction_reference: Mapped[Optional[str]] = mapped_column(String(160), unique=True)
    notes: Mapped[Optional[str]] = mapped_column(Text)
    recorded_by: Mapped[UUID] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Receipt(Base):
    __tablename__ = "receipts"
    __table_args__ = (UniqueConstraint("organization_id", "receipt_number"),)
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    organization_id: Mapped[UUID] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"), index=True)
    payment_id: Mapped[UUID] = mapped_column(ForeignKey("payments.id"), unique=True)
    receipt_number: Mapped[str] = mapped_column(String(80), index=True)
    issued_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Homework(Base):
    __tablename__ = "homework"
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    organization_id: Mapped[UUID] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"), index=True)
    class_id: Mapped[UUID] = mapped_column(ForeignKey("classes.id", ondelete="CASCADE"), index=True)
    title: Mapped[str] = mapped_column(String(200))
    description: Mapped[Optional[str]] = mapped_column(Text)
    due_date: Mapped[Optional[date]] = mapped_column(Date, index=True)
    created_by: Mapped[UUID] = mapped_column(ForeignKey("users.id"))


class AcademicTest(Base):
    __tablename__ = "academic_tests"
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    organization_id: Mapped[UUID] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"), index=True)
    class_id: Mapped[UUID] = mapped_column(ForeignKey("classes.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(160))
    subject: Mapped[Optional[str]] = mapped_column(String(120))
    test_date: Mapped[date] = mapped_column(Date)
    maximum_marks: Mapped[Decimal] = mapped_column(Numeric(12, 2))


class TestMark(Base):
    __tablename__ = "test_marks"
    __table_args__ = (UniqueConstraint("test_id", "student_id"),)
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    organization_id: Mapped[UUID] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"), index=True)
    test_id: Mapped[UUID] = mapped_column(ForeignKey("academic_tests.id", ondelete="CASCADE"), index=True)
    student_id: Mapped[UUID] = mapped_column(ForeignKey("students.id", ondelete="CASCADE"), index=True)
    marks: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    grade: Mapped[Optional[str]] = mapped_column(String(20))
    remarks: Mapped[Optional[str]] = mapped_column(Text)


class ScheduleEntry(Base):
    __tablename__ = "schedule_entries"
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    organization_id: Mapped[UUID] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"), index=True)
    class_id: Mapped[UUID] = mapped_column(ForeignKey("classes.id", ondelete="CASCADE"), index=True)
    teacher_id: Mapped[Optional[UUID]] = mapped_column(ForeignKey("teachers.id"))
    day_of_week: Mapped[int] = mapped_column(Integer)
    start_time: Mapped[str] = mapped_column(String(10))
    end_time: Mapped[str] = mapped_column(String(10))
    room: Mapped[Optional[str]] = mapped_column(String(120))


class SubscriptionPlan(Base):
    __tablename__ = "subscription_plans"
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String(80), unique=True)
    monthly_price: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0)
    annual_price: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0)
    student_limit: Mapped[Optional[int]] = mapped_column(Integer)
    teacher_limit: Mapped[Optional[int]] = mapped_column(Integer)
    features: Mapped[str] = mapped_column(Text, default="{}")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class Subscription(Base):
    __tablename__ = "subscriptions"
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    organization_id: Mapped[UUID] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"), unique=True)
    plan_id: Mapped[UUID] = mapped_column(ForeignKey("subscription_plans.id"))
    status: Mapped[str] = mapped_column(String(30), default="TRIAL")
    trial_ends_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    current_period_end: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))


class Notification(Base):
    __tablename__ = "notifications"
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    organization_id: Mapped[UUID] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"), index=True)
    recipient: Mapped[str] = mapped_column(String(320))
    channel: Mapped[str] = mapped_column(String(30))
    message: Mapped[str] = mapped_column(Text)
    notification_type: Mapped[str] = mapped_column(String(40))
    status: Mapped[str] = mapped_column(String(20), default="PENDING")
    failure_reason: Mapped[Optional[str]] = mapped_column(Text)
    sent_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
