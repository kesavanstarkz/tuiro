# Tuiro Platform Build Progress

## Current Status: Phase 2 in progress (P2-01 and P2-02 complete; P2-03 partial)

---

## 1. Phase 0: Baseline & Safety Net Verification

### Exit Criteria Status: ALL MET & VERIFIED
- [x] **Backend Test Suite Green**: 37 tests passing (`test_tuition_regression.py`, `test_full_suite.py`, `test_issues.py`, `test_mvp.py`).
- [x] **Tuition Regression Suite**: `backend/tests/test_tuition_regression.py` created and passing. Covers full lifecycle (classes, student enrollments, parents, attendance, homework, academic tests, schedule, fees, partial & full payments, atomic receipt counters, PDF generation, dashboard KPIs, cross-tenant 404 isolation).
- [x] **Alembic Drift Check Clean**: `alembic check` passes with 0 drift ("No new upgrade operations detected"). Tested from clean initial database state via `reset_db.py` through all revisions to head `ad8addcbf1e7`.
- [x] **Mobile TypeScript Clean**: `npx tsc --noEmit` passed with 0 errors.
- [x] **Route Verification**: `python3 scripts/verify_routes.py` passes with all 37 routes active, zero placeholders, and verified inbound navigation links.
- [x] **Documentation Created**:
  - `docs/ARCHITECTURE.md` (current & target architecture)
  - `docs/MIGRATION_PLAN.md` (target state, table mapping, phased rollout, rollback rules)
  - `docs/ROUTES.md` (catalog of all 37 mobile routes)
  - `docs/PROGRESS.md` (this file)

---

## 2. Real Commands Executed & Verified Output

```bash
# 1. Run all backend tests
cd backend && ./.venv/bin/pytest
# Output: 37 passed, 1 warning in 5.76s

# 2. Test fresh database recreation from empty
cd backend && ./.venv/bin/python scripts/reset_db.py
# Output: Recreated schema: alembic upgrade head completed.

# 3. Check for model/migration drift
cd backend && ./.venv/bin/alembic check
# Output: No new upgrade operations detected.

# 4. Mobile TypeScript check
cd mobile && npx tsc --noEmit
# Output: Exited with code 0 (zero errors).

# 5. Route integrity & inbound link check
python3 scripts/verify_routes.py
# Output: SUCCESS: All 37 routes verified. Zero placeholders, all routes active and reached with verified inbound links.
```

---

## 3. Decisions Taken

1. **Test Due Dates**: Replaced hardcoded September 2026 test due dates in `test_full_suite.py` with future dates so fees are tested in active `PENDING` status rather than auto-computed `OVERDUE` status.
2. **Dedicated Tuition Regression Test**: Created `backend/tests/test_tuition_regression.py` to lock down the exact end-to-end tuition workflow as required by Section 3.3.
3. **Enhanced Route Verification**: Added comprehensive AST/regex scanning in `scripts/verify_routes.py` that fails if any route file has zero inbound links across `mobile/`. Tested failure mode with a synthetic orphan route.
4. **Environment Note**: SQLite is used for local fast testing; PostgreSQL migrations are verified via Alembic DDL scripts. PostgreSQL/Docker was not found installed locally in the container environment.

---

## 4. Work Remaining: Phase 1 (Platform Core)

- [x] **P1-01**: Permission catalog, configurable roles, single permission matrix, and "every operation x every role" parameterized test.
- [x] **P1-02**: Organization model extensions (type, timezone, currency, enabled modules, settings).
- [x] **P1-03**: Terminology engine (backend service + API + starter templates for Corporate & Education + tests, and `useTerm` design).
- [x] **P1-04**: Auth completion (password reset, email verification, invitations flow, multi-org switching with org in token, rate limits).
- [x] **P1-05**: Audit log service & events for security and financial mutations.
- [x] **P1-06**: Notification core: user-scoped inbox, unread/read actions, preferences, idempotency keys, and a swappable thread-job runner. External email/SMS/WhatsApp delivery remains pending until a provider adapter is configured.
- [x] **P1-07**: Web app skeleton in `web/` (Next.js, auth screens, onboarding flow, permission & terminology-aware shell). Connected login, registration, settings terminology editing, and notification inbox paths use the live API; later modules remain unavailable until their backend phases.

---

## 5. P1-06 Verification

```bash
cd backend && ./.venv/bin/pytest
# Output: 48 passed, 2 warnings in 8.96s
```

## 6. P1-07 Verification

```bash
cd web && npm run typecheck
# Output: exited 0
cd web && npm run build
# Output: compiled successfully; generated 9 routes
```

## 7. Phase 2: People and Groups

- [x] **P2-01**: Added the canonical `groups` metadata and `group_memberships` history table through additive migration `2a1b4c6d8e0f`. Existing `classes` and `group_members` remain compatibility data for v1/mobile endpoints; `/api/v2/groups` is the new platform API. Existing groups/classes are retained and legacy student memberships are copied into the canonical table.
- [x] **P2-02**: Added separate corporate employee, department, and job-title entities, plus reusable per-person custom fields and document metadata. The v2 people API supports employee CRUD and archive state; students, teachers and parents remain distinct education entities.
- [x] **P2-03**: Built mobile-first People and Groups screens in `mobile/app/(app)/` connected to live `/api/v2/people` and `/api/v2/groups` endpoints:
  - People list (`/people`) with corporate employee list, search, status filter, and education navigation links
  - Employee detail (`/people/[personId]`) with profile cards, edit navigation, and archive action with confirmation
  - Employee create & edit forms (`/people/create`, `/people/[personId]/edit`) with React Hook Form + Zod validation
  - Groups list (`/groups`) with kind badges, search, and archived filters
  - Group detail (`/groups/[groupId]`) with member roster, membership roles, and archive action
  - Group create & edit forms (`/groups/create`, `/groups/[groupId]/edit`)
  - Group member assignment (`/groups/[groupId]/add-member`)
  - Added People and Groups links to `MoreScreen` and desktop sidebar
  - Added PATCH `/api/v2/groups/{id}` endpoint to backend
  - Updated `mobile/src/api/platformPeople.ts` and `mobile/src/api/v2Groups.ts`
  - Restored `mobile/src/utils/currency.ts` and `backend/tests/test_issues.py`
  - Verified route link integrity (all 46 mobile routes verified with zero placeholders and inbound links)

### Phase 2 verification

```bash
cd backend && ./.venv/bin/alembic upgrade head
# Output: Up to date, head 3b2c5d7e9f01.

cd backend && ./.venv/bin/pytest --tb=short -q
# Output: 51 passed, 2 warnings in 9.78s

cd backend && ./.venv/bin/alembic check
# Output: No new upgrade operations detected.

cd mobile && npx tsc --noEmit
# Output: Exited with code 0 (zero errors).

python3 scripts/verify_routes.py
# Output: SUCCESS: All 46 routes verified. Zero placeholders, all routes active and reached with verified inbound links.
```

### Phase 2: What you can now do in the app
1. Open the mobile app or web preview (`npm start` in `mobile/`).
2. Navigate to **More** tab (or Desktop Sidebar):
   - Tap **People** to view the employee directory or navigate to education rosters (Students, Teachers, Parents).
   - Tap **+** on People to create an employee (`EMP-001`, name, email, department, start date) with live Zod validation.
   - Tap any employee row to view details, edit fields, or archive.
   - Tap **Groups** in the More menu or Sidebar to view teams, classes, departments, and batches.
   - Tap **+** on Groups to create a team or department.
   - Tap a group to view members, add new members by UUID and role, or archive the group.

### Phase 2 decisions and limitations

1. The legacy `classes`, `class_students`, and `group_members` tables were deliberately not dropped. This is an additive, rollback-safe migration: v1 endpoints and the current mobile client continue to work while v2 reads canonical memberships.
2. Membership identity is polymorphic (`member_type`, `member_id`) so a group can contain separate domain models without a giant generic person table. Student members are also maintained in the legacy `group_members` projection until Phase 9 migration.
3. `PersonDocument` stores metadata and a storage key only. Binary upload/download waits for the object-storage service in Phase 6.

---

## 8. Phase 3: Attendance and Requests (In Progress)

### Planned Deliverables:
- [ ] **P3-01 Backend**: Unified attendance service (`GET /api/v1/attendance/unified` & `/api/v2/attendance`) that consolidates class sessions and group sessions into a single queryable source for dashboards and reports (fixes I-2).
- [ ] **P3-02 Backend**: Reusable approval engine: request types (`LEAVE`, `ATTENDANCE_CORRECTION`, `WORK_FROM_HOME`), request submissions, approval chain, comments, approvals & rejections, and notifications to requester on decision.
- [ ] **P3-03 Mobile**: Unified attendance UI in `mobile/app/(app)/(tabs)/attendance.tsx` supporting date navigation, check-in/out, and group attendance.
- [ ] **P3-04 Mobile**: Requests screens in `mobile/app/(app)/requests/` (my requests list, pending approvals, submit request form, request details with approval actions).
- [ ] **P3-05 Verification**: Automated pytest suite (`test_p3_attendance_requests.py`), route verification, and typecheck.
