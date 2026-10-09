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

## 8. Phase 3: Attendance and Requests (Complete)

### Deliverables:
- [x] **P3-01 Backend**: Unified attendance service (`GET /api/v1/attendance/unified`) that consolidates class sessions and group sessions into a single queryable source for dashboards and reports (fixes I-2).
- [x] **P3-02 Backend**: Reusable approval engine: request types (`LEAVE`, `ATTENDANCE_CORRECTION`, `WORK_FROM_HOME`, `PERMISSION`), request submissions (`POST /api/v1/requests`), list with scope (`my`, `pending`, `all`), approval decisions (`POST /requests/{id}/decide`), cancellation, comments (`POST /requests/{id}/comments`), and automatic in-app notifications to requesters upon approval/rejection.
- [x] **P3-03 Database**: Alembic migration `41bbd7ae5c1f` adding `requests` and `request_comments` tables with tenant and status indexes. Verified clean on SQLite and PostgreSQL DDL.
- [x] **P3-04 Mobile**: Requests module in `mobile/app/(app)/requests/`:
  - List screen (`/requests`) with "Pending Approval" tab for managers/owners and "My Requests" tab for employees/staff
  - Create request form (`/requests/create`) with type selection, date range pickers, and reason input
  - Request details screen (`/requests/[requestId]`) with status hero, approval/rejection actions for managers, cancel action for requesters, and live comment thread
  - Wired into `MoreScreen` under "WORKFLOWS & BUSINESS" and into Desktop Sidebar
- [x] **P3-05 Verification**: Automated pytest suite (`test_p3_attendance_requests.py`), route verification (all 49 routes verified active), and typecheck.

### Phase 3 verification

```bash
cd backend && ./.venv/bin/alembic upgrade head
# Output: Running upgrade 3b2c5d7e9f01 -> 41bbd7ae5c1f, add requests and request comments tables

cd backend && ./.venv/bin/pytest --tb=short -q
# Output: 54 passed, 3 warnings in 10.89s

cd backend && ./.venv/bin/alembic check
# Output: No new upgrade operations detected.

cd mobile && npx tsc --noEmit
# Output: Exited with code 0 (zero errors).

python3 scripts/verify_routes.py
# Output: SUCCESS: All 49 routes verified. Zero placeholders, all routes active and reached with verified inbound links.
```

### Phase 3: What you can now do in the app
1. Tap **More** tab (or Desktop Sidebar):
   - Tap **Requests** under WORKFLOWS & BUSINESS.
   - For administrators/owners: view **Pending Approval** tab to see pending requests with approval buttons, or switch to **My Requests**.
   - Tap **+** to submit a new request: choose request type (Leave, Attendance Correction, Work From Home, Permission), enter title, start/end dates, and details.
   - Tap any request to open its detail page: view status badge, approve or reject (with optional reason), or add comments to collaborate.
   - When a request is decided, an in-app notification is automatically generated for the requester.
2. In Attendance: `GET /api/v1/attendance/unified` merges group attendance records with class sessions into one unified response.

---

## 9. Phase 4: Work and Tasks (Complete)

### Deliverables:
- [x] **P4-01 Database**: Alembic migration `bd485bab4213` adding `tasks` and `task_checklists` tables with tenant, status, assignee, and group indexes.
- [x] **P4-02 Backend API**: `/api/v1/tasks` & `/api/v2/tasks`:
  - Full CRUD for tasks with priority, status, group, assignee, and due date filters
  - Checklist item creation (`POST /tasks/{id}/checklist`) and interactive toggling (`POST /tasks/{id}/checklist/{itemId}/toggle`)
  - Status updates (`PATCH /tasks/{id}`)
- [x] **P4-03 Mobile UI**: Tasks module in `mobile/app/(app)/tasks/`:
  - List screen (`/tasks`) with status filter tabs (ALL, TODO, IN_PROGRESS, DONE) and priority tags
  - Create task screen (`/tasks/create`) with priority selector chips, due date input, and validation
  - Detail screen (`/tasks/[taskId]`) with status switcher, interactive checklist completion toggles, new checklist item creation, and task deletion
  - Navigation links added to `MoreScreen` under WORKFLOWS & BUSINESS and to Desktop Sidebar
- [x] **P4-04 Verification**: Automated pytest suite (`test_p4_tasks.py`), route verification (all 52 routes verified active), and typecheck.

### Phase 4 verification

```bash
cd backend && ./.venv/bin/alembic upgrade head
# Output: Running upgrade 41bbd7ae5c1f -> bd485bab4213, add tasks and task checklists tables

cd backend && ./.venv/bin/pytest --tb=short -q
# Output: 55 passed, 3 warnings in 11.22s

cd backend && ./.venv/bin/alembic check
# Output: No new upgrade operations detected.

cd mobile && npx tsc --noEmit
# Output: Exited with code 0 (zero errors).

python3 scripts/verify_routes.py
# Output: SUCCESS: All 52 routes verified. Zero placeholders, all routes active and reached with verified inbound links.
```

### Phase 4: What you can now do in the app
1. Tap **More** tab (or Desktop Sidebar):
   - Tap **Tasks** under WORKFLOWS & BUSINESS.
   - View your tasks filtered by status (TODO, IN PROGRESS, DONE) with visual priority tags (URGENT, HIGH, MEDIUM, LOW).
   - Tap **+** to create a task: title, priority, due date, description.
   - Tap any task to see details: switch status on the fly, tap checklist items to mark them complete/incomplete, or add new checklist items inline.

---

## 10. Phase 5: Communication and Realtime (Next Up)

### Planned Deliverables:
- [ ] **P5-01 Backend**: Channels and Chat infrastructure (`chat_threads`, `chat_participants`, `chat_messages` already present in schema, verify endpoints and WebSocket support)
- [ ] **P5-02 Backend API**: `/api/v1/chat` & `/api/v2/chat`:
  - Direct 1:1 message threads and group channels
  - Send message endpoint, thread messages history with pagination
  - WebSocket `/ws/chat` for live message push
- [ ] **P5-03 Mobile UI**: Chat / Communication screens in `mobile/app/(app)/chat/`:
  - Thread list (Channels and Direct Messages)
  - Message thread view with send bar, bubble history, and real-time refresh
- [ ] **P5-04 Verification**: Automated pytest suite (`test_p5_chat.py`), route verification, and typecheck.
