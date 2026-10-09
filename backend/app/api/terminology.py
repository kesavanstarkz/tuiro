"""Terminology API Router."""
from __future__ import annotations

from typing import Any
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.dependencies import Principal, require_authenticated_user, require_roles
from app.db import get_db
from app.services import terminology

router = APIRouter()


class TermPair(BaseModel):
    singular: str = Field(min_length=1, max_length=50)
    plural: str = Field(min_length=1, max_length=50)


class UpdateTerminologyRequest(BaseModel):
    template: str | None = None
    terms: dict[str, TermPair] = Field(default_factory=dict)


class TerminologyResponse(BaseModel):
    organization_id: str
    template: str
    terms: dict[str, TermPair]
    updated_at: str


@router.get("/terminology", response_model=TerminologyResponse)
def get_terminology(
    principal: Principal = Depends(require_authenticated_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    return terminology.get_organization_terminology(db, principal.organization_id)


@router.put("/terminology", response_model=TerminologyResponse)
def update_terminology(
    request: UpdateTerminologyRequest,
    principal: Principal = Depends(require_roles("OWNER", "ADMIN")),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    terms_dict = {k: v.model_dump() for k, v in request.terms.items()}
    return terminology.update_organization_terminology(
        db,
        organization_id=principal.organization_id,
        terms=terms_dict,
        template=request.template,
    )


@router.get("/terminology/templates")
def list_terminology_templates(
    principal: Principal = Depends(require_authenticated_user),
) -> dict[str, Any]:
    return terminology.get_starter_templates()


@router.post("/terminology/apply-template/{template_name}", response_model=TerminologyResponse)
def apply_template(
    template_name: str,
    principal: Principal = Depends(require_roles("OWNER", "ADMIN")),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    try:
        return terminology.apply_terminology_template(
            db,
            organization_id=principal.organization_id,
            template_name=template_name,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
