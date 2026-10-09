"""Roles and Permissions API router."""
from __future__ import annotations

import json
from uuid import UUID, uuid4
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.dependencies import Principal, require_authenticated_user, require_roles
from app.core.permissions import ALL_PERMISSION_CODES, DEFAULT_ROLE_PERMISSIONS, PERMISSION_CATALOG
from app.db import get_db
from app.models import OrganizationRole

router = APIRouter()


class PermissionItem(BaseModel):
    code: str
    name: str
    category: str
    description: str


class RoleResponse(BaseModel):
    name: str
    display_name: str
    description: str | None = None
    is_system: bool
    permissions: list[str]


class CreateRoleRequest(BaseModel):
    name: str = Field(min_length=2, max_length=50, pattern="^[A-Z0-9_]+$")
    display_name: str = Field(min_length=2, max_length=100)
    description: str | None = Field(default=None, max_length=255)
    permissions: list[str] = Field(default_factory=list)


class UpdateRoleRequest(BaseModel):
    display_name: str | None = Field(default=None, min_length=2, max_length=100)
    description: str | None = Field(default=None, max_length=255)
    permissions: list[str] = Field(default_factory=list)


def ensure_system_roles_seeded(db: Session, organization_id: UUID) -> None:
    existing = {
        r.name: r
        for r in db.scalars(
            select(OrganizationRole).where(OrganizationRole.organization_id == organization_id)
        ).all()
    }
    for role_name, perms in DEFAULT_ROLE_PERMISSIONS.items():
        if role_name not in existing:
            role = OrganizationRole(
                organization_id=organization_id,
                name=role_name,
                display_name=role_name.replace("_", " ").title(),
                description=f"System default role for {role_name.replace('_', ' ').lower()}",
                is_system=True,
                permissions=json.dumps(sorted(list(perms))),
            )
            db.add(role)
    db.flush()


@router.get("/roles/permissions", response_model=list[PermissionItem])
def list_permission_catalog(
    principal: Principal = Depends(require_authenticated_user),
) -> list[dict]:
    return PERMISSION_CATALOG


@router.get("/roles", response_model=list[RoleResponse])
def list_organization_roles(
    principal: Principal = Depends(require_authenticated_user),
    db: Session = Depends(get_db),
) -> list[RoleResponse]:
    ensure_system_roles_seeded(db, principal.organization_id)
    roles = db.scalars(
        select(OrganizationRole)
        .where(OrganizationRole.organization_id == principal.organization_id)
        .order_by(OrganizationRole.is_system.desc(), OrganizationRole.name)
    ).all()
    result = []
    for r in roles:
        try:
            perms = json.loads(r.permissions) if r.permissions else []
        except Exception:
            perms = []
        result.append(
            RoleResponse(
                name=r.name,
                display_name=r.display_name,
                description=r.description,
                is_system=r.is_system,
                permissions=perms,
            )
        )
    return result


@router.post("/roles", response_model=RoleResponse, status_code=201)
def create_role(
    request: CreateRoleRequest,
    principal: Principal = Depends(require_roles("OWNER", "ADMIN")),
    db: Session = Depends(get_db),
) -> RoleResponse:
    ensure_system_roles_seeded(db, principal.organization_id)
    # Validate permissions exist in catalog
    invalid = set(request.permissions) - ALL_PERMISSION_CODES
    if invalid:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid permissions: {', '.join(sorted(invalid))}",
        )

    # Check for existing role with same name in org
    exists = db.scalar(
        select(OrganizationRole).where(
            OrganizationRole.organization_id == principal.organization_id,
            OrganizationRole.name == request.name,
        )
    )
    if exists:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Role with name '{request.name}' already exists",
        )

    role = OrganizationRole(
        organization_id=principal.organization_id,
        name=request.name,
        display_name=request.display_name,
        description=request.description,
        is_system=False,
        permissions=json.dumps(sorted(list(set(request.permissions)))),
    )
    db.add(role)
    db.commit()
    db.refresh(role)

    return RoleResponse(
        name=role.name,
        display_name=role.display_name,
        description=role.description,
        is_system=role.is_system,
        permissions=json.loads(role.permissions),
    )


@router.put("/roles/{role_name}", response_model=RoleResponse)
def update_role(
    role_name: str,
    request: UpdateRoleRequest,
    principal: Principal = Depends(require_roles("OWNER", "ADMIN")),
    db: Session = Depends(get_db),
) -> RoleResponse:
    ensure_system_roles_seeded(db, principal.organization_id)
    role = db.scalar(
        select(OrganizationRole).where(
            OrganizationRole.organization_id == principal.organization_id,
            OrganizationRole.name == role_name,
        )
    )
    if not role:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Role '{role_name}' not found")

    invalid = set(request.permissions) - ALL_PERMISSION_CODES
    if invalid:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid permissions: {', '.join(sorted(invalid))}",
        )

    if request.display_name:
        role.display_name = request.display_name
    if request.description is not None:
        role.description = request.description
    role.permissions = json.dumps(sorted(list(set(request.permissions))))

    db.commit()
    db.refresh(role)
    return RoleResponse(
        name=role.name,
        display_name=role.display_name,
        description=role.description,
        is_system=role.is_system,
        permissions=json.loads(role.permissions),
    )


@router.delete("/roles/{role_name}", status_code=204)
def delete_role(
    role_name: str,
    principal: Principal = Depends(require_roles("OWNER", "ADMIN")),
    db: Session = Depends(get_db),
) -> None:
    role = db.scalar(
        select(OrganizationRole).where(
            OrganizationRole.organization_id == principal.organization_id,
            OrganizationRole.name == role_name,
        )
    )
    if not role:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Role '{role_name}' not found")
    if role.is_system:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"System role '{role_name}' cannot be deleted",
        )

    db.delete(role)
    db.commit()
