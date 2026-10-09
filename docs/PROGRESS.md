# Tuiro Platform Build Progress

## Current Status: Phase 1 P1-01 through P1-06 completed; P1-07 is next

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
- [ ] **P1-07**: Web app skeleton in `web/` (Next.js, auth screens, onboarding flow, permission & terminology-aware shell).

---

## 5. P1-06 Verification

```bash
cd backend && ./.venv/bin/pytest
# Output: 48 passed, 2 warnings in 8.96s
```

## 6. Next Resume Point
Begin **P1-07**: create the `web/` Next.js application with authenticated onboarding and a terminology-, permissions-, and modules-aware app shell.
