"""v2 people foundation for corporate records and shared metadata."""
from __future__ import annotations

import json
from datetime import date
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy import or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.dependencies import Principal, require_roles
from app.core.errors import TuiroError
from app.db import get_db
from app.models import Department, Employee, JobTitle, PersonCustomField, PersonDocument

router = APIRouter(prefix="/people", tags=["people-v2"])
ADMINS = ("OWNER", "ADMIN")
STAFF = ("OWNER", "ADMIN", "TEACHER")


class NamedRecord(BaseModel):
    name: str = Field(min_length=1, max_length=160)
    description: str | None = Field(default=None, max_length=5000)


class EmployeeInput(BaseModel):
    employee_number: str = Field(min_length=1, max_length=80)
    first_name: str = Field(min_length=1, max_length=100)
    last_name: str = ""
    email: str | None = None
    phone: str | None = None
    department_id: UUID | None = None
    job_title_id: UUID | None = None
    manager_id: UUID | None = None
    employment_type: str = "FULL_TIME"
    start_date: date | None = None
    status: str = "ACTIVE"


class EmployeePatch(BaseModel):
    employee_number: str | None = Field(default=None, min_length=1, max_length=80)
    first_name: str | None = Field(default=None, min_length=1, max_length=100)
    last_name: str | None = None
    email: str | None = None
    phone: str | None = None
    department_id: UUID | None = None
    job_title_id: UUID | None = None
    manager_id: UUID | None = None
    employment_type: str | None = None
    start_date: date | None = None
    status: str | None = None


class CustomFields(BaseModel):
    values: dict[str, object]


class PersonDocumentInput(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    storage_key: str = Field(min_length=1, max_length=500)


def _owned(db: Session, model, organization_id: UUID, record_id: UUID, name: str):
    row = db.scalar(select(model).where(model.id == record_id, model.organization_id == organization_id))
    if row is None:
        raise TuiroError(f"{name.upper()}_NOT_FOUND", f"The requested {name} was not found.", 404)
    return row


def _employee_payload(row: Employee) -> dict:
    return {key: (str(value) if isinstance(value, UUID) else value) for key, value in {
        "id": row.id, "employee_number": row.employee_number, "first_name": row.first_name, "last_name": row.last_name,
        "email": row.email, "phone": row.phone, "department_id": row.department_id, "job_title_id": row.job_title_id,
        "manager_id": row.manager_id, "employment_type": row.employment_type, "start_date": row.start_date, "status": row.status,
    }.items()}


def _entity_type(entity_type: str) -> None:
    if entity_type not in {"student", "teacher", "parent", "employee"}:
        raise TuiroError("PERSON_TYPE_NOT_FOUND", "The requested person type was not found.", 404)


@router.get("/departments")
def list_departments(principal: Principal = Depends(require_roles(*STAFF)), db: Session = Depends(get_db)):
    return db.scalars(select(Department).where(Department.organization_id == principal.organization_id).order_by(Department.name)).all()


@router.post("/departments", status_code=201)
def create_department(request: NamedRecord, principal: Principal = Depends(require_roles(*ADMINS)), db: Session = Depends(get_db)):
    row = Department(organization_id=principal.organization_id, **request.model_dump()); db.add(row)
    try: db.commit()
    except IntegrityError as error:
        db.rollback(); raise TuiroError("DUPLICATE_DEPARTMENT", "A department with that name already exists.", 409) from error
    db.refresh(row); return row


@router.get("/job-titles")
def list_job_titles(principal: Principal = Depends(require_roles(*STAFF)), db: Session = Depends(get_db)):
    return db.scalars(select(JobTitle).where(JobTitle.organization_id == principal.organization_id).order_by(JobTitle.name)).all()


@router.post("/job-titles", status_code=201)
def create_job_title(request: NamedRecord, principal: Principal = Depends(require_roles(*ADMINS)), db: Session = Depends(get_db)):
    row = JobTitle(organization_id=principal.organization_id, **request.model_dump()); db.add(row)
    try: db.commit()
    except IntegrityError as error:
        db.rollback(); raise TuiroError("DUPLICATE_JOB_TITLE", "A job title with that name already exists.", 409) from error
    db.refresh(row); return row


@router.get("/employees")
def list_employees(search: str | None = None, include_archived: bool = False, principal: Principal = Depends(require_roles(*STAFF)), db: Session = Depends(get_db)):
    statement = select(Employee).where(Employee.organization_id == principal.organization_id)
    if not include_archived: statement = statement.where(Employee.status == "ACTIVE")
    if search:
        pattern = f"%{search}%"; statement = statement.where(or_(Employee.first_name.ilike(pattern), Employee.last_name.ilike(pattern), Employee.employee_number.ilike(pattern), Employee.email.ilike(pattern)))
    return [_employee_payload(row) for row in db.scalars(statement.order_by(Employee.first_name, Employee.last_name)).all()]


@router.post("/employees", status_code=201)
def create_employee(request: EmployeeInput, principal: Principal = Depends(require_roles(*ADMINS)), db: Session = Depends(get_db)):
    values = request.model_dump()
    for model, key, name in ((Department, "department_id", "department"), (JobTitle, "job_title_id", "job title"), (Employee, "manager_id", "manager")):
        if values[key]: _owned(db, model, principal.organization_id, values[key], name)
    row = Employee(organization_id=principal.organization_id, **values); db.add(row)
    try: db.commit()
    except IntegrityError as error:
        db.rollback(); raise TuiroError("DUPLICATE_EMPLOYEE_NUMBER", "That employee number is already in use.", 409) from error
    db.refresh(row); return _employee_payload(row)


@router.get("/employees/{employee_id:uuid}")
def get_employee(employee_id: UUID, principal: Principal = Depends(require_roles(*STAFF)), db: Session = Depends(get_db)):
    return _employee_payload(_owned(db, Employee, principal.organization_id, employee_id, "employee"))


@router.patch("/employees/{employee_id:uuid}")
def update_employee(employee_id: UUID, request: EmployeePatch, principal: Principal = Depends(require_roles(*ADMINS)), db: Session = Depends(get_db)):
    row = _owned(db, Employee, principal.organization_id, employee_id, "employee")
    values = request.model_dump(exclude_unset=True)
    if values.get("manager_id") == employee_id: raise TuiroError("INVALID_MANAGER", "An employee cannot manage themselves.", 422)
    for key, value in values.items(): setattr(row, key, value)
    try: db.commit()
    except IntegrityError as error:
        db.rollback(); raise TuiroError("DUPLICATE_EMPLOYEE_NUMBER", "That employee number is already in use.", 409) from error
    db.refresh(row); return _employee_payload(row)


@router.post("/{entity_type}/{entity_id:uuid}/custom-fields")
def set_custom_fields(entity_type: str, entity_id: UUID, request: CustomFields, principal: Principal = Depends(require_roles(*ADMINS)), db: Session = Depends(get_db)):
    # IDs intentionally remain polymorphic: person entities retain separate
    # domain tables while this metadata layer stays reusable.
    _entity_type(entity_type)
    for key, value in request.values.items():
        row = db.scalar(select(PersonCustomField).where(PersonCustomField.organization_id == principal.organization_id, PersonCustomField.entity_type == entity_type, PersonCustomField.entity_id == entity_id, PersonCustomField.field_key == key))
        if row: row.value_json = json.dumps(value)
        else: db.add(PersonCustomField(organization_id=principal.organization_id, entity_type=entity_type, entity_id=entity_id, field_key=key, value_json=json.dumps(value)))
    db.commit(); return {"values": request.values}


@router.get("/{entity_type}/{entity_id:uuid}/custom-fields")
def get_custom_fields(entity_type: str, entity_id: UUID, principal: Principal = Depends(require_roles(*STAFF)), db: Session = Depends(get_db)):
    _entity_type(entity_type)
    rows = db.scalars(select(PersonCustomField).where(PersonCustomField.organization_id == principal.organization_id, PersonCustomField.entity_type == entity_type, PersonCustomField.entity_id == entity_id)).all()
    return {"values": {row.field_key: json.loads(row.value_json) for row in rows}}


@router.post("/{entity_type}/{entity_id:uuid}/documents", status_code=201)
def attach_document(entity_type: str, entity_id: UUID, request: PersonDocumentInput, principal: Principal = Depends(require_roles(*ADMINS)), db: Session = Depends(get_db)):
    _entity_type(entity_type)
    row = PersonDocument(organization_id=principal.organization_id, entity_type=entity_type, entity_id=entity_id, **request.model_dump()); db.add(row); db.commit(); db.refresh(row); return row
