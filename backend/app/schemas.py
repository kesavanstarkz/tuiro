from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class OrganizationItem(BaseModel):
    id: UUID
    name: str
    role: str


class TokenPair(BaseModel):
    access_token: str | None = None
    refresh_token: str | None = None
    token_type: str = "bearer"
    organizations: list[OrganizationItem] = []


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)
    display_name: str = Field(min_length=1, max_length=160)
    organization_name: str = Field(min_length=1, max_length=200)
    country_code: str = Field(default="XX", min_length=2, max_length=2)
    currency_code: str = Field(default="USD", min_length=3, max_length=3)
    timezone: str = "Asia/Kolkata"


class LoginRequest(BaseModel):
    email: EmailStr
    password: str
    organization_id: UUID | None = None


class SwitchOrganizationRequest(BaseModel):
    organization_id: UUID
    refresh_token: str | None = None


class RefreshRequest(BaseModel):
    refresh_token: str = Field(min_length=20)


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    email: EmailStr
    display_name: str
    organization_id: UUID
    role: str


class StudentCreate(BaseModel):
    student_number: str = Field(min_length=1, max_length=80)
    first_name: str = Field(min_length=1, max_length=100)
    last_name: str = ""
    school: str | None = None
    grade: str | None = None
    address: str | None = None
    joining_date: date | None = None
    notes: str | None = None
    status: str = "ACTIVE"


class StudentUpdate(BaseModel):
    student_number: str | None = Field(default=None, min_length=1, max_length=80)
    first_name: str | None = Field(default=None, min_length=1, max_length=100)
    last_name: str | None = None
    school: str | None = None
    grade: str | None = None
    address: str | None = None
    joining_date: date | None = None
    notes: str | None = None
    status: str | None = None


class StudentResponse(StudentCreate):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    organization_id: UUID
    created_at: datetime
    updated_at: datetime


class ParentCreate(BaseModel):
    name: str = Field(min_length=1, max_length=160)
    phone: str | None = None
    email: EmailStr | None = None
    address: str | None = None
    relationship: str | None = None
    status: str = "ACTIVE"


class ParentUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=160)
    phone: str | None = None
    email: EmailStr | None = None
    address: str | None = None
    relationship: str | None = None
    status: str | None = None


class ParentResponse(ParentCreate):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    organization_id: UUID
    created_at: datetime
    updated_at: datetime


class ClassCreate(BaseModel):
    name: str = Field(min_length=1, max_length=160)
    subject: str | None = None
    description: str | None = None
    fee_amount: Decimal = Field(default=0, ge=0)
    status: str = "ACTIVE"


class ClassUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=160)
    subject: str | None = None
    description: str | None = None
    fee_amount: Decimal | None = Field(default=None, ge=0)
    status: str | None = None


class ClassResponse(ClassCreate):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    organization_id: UUID


class PaginatedResponse(BaseModel):
    items: list
    next_cursor: str | None = None
