# Tuiro Platform Migration Plan

## 1. Executive Summary

This document outlines the evolutionary database and architectural migration plan for consolidating Tuiro from its legacy parallel models (Class model vs Group model) into a unified, modular organization-management platform serving both Corporate and Education tenants without breaking existing mobile clients or losing existing data.

---

## 2. Table Mapping: Legacy to Target Domain Model

| Legacy Class Model Table | Legacy Group Model Table | Target Unified Model Table | Strategy & Mapping Notes |
|---|---|---|---|
| `classes` | `groups` | `groups` | Unified `groups` table with canonical `kind` (`"class"`, `"batch"`, `"team"`, `"department"`). Existing UUIDs preserved. |
| `class_students` | `group_members` | `group_members` | Unified membership with `member_type` (`"student"`, `"employee"`), `role` (`"member"`, `"lead"`), and `removed_at` (soft removal). |
| `class_teachers` | - | `group_members` | Stored as `group_members` with role `"teacher"` / `"lead"`. |
| `attendance_sessions` | `group_attendance_sessions` | `attendance_sessions` | Merged into single session table linked to `group_id`. |
| `attendance_records` | `group_attendance_records` | `attendance_records` | Merged into single record table linked to session and member. |
| `homework` | `assignments` | `tasks` / `work_items` | Unified task model with optional educational metadata (`subject`, `max_marks`, `due_date`). |
| `academic_tests` | - | `academic_assessments` | Retained as educational domain entity linked to `group_id`. |
| `test_marks` | - | `academic_marks` | Retained as educational domain entity. |
| `schedule_entries` | `group_schedules` | `schedules` | Unified timetable entry model linked to `group_id`. |
| `student_fees` | `fees` | `fees` | Unified fee structure supporting student tuition and corporate billing. |
| `payments` | `fee_payments` | `payments` | Unified payment transaction records with org-scoped transaction references and row-level locking. |
| `receipts` | - | `receipts` | Retained and linked to unified payments with per-org atomic receipt counters. |

---

## 3. Migration Phasing & Ordering

```text
Phase 0: Baseline & Safety Net (COMPLETED)
  - Full regression suite established
  - Mobile route consistency verified (37 active routes, 0 placeholders, 100% inbound links)
  - Zero Alembic drift confirmed

Phase 1: Platform Core
  - Permission catalog & configurable role matrix
  - Organization settings: type, timezone, currency, enabled modules
  - Configurable terminology engine (backend service + API + templates + frontend useTerm hook)
  - Auth completion: multi-org switching, invitations, password reset
  - Audit logging & background notification interface

Phase 2: Data & Model Unification
  - Additive Alembic migration introducing unified tables and columns
  - Data migration: backfill unified `groups` and `group_members` from `classes` and `class_students`
  - Dual-write / compatibility view layer so legacy endpoints (`/api/v1/classes`, `/api/v1/groups`) continue functioning
  - Verify tuition regression suite remains 100% green
  - Mark legacy endpoints as deprecated in OpenAPI

Phase 3 - 8: Modular Platform Capabilities
  - Phase 3: Unified Attendance & Requests engine
  - Phase 4: Work & Tasks (tasks + homework/assignments)
  - Phase 5: Communication (channels, direct chat, realtime WebSockets)
  - Phase 6: Calendar & Files (object storage abstraction)
  - Phase 7: Finance (fees, partial payments, receipts, payslips)
  - Phase 8: Reports, Global Search, Subscription Entitlements

Phase 9: Mobile Alignment
  - Update mobile application to consume unified terminology and v2 endpoints
  - Remove legacy compatibility shims

Phase 10: Hardening, Cleanup & Release
  - Retire deprecated legacy tables
  - Drop compatibility views
  - Final performance and index optimization
```

---

## 4. Safety & Rollback Rules

1. **Additive Schema Changes First**:
   - Never drop or rename an existing column or table in the first migration.
   - New columns must have sensible defaults or allow nulls during intermediate stages.
2. **Data Preservation**:
   - All data migrations run within explicit transactions where supported.
   - Historical fees, payments, attendance records, and receipts must not be modified or deleted.
3. **Rollback Strategy**:
   - Each Alembic migration script defines both `upgrade()` and `downgrade()` procedures.
   - If a rollback occurs during Phase 2, legacy `classes` and `groups` tables remain intact because they are not dropped until Phase 10.
4. **Compatibility Layer**:
   - The existing 100 API endpoints must remain operational for the mobile client until Phase 9 is completed.
   - Compatibility adapters map legacy endpoint requests to the underlying unified service methods.
