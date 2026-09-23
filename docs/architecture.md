# Tuiro Architecture

## Product boundary

Tuiro is a global, multi-tenant SaaS product for small education businesses. The organization is the tenant boundary. Country, currency, timezone, locale, terminology, tax rules, and enabled payment/communication providers are organization configuration, never application constants.

## System architecture

```text
Expo React Native app
  -> HTTPS REST /api/v1
FastAPI API layer
  -> authentication, authorization, request/response schemas
Service layer
  -> fee, payment, receipt, attendance, subscription rules
Repository layer
  -> tenant-scoped SQLAlchemy queries
PostgreSQL (Neon in production)
```

The mobile app stores access and refresh tokens in Expo SecureStore and never connects to PostgreSQL. TanStack Query owns server state; Zustand owns session and UI state. Axios is configured once with access-token injection and refresh handling.

## Backend boundaries

- `api/`: versioned routers and dependency injection
- `schemas/`: Pydantic request and response contracts
- `services/`: business workflows and transaction boundaries
- `repositories/`: SQLAlchemy persistence, always requiring organization context
- `models/`: database mappings
- `core/`: settings, security, database session, permissions
- `integrations/`: payment, communication, storage, and PDF provider adapters
- `jobs/`: deferred fee generation, reminders, PDF, and exports

Repositories must not accept an unscoped query from an API handler. A service receives an authenticated principal and organization context, verifies access, then calls a repository with `organization_id` explicitly. Database constraints are the second line of defense.

## Identity and authorization

Roles are `SUPER_ADMIN`, `OWNER`, `ADMIN`, `TEACHER`, `PARENT`, and `STUDENT`. Organization roles are separate from the platform super-admin role. Permission checks are centralized and combine role, organization membership, resource ownership, and feature entitlements.

- Super admins access platform administration only.
- Owners/admins manage organization operations according to configured permissions.
- Teachers see assigned classes/students and academic workflows, not finances by default.
- Parents see only their linked students.
- Students see only their own permitted records.

Access tokens are short-lived JWTs. Refresh tokens are rotated, stored hashed in the database, revocable, and bound to a user/session. Passwords use Argon2id or bcrypt through a maintained password-hashing library. No secrets are placed in `EXPO_PUBLIC_*` variables.

## Critical transactional workflows

### Fee generation

`FeeGenerationService` selects active students and creates one monthly fee per `(organization_id, student_id, billing_period)`. That compound key is unique, so retries are idempotent.

### Payment

Within one database transaction: lock the fee, validate the payment amount against the outstanding balance, insert an immutable payment, recalculate fee status, create an optional receipt, write an audit event, and commit. A duplicate provider transaction reference is rejected by a tenant-scoped unique constraint.

### Notifications

Domain events such as `PaymentRecorded` and `AttendanceMarkedAbsent` are created after the domain transaction succeeds. Delivery is delegated to `CommunicationProvider` implementations and logged with provider status. Personal WhatsApp automation is not assumed; MVP uses share/deep-link flows where appropriate.

## API conventions

- Prefix: `/api/v1`
- JSON request and response schemas only; never expose ORM objects directly.
- Paginated collections use `{items, next_cursor}`.
- Errors use `{success: false, error: {code, message, details?}}`.
- `401` means missing/invalid authentication; `403` means authenticated but forbidden; `404` does not reveal cross-tenant resource existence.
- Dates are ISO 8601; money is decimal in the API and PostgreSQL `numeric(12,2)` in storage; locale formatting happens at the client edge.

## Mobile navigation

Primary tabs: Dashboard, Students, Attendance, Fees, More.

More routes: Teachers, Parents, Classes, Homework, Tests, Schedule, Receipts, Reports, Notifications, Settings, Subscription.

Each feature screen has loading, error/retry, empty, and success states. The first vertical slice is `Students -> Fees -> Payments -> Receipts -> Reminder`; this is the product's highest-value workflow.

## Delivery milestones

1. Foundation: repository structure, settings, health endpoint, API error envelope, database session, CI checks.
2. Identity: organizations, users, memberships, registration, login, refresh rotation, logout, RBAC and tenant tests.
3. Core directory: students, parents, teachers, classes, relationship tables, pagination and search.
4. Attendance: sessions, records, bulk marking, history, role checks.
5. Fees and payments: monthly generation, pending views, partial payments, transaction safety, idempotency.
6. Receipts and reminders: receipt numbering/PDF adapter, share flows, notification log.
7. Dashboard: organization-configured KPIs, pending fees, today's classes, quick actions.
8. Hardening: audit log, indexes from query plans, rate limits, security tests, deployment and observability.

Homework, tests, schedules, subscriptions, offline sync, and multilingual UI follow after the core workflow is validated with 5-10 real organizations.
