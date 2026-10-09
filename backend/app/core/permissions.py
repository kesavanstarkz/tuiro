"""Unified Permission Matrix for Tuiro SaaS.

Enforces role-based permissions across roles:
SUPER_ADMIN, OWNER, ADMIN, TEACHER, PARENT, STUDENT.
"""
from __future__ import annotations

from typing import TYPE_CHECKING, Set, Tuple
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

if TYPE_CHECKING:
    from app.core.dependencies import Principal

OWNER_ADMIN: Set[str] = {"OWNER", "ADMIN"}
STAFF: Set[str] = {"OWNER", "ADMIN", "TEACHER"}
PORTAL_READ: Set[str] = {"OWNER", "ADMIN", "PARENT", "STUDENT"}
ALL_ORG_ROLES: Set[str] = {"OWNER", "ADMIN", "TEACHER", "PARENT", "STUDENT"}
EVERYONE_AUTHENTICATED: Set[str] = {"SUPER_ADMIN", "OWNER", "ADMIN", "TEACHER", "PARENT", "STUDENT"}

# Exact permission matrix table covering every API operation
PERMISSION_MATRIX: dict[Tuple[str, str], Set[str]] = {
    # Auth & Sessions
    ("GET", "/api/v1/me"): EVERYONE_AUTHENTICATED,
    ("POST", "/api/v1/auth/logout"): EVERYONE_AUTHENTICATED,
    ("POST", "/api/v1/auth/switch-organization"): EVERYONE_AUTHENTICATED,
    ("POST", "/api/v1/auth/invites"): OWNER_ADMIN,
    ("GET", "/api/v1/auth/invites"): OWNER_ADMIN,
    ("DELETE", "/api/v1/auth/invites/{invite_id}"): OWNER_ADMIN,

    # Roles & Permissions
    ("GET", "/api/v1/roles/permissions"): EVERYONE_AUTHENTICATED,
    ("GET", "/api/v1/roles"): EVERYONE_AUTHENTICATED,
    ("POST", "/api/v1/roles"): OWNER_ADMIN,
    ("PUT", "/api/v1/roles/{role_name}"): OWNER_ADMIN,
    ("DELETE", "/api/v1/roles/{role_name}"): OWNER_ADMIN,

    # Terminology
    ("GET", "/api/v1/terminology"): EVERYONE_AUTHENTICATED,
    ("GET", "/api/v1/terminology/templates"): EVERYONE_AUTHENTICATED,
    ("PUT", "/api/v1/terminology"): OWNER_ADMIN,
    ("POST", "/api/v1/terminology/apply-template/{template_name}"): OWNER_ADMIN,

    # Students (Teacher gets read-only student roster; Owner/Admin manage)
    ("GET", "/api/v1/students"): STAFF,
    ("POST", "/api/v1/students"): OWNER_ADMIN,
    ("GET", "/api/v1/students/{record_id}"): ALL_ORG_ROLES,
    ("PATCH", "/api/v1/students/{record_id}"): OWNER_ADMIN,
    ("DELETE", "/api/v1/students/{record_id}"): OWNER_ADMIN,

    # Parents
    ("GET", "/api/v1/parents"): OWNER_ADMIN,
    ("POST", "/api/v1/parents"): OWNER_ADMIN,
    ("GET", "/api/v1/parents/{record_id}"): {"OWNER", "ADMIN", "PARENT"},
    ("PATCH", "/api/v1/parents/{record_id}"): OWNER_ADMIN,
    ("DELETE", "/api/v1/parents/{record_id}"): OWNER_ADMIN,

    # Classes
    ("GET", "/api/v1/classes"): ALL_ORG_ROLES,
    ("POST", "/api/v1/classes"): OWNER_ADMIN,
    ("GET", "/api/v1/classes/{record_id}"): ALL_ORG_ROLES,
    ("PATCH", "/api/v1/classes/{record_id}"): OWNER_ADMIN,
    ("DELETE", "/api/v1/classes/{record_id}"): OWNER_ADMIN,

    # Class enrollment & teacher assignment
    ("POST", "/api/v1/classes/{class_id}/students"): OWNER_ADMIN,
    ("GET", "/api/v1/classes/{class_id}/students"): STAFF,
    ("DELETE", "/api/v1/classes/{class_id}/students/{student_id}"): OWNER_ADMIN,
    ("POST", "/api/v1/classes/{class_id}/teachers"): OWNER_ADMIN,
    ("GET", "/api/v1/classes/{class_id}/teachers"): STAFF,
    ("DELETE", "/api/v1/classes/{class_id}/teachers/{teacher_id}"): OWNER_ADMIN,

    # Teachers
    ("GET", "/api/v1/teachers"): STAFF,
    ("POST", "/api/v1/teachers"): OWNER_ADMIN,
    ("GET", "/api/v1/teachers/{record_id}"): STAFF,
    ("PATCH", "/api/v1/teachers/{record_id}"): OWNER_ADMIN,
    ("DELETE", "/api/v1/teachers/{record_id}"): OWNER_ADMIN,

    # Student Parents links
    ("POST", "/api/v1/students/{student_id}/parents"): OWNER_ADMIN,
    ("GET", "/api/v1/students/{student_id}/parents"): ALL_ORG_ROLES,
    ("GET", "/api/v1/parents/{parent_id}/students"): {"OWNER", "ADMIN", "PARENT"},
    ("DELETE", "/api/v1/students/{student_id}/parents/{parent_id}"): OWNER_ADMIN,

    # Groups
    ("GET", "/api/v1/groups"): ALL_ORG_ROLES,
    ("POST", "/api/v1/groups"): OWNER_ADMIN,
    ("GET", "/api/v1/groups/{group_id:uuid}"): ALL_ORG_ROLES,
    ("GET", "/api/v1/groups/{group_id:uuid}/members"): STAFF,
    ("GET", "/api/v1/groups/students/{group_id:uuid}"): STAFF,
    ("POST", "/api/v1/groups/{group_id:uuid}/members/{student_id:uuid}"): OWNER_ADMIN,
    ("DELETE", "/api/v1/groups/{group_id:uuid}/members/{student_id:uuid}"): OWNER_ADMIN,
    ("GET", "/api/v1/groups/{group_id:uuid}/schedule"): ALL_ORG_ROLES,
    ("POST", "/api/v1/groups/{group_id:uuid}/schedule"): OWNER_ADMIN,

    # Group Assignments
    ("POST", "/api/v1/groups/assignments"): STAFF,
    ("GET", "/api/v1/groups/assignments"): ALL_ORG_ROLES,
    ("DELETE", "/api/v1/groups/assignments/{assignment_id:uuid}"): STAFF,

    # Group Fees (Teacher has no fee access)
    ("POST", "/api/v1/groups/fees"): OWNER_ADMIN,
    ("GET", "/api/v1/groups/fees/needs-attention"): OWNER_ADMIN,
    ("POST", "/api/v1/groups/fees/{fee_id:uuid}/payments"): OWNER_ADMIN,

    # Group Attendance
    ("POST", "/api/v1/groups/{group_id:uuid}/attendance"): STAFF,
    ("GET", "/api/v1/groups/{group_id:uuid}/attendance"): STAFF,
    ("GET", "/api/v1/groups/{group_id:uuid}/attendance/history"): STAFF,
    ("GET", "/api/v1/groups/students/{student_id:uuid}/attendance"): ALL_ORG_ROLES,
    ("GET", "/api/v1/groups/students/{student_id}/view"): PORTAL_READ,

    # Group Chat & Direct Messages
    ("POST", "/api/v1/groups/{group_id:uuid}/chat"): ALL_ORG_ROLES,
    ("GET", "/api/v1/groups/{group_id:uuid}/chat"): ALL_ORG_ROLES,
    ("POST", "/api/v1/groups/chats/direct/{participant_id:uuid}"): ALL_ORG_ROLES,
    ("GET", "/api/v1/groups/chats/direct/{participant_id:uuid}"): ALL_ORG_ROLES,

    # Attendance (class-based)
    ("POST", "/api/v1/attendance/sessions"): STAFF,
    ("GET", "/api/v1/attendance/sessions"): STAFF,
    ("GET", "/api/v1/attendance/session"): STAFF,
    ("GET", "/api/v1/attendance/student/{student_id}"): ALL_ORG_ROLES,

    # Fees & Payments (class-based)
    ("POST", "/api/v1/fees/generate"): OWNER_ADMIN,
    ("POST", "/api/v1/fees"): OWNER_ADMIN,
    ("GET", "/api/v1/fees"): PORTAL_READ,
    ("GET", "/api/v1/fees/pending"): PORTAL_READ,
    ("POST", "/api/v1/payments"): OWNER_ADMIN,
    ("GET", "/api/v1/payments"): PORTAL_READ,

    # Receipts
    ("GET", "/api/v1/receipts"): PORTAL_READ,
    ("GET", "/api/v1/receipts/{receipt_id}"): PORTAL_READ,
    ("GET", "/api/v1/receipts/{receipt_id}/pdf"): PORTAL_READ,
    ("POST", "/api/v1/receipts/{receipt_id}/send"): OWNER_ADMIN,

    # Notifications
    ("POST", "/api/v1/notifications/fee-reminder/{fee_id}"): OWNER_ADMIN,
    ("GET", "/api/v1/notifications"): ALL_ORG_ROLES,
    ("POST", "/api/v1/notifications"): STAFF,

    # Homework
    ("POST", "/api/v1/homework"): STAFF,
    ("GET", "/api/v1/homework"): ALL_ORG_ROLES,
    ("PATCH", "/api/v1/homework/{homework_id}"): STAFF,
    ("DELETE", "/api/v1/homework/{homework_id}"): STAFF,

    # Tests
    ("POST", "/api/v1/tests"): STAFF,
    ("GET", "/api/v1/tests"): ALL_ORG_ROLES,
    ("PATCH", "/api/v1/tests/{test_id}"): STAFF,
    ("DELETE", "/api/v1/tests/{test_id}"): STAFF,
    ("POST", "/api/v1/tests/{test_id}/marks"): STAFF,
    ("GET", "/api/v1/tests/{test_id}/marks"): ALL_ORG_ROLES,

    # Schedule
    ("GET", "/api/v1/schedule"): ALL_ORG_ROLES,
    ("POST", "/api/v1/schedule"): OWNER_ADMIN,
    ("PATCH", "/api/v1/schedule/{schedule_id}"): OWNER_ADMIN,
    ("DELETE", "/api/v1/schedule/{schedule_id}"): OWNER_ADMIN,

    # Dashboard & Reports
    ("GET", "/api/v1/dashboard"): OWNER_ADMIN,
    ("GET", "/api/v1/audit-logs"): OWNER_ADMIN,
    ("GET", "/api/v1/reports/fees"): OWNER_ADMIN,
    ("GET", "/api/v1/reports/attendance"): OWNER_ADMIN,
    ("GET", "/api/v1/reports/fees/export.csv"): OWNER_ADMIN,
    ("GET", "/api/v1/reports/attendance/export.csv"): OWNER_ADMIN,

    # Settings & Subscription
    ("PATCH", "/api/v1/settings"): OWNER_ADMIN,
    ("GET", "/api/v1/settings"): OWNER_ADMIN,
    ("GET", "/api/v1/subscription"): OWNER_ADMIN,
    ("GET", "/api/v1/subscription/plans"): OWNER_ADMIN,
}


def roles_for(method: str, path: str) -> tuple[str, ...]:
    """Retrieve allowed roles for a given method and path template."""
    key = (method.upper(), path)
    if key in PERMISSION_MATRIX:
        return tuple(sorted(PERMISSION_MATRIX[key]))
    return ("OWNER", "ADMIN")


def check_teacher_class_access(db: Session, principal: Principal, class_id: UUID) -> None:
    if principal.role == "TEACHER":
        from app.models import ClassTeacher, ScheduleEntry, Teacher
        teacher = db.scalar(
            select(Teacher).where(
                Teacher.organization_id == principal.organization_id,
                Teacher.user_id == principal.user.id
            )
        )
        if not teacher:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Teacher is not assigned to this class")
        assigned = db.scalar(
            select(ClassTeacher).where(
                ClassTeacher.organization_id == principal.organization_id,
                ClassTeacher.class_id == class_id,
                ClassTeacher.teacher_id == teacher.id
            )
        )
        if not assigned:
            assigned_sched = db.scalar(
                select(ScheduleEntry).where(
                    ScheduleEntry.organization_id == principal.organization_id,
                    ScheduleEntry.class_id == class_id,
                    ScheduleEntry.teacher_id == teacher.id
                )
            )
            if not assigned_sched:
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Teacher is not assigned to this class")


def check_parent_student_access(db: Session, principal: Principal, student_id: UUID) -> None:
    if principal.role == "PARENT":
        from app.models import Parent, StudentParent
        parent = db.scalar(
            select(Parent).where(
                Parent.organization_id == principal.organization_id,
                Parent.user_id == principal.user.id
            )
        )
        if not parent:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Student not found")
        link = db.scalar(
            select(StudentParent).where(
                StudentParent.organization_id == principal.organization_id,
                StudentParent.parent_id == parent.id,
                StudentParent.student_id == student_id
            )
        )
        if not link:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Student not found")


def check_student_self_access(db: Session, principal: Principal, student_id: UUID) -> None:
    if principal.role == "STUDENT":
        from app.models import Student
        student = db.scalar(
            select(Student).where(
                Student.organization_id == principal.organization_id,
                Student.id == student_id,
                Student.user_id == principal.user.id
            )
        )
        if not student:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Student not found")


def get_parent_student_ids(db: Session, principal: Principal) -> set[UUID]:
    if principal.role == "PARENT":
        from app.models import Parent, StudentParent
        parent = db.scalar(
            select(Parent).where(
                Parent.organization_id == principal.organization_id,
                Parent.user_id == principal.user.id
            )
        )
        if not parent:
            return set()
        return set(db.scalars(
            select(StudentParent.student_id).where(
                StudentParent.organization_id == principal.organization_id,
                StudentParent.parent_id == parent.id
            )
        ).all())
    return set()


def get_student_self_id(db: Session, principal: Principal) -> UUID | None:
    if principal.role == "STUDENT":
        from app.models import Student
        student = db.scalar(
            select(Student).where(
                Student.organization_id == principal.organization_id,
                Student.user_id == principal.user.id
            )
        )
        return student.id if student else None
    return None


# ---------------------------------------------------------------------------
# P1-01: Permission Catalog & Configurable Roles
# ---------------------------------------------------------------------------

class PermissionCode:
    # Organization & Administration
    ORG_READ = "org:read"
    ORG_UPDATE = "org:update"
    ORG_MODULES_MANAGE = "org:modules:manage"
    ROLES_MANAGE = "roles:manage"
    MEMBERS_MANAGE = "members:manage"

    # People (Employees, Students, Teachers, Parents)
    PEOPLE_READ = "people:read"
    PEOPLE_WRITE = "people:write"

    # Groups (Teams, Classes, Batches, Departments)
    GROUPS_READ = "groups:read"
    GROUPS_WRITE = "groups:write"

    # Attendance & Time
    ATTENDANCE_READ = "attendance:read"
    ATTENDANCE_WRITE = "attendance:write"

    # Requests & Leaves
    REQUESTS_READ = "requests:read"
    REQUESTS_CREATE = "requests:create"
    REQUESTS_APPROVE = "requests:approve"

    # Tasks & Work
    TASKS_READ = "tasks:read"
    TASKS_WRITE = "tasks:write"

    # Collaboration
    COMMUNICATION_ACCESS = "communication:access"
    CALENDAR_ACCESS = "calendar:access"

    # Files
    FILES_READ = "files:read"
    FILES_WRITE = "files:write"

    # Finance
    FINANCE_READ = "finance:read"
    FINANCE_WRITE = "finance:write"

    # Reports & Audit
    REPORTS_READ = "reports:read"
    AUDIT_LOG_READ = "audit_log:read"


PERMISSION_CATALOG: list[dict] = [
    {"code": PermissionCode.ORG_READ, "name": "View Organization Details", "category": "Administration", "description": "View organization profile, settings, and enabled modules."},
    {"code": PermissionCode.ORG_UPDATE, "name": "Update Organization Details", "category": "Administration", "description": "Update organization profile, timezone, currency, and settings."},
    {"code": PermissionCode.ORG_MODULES_MANAGE, "name": "Manage Modules", "category": "Administration", "description": "Enable or disable platform modules for the organization."},
    {"code": PermissionCode.ROLES_MANAGE, "name": "Manage Roles & Permissions", "category": "Administration", "description": "Create, modify, and assign custom roles and permission sets."},
    {"code": PermissionCode.MEMBERS_MANAGE, "name": "Manage Members & Invites", "category": "Administration", "description": "Invite, manage, and remove organization members."},
    {"code": PermissionCode.PEOPLE_READ, "name": "View People Directory", "category": "People", "description": "View employee or student directories and profiles."},
    {"code": PermissionCode.PEOPLE_WRITE, "name": "Manage People Directory", "category": "People", "description": "Create, edit, archive, and link people records."},
    {"code": PermissionCode.GROUPS_READ, "name": "View Groups", "category": "Groups", "description": "View teams, classes, batches, and group rosters."},
    {"code": PermissionCode.GROUPS_WRITE, "name": "Manage Groups", "category": "Groups", "description": "Create, edit, and manage group rosters and memberships."},
    {"code": PermissionCode.ATTENDANCE_READ, "name": "View Attendance Records", "category": "Attendance", "description": "View attendance registers, summaries, and reports."},
    {"code": PermissionCode.ATTENDANCE_WRITE, "name": "Record Attendance", "category": "Attendance", "description": "Record check-ins, check-outs, and mark session registers."},
    {"code": PermissionCode.REQUESTS_READ, "name": "View Requests", "category": "Requests", "description": "View leave, attendance correction, or permission requests."},
    {"code": PermissionCode.REQUESTS_CREATE, "name": "Submit Requests", "category": "Requests", "description": "Submit leave or permission requests."},
    {"code": PermissionCode.REQUESTS_APPROVE, "name": "Approve Requests", "category": "Requests", "description": "Approve or reject requests in approval chains."},
    {"code": PermissionCode.TASKS_READ, "name": "View Tasks & Work", "category": "Work", "description": "View personal, team, or class tasks and assignments."},
    {"code": PermissionCode.TASKS_WRITE, "name": "Manage Tasks & Work", "category": "Work", "description": "Create, assign, edit, and grade tasks and work items."},
    {"code": PermissionCode.COMMUNICATION_ACCESS, "name": "Communication & Collaboration", "category": "Communication", "description": "Participate in group chats, direct messages, and view announcements."},
    {"code": PermissionCode.CALENDAR_ACCESS, "name": "View Calendar & Schedule", "category": "Calendar", "description": "Access organization, team, or class calendar and timetables."},
    {"code": PermissionCode.FILES_READ, "name": "View Files", "category": "Files", "description": "View and download shared organization and group files."},
    {"code": PermissionCode.FILES_WRITE, "name": "Manage Files", "category": "Files", "description": "Upload, categorize, and delete files."},
    {"code": PermissionCode.FINANCE_READ, "name": "View Finances", "category": "Finance", "description": "View fee invoices, payments, receipts, or payroll records."},
    {"code": PermissionCode.FINANCE_WRITE, "name": "Manage Finances", "category": "Finance", "description": "Issue fees, process payments, generate receipts, and record payroll."},
    {"code": PermissionCode.REPORTS_READ, "name": "View Analytics & Reports", "category": "Reports", "description": "Access dashboard metrics, attendance reports, and financial summaries."},
    {"code": PermissionCode.AUDIT_LOG_READ, "name": "View Audit Logs", "category": "Security", "description": "Inspect security, authentication, and financial audit trails."},
]

ALL_PERMISSION_CODES: set[str] = {p["code"] for p in PERMISSION_CATALOG}

DEFAULT_ROLE_PERMISSIONS: dict[str, set[str]] = {
    "SUPER_ADMIN": ALL_PERMISSION_CODES,
    "OWNER": ALL_PERMISSION_CODES,
    "ADMIN": {
        PermissionCode.ORG_READ,
        PermissionCode.ORG_UPDATE,
        PermissionCode.ORG_MODULES_MANAGE,
        PermissionCode.ROLES_MANAGE,
        PermissionCode.MEMBERS_MANAGE,
        PermissionCode.PEOPLE_READ,
        PermissionCode.PEOPLE_WRITE,
        PermissionCode.GROUPS_READ,
        PermissionCode.GROUPS_WRITE,
        PermissionCode.ATTENDANCE_READ,
        PermissionCode.ATTENDANCE_WRITE,
        PermissionCode.REQUESTS_READ,
        PermissionCode.REQUESTS_CREATE,
        PermissionCode.REQUESTS_APPROVE,
        PermissionCode.TASKS_READ,
        PermissionCode.TASKS_WRITE,
        PermissionCode.COMMUNICATION_ACCESS,
        PermissionCode.CALENDAR_ACCESS,
        PermissionCode.FILES_READ,
        PermissionCode.FILES_WRITE,
        PermissionCode.FINANCE_READ,
        PermissionCode.FINANCE_WRITE,
        PermissionCode.REPORTS_READ,
        PermissionCode.AUDIT_LOG_READ,
    },
    "TEACHER": {
        PermissionCode.PEOPLE_READ,
        PermissionCode.GROUPS_READ,
        PermissionCode.ATTENDANCE_READ,
        PermissionCode.ATTENDANCE_WRITE,
        PermissionCode.REQUESTS_CREATE,
        PermissionCode.REQUESTS_READ,
        PermissionCode.TASKS_READ,
        PermissionCode.TASKS_WRITE,
        PermissionCode.COMMUNICATION_ACCESS,
        PermissionCode.CALENDAR_ACCESS,
        PermissionCode.FILES_READ,
    },
    "PARENT": {
        PermissionCode.PEOPLE_READ,
        PermissionCode.ATTENDANCE_READ,
        PermissionCode.TASKS_READ,
        PermissionCode.FINANCE_READ,
        PermissionCode.CALENDAR_ACCESS,
        PermissionCode.COMMUNICATION_ACCESS,
    },
    "STUDENT": {
        PermissionCode.PEOPLE_READ,
        PermissionCode.ATTENDANCE_READ,
        PermissionCode.TASKS_READ,
        PermissionCode.CALENDAR_ACCESS,
        PermissionCode.COMMUNICATION_ACCESS,
    },
}


