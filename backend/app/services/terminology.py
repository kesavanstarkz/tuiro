"""Centralized Terminology Engine for Tuiro SaaS."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any
from uuid import UUID, uuid4
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Organization, OrganizationTerminology

CANONICAL_CONCEPTS = [
    "person",
    "group",
    "work_item",
    "supervisor",
    "org_admin",
    "leave_request",
    "attendance",
    "fee",
]

STARTER_TEMPLATES: dict[str, dict[str, dict[str, str]]] = {
    "EDUCATION": {
        "person": {"singular": "Student", "plural": "Students"},
        "group": {"singular": "Class", "plural": "Classes"},
        "work_item": {"singular": "Homework", "plural": "Homework"},
        "supervisor": {"singular": "Coordinator", "plural": "Coordinators"},
        "org_admin": {"singular": "Center Admin", "plural": "Center Admins"},
        "leave_request": {"singular": "Leave Request", "plural": "Leave Requests"},
        "attendance": {"singular": "Attendance", "plural": "Attendance"},
        "fee": {"singular": "Fee", "plural": "Fees"},
    },
    "CORPORATE": {
        "person": {"singular": "Employee", "plural": "Employees"},
        "group": {"singular": "Team", "plural": "Teams"},
        "work_item": {"singular": "Task", "plural": "Tasks"},
        "supervisor": {"singular": "Manager", "plural": "Managers"},
        "org_admin": {"singular": "HR Admin", "plural": "HR Admins"},
        "leave_request": {"singular": "Leave Request", "plural": "Leave Requests"},
        "attendance": {"singular": "Attendance", "plural": "Attendance"},
        "fee": {"singular": "Invoice", "plural": "Invoices"},
    },
}

# Per-organization in-memory terminology cache
_TERMINOLOGY_CACHE: dict[UUID, dict[str, Any]] = {}


def get_starter_templates() -> dict[str, dict[str, dict[str, str]]]:
    return STARTER_TEMPLATES


def resolve_terminology(template_name: str, custom_terms: dict[str, dict[str, str]]) -> dict[str, dict[str, str]]:
    base_template = STARTER_TEMPLATES.get(template_name.upper(), STARTER_TEMPLATES["EDUCATION"])
    merged: dict[str, dict[str, str]] = {}
    for concept in CANONICAL_CONCEPTS:
        default_pair = base_template.get(concept, {"singular": concept.title(), "plural": f"{concept.title()}s"})
        override_pair = custom_terms.get(concept, {})
        merged[concept] = {
            "singular": override_pair.get("singular", default_pair["singular"]),
            "plural": override_pair.get("plural", default_pair["plural"]),
        }
    return merged


def get_organization_terminology(db: Session, organization_id: UUID) -> dict[str, Any]:
    if organization_id in _TERMINOLOGY_CACHE:
        return _TERMINOLOGY_CACHE[organization_id]

    record = db.scalar(
        select(OrganizationTerminology).where(OrganizationTerminology.organization_id == organization_id)
    )
    if not record:
        org = db.get(Organization, organization_id)
        default_template = (org.org_type if org and org.org_type else "EDUCATION").upper()
        if default_template not in STARTER_TEMPLATES:
            default_template = "EDUCATION"
        record = OrganizationTerminology(
            id=uuid4(),
            organization_id=organization_id,
            template=default_template,
            terms="{}",
        )
        db.add(record)
        db.commit()
        db.refresh(record)

    try:
        custom_terms = json.loads(record.terms) if record.terms else {}
    except Exception:
        custom_terms = {}

    resolved = resolve_terminology(record.template, custom_terms)
    payload = {
        "organization_id": str(organization_id),
        "template": record.template,
        "terms": resolved,
        "updated_at": record.updated_at.isoformat() if record.updated_at else datetime.now(timezone.utc).isoformat(),
    }
    _TERMINOLOGY_CACHE[organization_id] = payload
    return payload


def update_organization_terminology(
    db: Session,
    organization_id: UUID,
    terms: dict[str, dict[str, str]],
    template: str | None = None,
) -> dict[str, Any]:
    record = db.scalar(
        select(OrganizationTerminology).where(OrganizationTerminology.organization_id == organization_id)
    )
    if not record:
        record = OrganizationTerminology(
            id=uuid4(),
            organization_id=organization_id,
            template=(template or "EDUCATION").upper(),
            terms="{}",
        )
        db.add(record)

    if template:
        tpl_clean = template.upper()
        if tpl_clean in STARTER_TEMPLATES:
            record.template = tpl_clean

    try:
        existing = json.loads(record.terms) if record.terms else {}
    except Exception:
        existing = {}

    for concept, pair in terms.items():
        if concept in CANONICAL_CONCEPTS and isinstance(pair, dict):
            existing[concept] = {
                "singular": str(pair.get("singular", concept.title())).strip(),
                "plural": str(pair.get("plural", f"{concept.title()}s")).strip(),
            }

    record.terms = json.dumps(existing)
    record.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(record)

    # Invalidate and re-populate cache
    _TERMINOLOGY_CACHE.pop(organization_id, None)
    return get_organization_terminology(db, organization_id)


def apply_terminology_template(db: Session, organization_id: UUID, template_name: str) -> dict[str, Any]:
    tpl_clean = template_name.upper()
    if tpl_clean not in STARTER_TEMPLATES:
        raise ValueError(f"Unknown template: '{template_name}'. Available: {list(STARTER_TEMPLATES.keys())}")

    record = db.scalar(
        select(OrganizationTerminology).where(OrganizationTerminology.organization_id == organization_id)
    )
    if not record:
        record = OrganizationTerminology(
            id=uuid4(),
            organization_id=organization_id,
            template=tpl_clean,
            terms="{}",
        )
        db.add(record)
    else:
        record.template = tpl_clean
        record.terms = "{}"  # Reset custom overrides to follow the new template defaults cleanly
        record.updated_at = datetime.now(timezone.utc)

    db.commit()
    db.refresh(record)
    _TERMINOLOGY_CACHE.pop(organization_id, None)
    return get_organization_terminology(db, organization_id)
