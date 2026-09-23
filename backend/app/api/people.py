from __future__ import annotations

from datetime import date
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from app.core.dependencies import Principal, require_authenticated_user, require_roles
from app.db import get_db
from app.schemas import ClassCreate, ClassResponse, ParentCreate, ParentResponse, StudentCreate, StudentResponse
from app.services import people

router = APIRouter()


class TeacherCreate(BaseModel):
    employee_number: str | None = None
    specialization: str | None = None
    joining_date: date | None = None
    status: str = "ACTIVE"


class TeacherResponse(TeacherCreate):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    organization_id: UUID
    user_id: UUID | None


def _list(kind: str, response_model, search: str | None, limit: int, offset: int, principal: Principal, db: Session):
    return people.list_records(db, principal.organization_id, kind, search, limit, offset)


@router.get("/students", response_model=list[StudentResponse])
def list_students(search: str | None = None, limit: int = Query(50, ge=1, le=100), offset: int = Query(0, ge=0), principal: Principal = Depends(require_authenticated_user), db: Session = Depends(get_db)):
    return _list("students", StudentResponse, search, limit, offset, principal, db)


@router.post("/students", response_model=StudentResponse, status_code=status.HTTP_201_CREATED)
def create_student(request: StudentCreate, principal: Principal = Depends(require_roles("OWNER", "ADMIN")), db: Session = Depends(get_db)):
    return people.create_record(db, principal.organization_id, "students", request.model_dump())


@router.get("/students/{record_id}", response_model=StudentResponse)
def get_student(record_id: UUID, principal: Principal = Depends(require_authenticated_user), db: Session = Depends(get_db)):
    return people.get_record(db, principal.organization_id, "students", record_id)


@router.patch("/students/{record_id}", response_model=StudentResponse)
def update_student(record_id: UUID, request: StudentCreate, principal: Principal = Depends(require_roles("OWNER", "ADMIN")), db: Session = Depends(get_db)):
    return people.update_record(db, principal.organization_id, "students", record_id, request.model_dump())


@router.delete("/students/{record_id}", status_code=204)
def delete_student(record_id: UUID, principal: Principal = Depends(require_roles("OWNER", "ADMIN")), db: Session = Depends(get_db)):
    people.delete_record(db, principal.organization_id, "students", record_id)


@router.get("/parents", response_model=list[ParentResponse])
def list_parents(search: str | None = None, limit: int = Query(50, ge=1, le=100), offset: int = Query(0, ge=0), principal: Principal = Depends(require_authenticated_user), db: Session = Depends(get_db)):
    return _list("parents", ParentResponse, search, limit, offset, principal, db)


@router.post("/parents", response_model=ParentResponse, status_code=201)
def create_parent(request: ParentCreate, principal: Principal = Depends(require_roles("OWNER", "ADMIN")), db: Session = Depends(get_db)):
    return people.create_record(db, principal.organization_id, "parents", request.model_dump())


@router.get("/parents/{record_id}", response_model=ParentResponse)
def get_parent(record_id: UUID, principal: Principal = Depends(require_authenticated_user), db: Session = Depends(get_db)):
    return people.get_record(db, principal.organization_id, "parents", record_id)


@router.patch("/parents/{record_id}", response_model=ParentResponse)
def update_parent(record_id: UUID, request: ParentCreate, principal: Principal = Depends(require_roles("OWNER", "ADMIN")), db: Session = Depends(get_db)):
    return people.update_record(db, principal.organization_id, "parents", record_id, request.model_dump())


@router.delete("/parents/{record_id}", status_code=204)
def delete_parent(record_id: UUID, principal: Principal = Depends(require_roles("OWNER", "ADMIN")), db: Session = Depends(get_db)):
    people.delete_record(db, principal.organization_id, "parents", record_id)


@router.get("/classes", response_model=list[ClassResponse])
def list_classes(search: str | None = None, limit: int = Query(50, ge=1, le=100), offset: int = Query(0, ge=0), principal: Principal = Depends(require_authenticated_user), db: Session = Depends(get_db)):
    return _list("classes", ClassResponse, search, limit, offset, principal, db)


@router.post("/classes", response_model=ClassResponse, status_code=201)
def create_class(request: ClassCreate, principal: Principal = Depends(require_roles("OWNER", "ADMIN")), db: Session = Depends(get_db)):
    return people.create_record(db, principal.organization_id, "classes", request.model_dump())


@router.get("/classes/{record_id}", response_model=ClassResponse)
def get_class(record_id: UUID, principal: Principal = Depends(require_authenticated_user), db: Session = Depends(get_db)):
    return people.get_record(db, principal.organization_id, "classes", record_id)


@router.patch("/classes/{record_id}", response_model=ClassResponse)
def update_class(record_id: UUID, request: ClassCreate, principal: Principal = Depends(require_roles("OWNER", "ADMIN")), db: Session = Depends(get_db)):
    return people.update_record(db, principal.organization_id, "classes", record_id, request.model_dump())


@router.delete("/classes/{record_id}", status_code=204)
def delete_class(record_id: UUID, principal: Principal = Depends(require_roles("OWNER", "ADMIN")), db: Session = Depends(get_db)):
    people.delete_record(db, principal.organization_id, "classes", record_id)


@router.get("/teachers", response_model=list[TeacherResponse])
def list_teachers(principal: Principal = Depends(require_authenticated_user), db: Session = Depends(get_db)):
    return people.list_records(db, principal.organization_id, "teachers", None, 100, 0)


@router.post("/teachers", response_model=TeacherResponse, status_code=201)
def create_teacher(request: TeacherCreate, principal: Principal = Depends(require_roles("OWNER", "ADMIN")), db: Session = Depends(get_db)):
    return people.create_record(db, principal.organization_id, "teachers", request.model_dump())


@router.get("/teachers/{record_id}", response_model=TeacherResponse)
def get_teacher(record_id: UUID, principal: Principal = Depends(require_authenticated_user), db: Session = Depends(get_db)):
    return people.get_record(db, principal.organization_id, "teachers", record_id)


@router.patch("/teachers/{record_id}", response_model=TeacherResponse)
def update_teacher(record_id: UUID, request: TeacherCreate, principal: Principal = Depends(require_roles("OWNER", "ADMIN")), db: Session = Depends(get_db)):
    return people.update_record(db, principal.organization_id, "teachers", record_id, request.model_dump())


@router.delete("/teachers/{record_id}", status_code=204)
def delete_teacher(record_id: UUID, principal: Principal = Depends(require_roles("OWNER", "ADMIN")), db: Session = Depends(get_db)):
    people.delete_record(db, principal.organization_id, "teachers", record_id)
