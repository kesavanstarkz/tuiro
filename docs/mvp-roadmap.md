# MVP Roadmap

## Milestone 1: Foundation

Repository structure, environment settings, FastAPI health endpoint, Expo Router shell, API error contract, formatting/lint/typecheck commands, and CI.

**Exit check:** backend imports; mobile typechecks; no production secrets are committed.

## Milestone 2: Identity and tenant security

Organizations, users, membership roles, password hashing, JWT access tokens, refresh rotation, logout, and tenant-isolation tests.

**Exit check:** Organization A cannot read or mutate Organization B; unauthorized requests return 401/403.

## Milestone 3: Directory

Students, parents, teachers, classes, relationship tables, searchable/paginated lists, forms with Zod/RHF, and empty/error states.

**Exit check:** owner can create a student, connect a parent, assign a class, and view the profile.

## Milestone 4: Attendance

Class/date session creation, bulk present/absent actions, late/excused statuses, history, and teacher authorization.

**Exit check:** duplicate class/date records are prevented and teacher scope is enforced.

## Milestone 5: Fees and payments

Monthly fee generation, pending fees, partial payments, transaction references, balance/status calculation, and audit events.

**Exit check:** running generation twice is idempotent; payment plus balance update is atomic.

## Milestone 6: Receipts and reminders

Per-organization receipt numbers, PDF adapter, receipt share flow, reminder message templates, and delivery log abstraction.

**Exit check:** payment -> receipt -> share is usable in a few interactions without exposing financial data across tenants.

## Milestone 7: Dashboard and pilot

Dashboard KPIs, pending fee actions, today's classes, configurable currency/locale display, analytics events, and pilot feedback with 5-10 organizations.

**Exit check:** core workflow is usable end-to-end on Android and pilot users can complete it without support.

Later features such as homework, tests, schedules, subscriptions, offline sync, official WhatsApp API, and multilingual UI remain behind this validated core.
