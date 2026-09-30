# Tuiro Changes & Verification Log

This document records the architectural and functional fixes and new features implemented across the Tuiro backend (FastAPI + SQLAlchemy + Alembic) and mobile application (Expo 57 / React Native / Expo Router).

---

## Phase 1: Fix Known Issues

### I-1: `POST /groups` Reuses Class ID
- **What Changed**: Unified `ClassGroup` and `Class` creation in both `app/api/groups.py` and `app/services/people.py` within single transactions so that group creation produces matching IDs. Created data migration `e1f2a3b4c5d6_repair_orphan_classes_and_groups.py` to link existing orphaned records.
- **Verification**: Pytest `test_i1_group_and_class_id_sync_and_endpoints` verifies creating groups and classes, enrolling students, creating homework, tests, and schedule entries without 404 errors.

### I-2: Dashboard & Attendance Reports Include Group Attendance
- **What Changed**: Refactored `/dashboard` and `/reports/attendance` to merge attendance records from both `AttendanceRecord` and `GroupAttendanceRecord` without double-counting when sessions overlap.
- **Verification**: Pytest `test_i2_dashboard_and_reports_include_group_attendance` asserts 100% attendance calculation when student is marked present in group attendance.

### I-3: Group Fees Create Payments, Receipts, and Dashboard Totals
- **What Changed**: Unified group fee payments into real `Payment` and `Receipt` records. Included group fees in `/dashboard` collected/pending totals, `/fees/pending`, and `/reports/fees`.
- **Verification**: Pytest `test_i3_group_fees_create_payments_and_receipts` verifies payment creation, receipt counter generation, and dashboard reflection.

### I-4: Role-Based Access Control (RBAC) Matrix
- **What Changed**: Strict RBAC enforcement across all endpoints for `SUPER_ADMIN`, `OWNER`, `ADMIN`, `TEACHER`, `PARENT`, and `STUDENT`. Multi-tenant scoping guarantees that cross-tenant access returns 404. Teachers only access assigned classes; parents only access linked students; students only access self.
- **Verification**: Pytest `test_i4_role_matrix_enforcement` tests matrix endpoints across all roles.

### I-5: Transaction Reference Unique Per Organization
- **What Changed**: Updated `payments.transaction_reference` unique constraint to compound `(organization_id, transaction_reference)` with Alembic migration `c5d6e7f8a9b0_make_payment_transaction_reference_org_scoped.py`.
- **Verification**: Pytest `test_i5_payment_reference_unique_per_org` ensures two organizations can reuse the same transaction reference, while a single organization gets a 409 conflict on duplicate reference.

### I-6: Multi-Organization Support & Switching
- **What Changed**: Added `/api/v1/auth/switch-organization` endpoint. Updated auth response to include list of user's organization memberships. Users with multiple organizations can switch context seamlessly.
- **Verification**: Pytest `test_i6_multi_org_support_and_switching` verifies multi-membership authentication and organization switching.

### I-7: Concurrency & Side Effects
- **What Changed**: Added row-level locking (`SELECT ... FOR UPDATE`, no-op on SQLite) on fee rows during payment processing to prevent double payment race conditions. Atomic sequential receipt numbering backed by `OrganizationReceiptCounter` per organization per year. GET endpoints made completely side-effect free.
- **Verification**: Pytest `test_i7_concurrency_and_safe_receipts`.

### I-8: PATCH Endpoints Accept Partial Bodies
- **What Changed**: Audited and fixed all PATCH schemas across homework, tests, classes, students, and settings to use optional default fields (`None`) and `model_dump(exclude_unset=True)` so omitted fields are never overwritten with null.
- **Verification**: Pytest `test_i8_patch_endpoints_accept_partial_bodies`.

### I-9: Filter Withdrawn Students by Default
- **What Changed**: Updated student listing queries to filter by `status == "ACTIVE"` by default, with an optional `include_inactive=true` query parameter to view withdrawn/inactive students.
- **Verification**: Pytest `test_i9_filter_withdrawn_students_by_default`.

### I-10: Require Authentication for Subscription Plans
- **What Changed**: Added `require_authenticated_user` dependency to `/subscription/plans` to prevent unauthenticated enumeration of pricing tiers and platform limits.
- **Verification**: Pytest `test_i10_subscription_plans_require_auth`.

### I-11: Model & Migration Drift
- **What Changed**: Created migration `feafcf8ce39c_align_models_and_migrations.py` resolving all schema discrepancies.
- **Verification**: Pytest `test_i11_no_migration_drift` and `alembic check` report no schema drift.

### I-12: Repo Hygiene & Secret Safeguards
- **What Changed**: Cleaned tracked secret files, updated `.gitignore`, sanitized environment examples.
- **Verification**: Pytest and repository file audit.

### I-13: Center Timezone for Dates & Attendance
- **What Changed**: Implemented `app/core/timezone.py` using Python standard library `zoneinfo.ZoneInfo`. All dates, next class schedules, and fee statuses use the organization's configured timezone rather than UTC or server local time.
- **Verification**: Pytest `test_i13_center_timezone_usage`.

### I-14: Organization Currency Setting & Formatting Helper
- **What Changed**: Stored and returned organization `currency_code` (e.g. `USD`, `INR`, `EUR`) in organization settings and dashboard. Implemented currency formatting helper in mobile application.
- **Verification**: Pytest `test_i14_organization_currency_and_format_money`.

---

## Phase 2: Route Standardization & Production Features

### R-1 & R-2: Route Collision & Sidebar Active Highlighting
- **What Changed**: Renamed `mobile/app/(app)/(tabs)/index.tsx` to `dashboard.tsx` to resolve Expo Router root route ambiguity. Fixed `isItemActive()` in `DesktopSidebar` to correctly identify active paths and sub-routes without false highlights.
- **Verification**: Verified web build and route navigation.

### R-3: Real Screens for All 37 Routes
- **What Changed**: Replaced all placeholder stubs and alias redirects across `mobile/app/(app)/` with real, production-styled responsive screens matching Tuiro design tokens. Added backend detail endpoints:
  - `GET /homework/{homework_id}`
  - `GET /tests/{test_id}`
  - `GET /students/{student_id}/tests`
  - `GET /fees/{fee_id}`
  - `GET /payments/{payment_id}`
  - `GET /fees?student_id={student_id}`
- **Verification**: Pytest `test_r3_endpoints_and_navigation`, TypeScript check (`npx tsc --noEmit`), and Expo web export.

### R-4: Route Documentation & Verification Script
- **What Changed**: Created `docs/ROUTES.md` mapping all 37 application routes. Created automated verification script `scripts/verify_routes.py` ensuring zero placeholder screens exist.
- **Verification**: Executed `python3 scripts/verify_routes.py` (37 routes verified, 0 placeholders).

### F-1: Fee Payment Screen & Online Payment Provider Interface
- **What Changed**:
  - Unified fee payment processing in `backend/app/api/workflows.py` (`process_fee_payment()`).
  - Added extensible `PaymentProvider` abstraction with `RazorpayProvider` implementation in `app/services/payment_provider.py`.
  - Added endpoints:
    - `GET /payments/config`: returns whether online payments are configured and public key ID.
    - `POST /payments/create-order`: creates order with provider and records metadata.
    - `POST /payments/verify`: verifies checkout signature and records payment idempotently.
    - `POST /payments/webhook`: handles asynchronous provider webhooks idempotently.
  - Mobile fee detail screen supports cash, UPI, bank, and online payment options.
- **Verification**: Pytest `test_f1_online_payment_flow`.

### F-2: Automatic Fee Reminders Scheduled CLI
- **What Changed**:
  - Implemented standalone, cron-safe scheduled CLI command `backend/app/commands/send_fee_reminders.py`.
  - Added `FeeReminderLog` database model to deduplicate sends so a fee is never reminded twice on the same day.
  - Added `NotificationChannel` interface supporting `InAppNotificationChannel` and `WhatsAppMockChannel`.
  - Per-organization settings support custom reminder schedules (`remind_days_before`, enabled toggle).
- **Verification**: Pytest `test_f2_fee_reminders`.

### F-3: Parent & Student Portal Tabs
- **What Changed**:
  - Updated `MobileTabBar` and `DesktopSidebar` in `mobile/app/(app)/(tabs)/_layout.tsx` to conditionally render role-appropriate navigation.
  - `PARENT` and `STUDENT` users only see their relevant tabs (Home, Attendance, Fees, Academic Homework/Tests/Schedule, Settings, Notifications) and do not see centre-wide student management, staff directories, or business financial reports.
- **Verification**: TypeScript validation (`npx tsc --noEmit`) and Expo web build export.

### F-4: Invite Flow for Staff & Parents
- **What Changed**:
  - Added `InviteCode` model in `backend/app/models.py`.
  - Added `POST /api/v1/auth/invites`: OWNER/ADMIN creates single-use expiring invite codes with assigned role and optional linked student for parents.
  - Added `GET /api/v1/auth/invites`: lists organization invites and status.
  - Added `POST /api/v1/auth/invites/accept`: invitee registers password, creates/links user, joins organization, and automatically establishes parent-student relationships if applicable.
- **Verification**: Pytest `test_f4_invite_flow`.

### F-5: Password Reset Flow
- **What Changed**:
  - Added `PasswordResetToken` model in `backend/app/models.py`.
  - Added `POST /api/v1/auth/password-reset/request`: requests single-use token; timing-safe (returns 204 regardless of whether email exists).
  - Added `POST /api/v1/auth/password-reset/complete`: verifies token, updates user password hash, invalidates token, and revokes all active refresh sessions.
- **Verification**: Pytest `test_f5_password_reset`.

### F-6: Reports Export & Marks-Based Report Cards
- **What Changed**:
  - Enhanced attendance and fee CSV exports (`GET /reports/fees/export.csv`, `GET /reports/attendance/export.csv`).
  - Added `GET /reports/audit-logs`: queries audit trails of changes made to attendance, fees, and payments.
  - Added `GET /reports/students/{student_id}/report-card`: provides comprehensive student report cards combining academic test marks, individual percentages, overall weighted score, and total attendance percentage.
- **Verification**: Pytest `test_f6_reports_export_and_report_cards`.

---

## Final Validation Summary

- **Backend Pytest**: 36 passed in ~6 seconds (`tests/test_issues.py`)
- **Alembic Database Status**: `alembic check` reports zero drift ("No new upgrade operations detected")
- **Mobile TypeScript**: `npx tsc --noEmit` reports 0 errors
- **Mobile Web Export**: `EXPO_NO_TELEMETRY=1 npx expo export --platform web` bundles and exports successfully
- **Route Integrity**: `scripts/verify_routes.py` validates all 37 screens
