# Tuiro Mobile App Route Table

This document lists every active route in the Tuiro mobile application (`mobile/app`), its corresponding source file, where it is reached from within the UI, and its current status.

## Routing Architecture Highlights

1. **Root URL Resolution (`/`)**:
   - `mobile/app/index.tsx` serves as the sole handler for `/` and cleanly redirects signed-in users to `/dashboard` and unauthenticated users to `/auth/login`.
   - The primary dashboard tab was renamed from `mobile/app/(app)/(tabs)/index.tsx` to `mobile/app/(app)/(tabs)/dashboard.tsx` to prevent Expo Router root route collisions.
2. **Tab & Desktop Sidebar Navigation**:
   - Both mobile bottom navigation and desktop sidebar correctly highlight active routes, including nested detail views (e.g. `/fees/[feeId]` highlights the Fees navigation tab).
3. **Zero Dead Placeholders**:
   - All legacy alias files (`attendance/register.tsx`, `fees/pending.tsx`, etc.) and placeholder stubs have been eliminated.
   - 100% of route files render fully implemented production screens backed by live API endpoints.

---

## Route Table

| Route | Relative Screen File | Reached From | Status |
| :--- | :--- | :--- | :--- |
| `/` | `mobile/app/index.tsx` | App launch / root URL | Active (Redirects to `/dashboard` or `/auth/login`) |
| `/auth/login` | `mobile/app/auth/login.tsx` | Root redirect, register link, logout | Active |
| `/auth/register` | `mobile/app/auth/register.tsx` | Login screen "Create an account" link | Active |
| `/dashboard` | `mobile/app/(app)/(tabs)/dashboard.tsx` | Bottom Tab 1, Desktop Sidebar, root redirect | Active |
| `/students` | `mobile/app/(app)/(tabs)/students.tsx` | Bottom Tab 2, Desktop Sidebar | Active |
| `/attendance` | `mobile/app/(app)/(tabs)/attendance.tsx` | Bottom Tab 3, Desktop Sidebar, Dashboard quick action | Active |
| `/fees` | `mobile/app/(app)/(tabs)/fees.tsx` | Bottom Tab 4, Desktop Sidebar, Dashboard fee follow-up | Active |
| `/more` | `mobile/app/(app)/(tabs)/more.tsx` | Bottom Tab 5, Desktop Sidebar | Active |
| `/classes` | `mobile/app/(app)/classes/index.tsx` | More menu, Desktop Sidebar, Dashboard quick action | Active |
| `/classes/[classId]` | `mobile/app/(app)/classes/[classId]/index.tsx` | Classes list rows | Active |
| `/fees/collect` | `mobile/app/(app)/fees/collect.tsx` | Fees tab "+ Create fee", Dashboard quick action | Active |
| `/fees/[feeId]` | `mobile/app/(app)/fees/[feeId].tsx` | Fees tab rows, Dashboard fee rows, Student fees rows | Active |
| `/homework` | `mobile/app/(app)/homework/index.tsx` | More menu, Desktop Sidebar, Dashboard quick action | Active |
| `/homework/[homeworkId]` | `mobile/app/(app)/homework/[homeworkId].tsx` | Homework list cards | Active |
| `/tests` | `mobile/app/(app)/tests/index.tsx` | More menu, Desktop Sidebar, Student tests empty state | Active |
| `/tests/[testId]` | `mobile/app/(app)/tests/[testId].tsx` | Tests list rows, Student tests result cards | Active |
| `/tests/[testId]/marks` | `mobile/app/(app)/tests/[testId]/marks.tsx` | Test detail "Enter / Edit Marks" button | Active |
| `/teachers` | `mobile/app/(app)/teachers/index.tsx` | More menu, Desktop Sidebar | Active |
| `/teachers/[teacherId]` | `mobile/app/(app)/teachers/[teacherId].tsx` | Teachers list rows | Active |
| `/parents` | `mobile/app/(app)/parents/index.tsx` | More menu, Desktop Sidebar, Student parent empty state | Active |
| `/parents/[parentId]` | `mobile/app/(app)/parents/[parentId].tsx` | Parents list rows, Student parent profile button | Active |
| `/payments` | `mobile/app/(app)/payments/index.tsx` | More menu, Desktop Sidebar, Fees tab "Payment records" | Active |
| `/payments/[paymentId]` | `mobile/app/(app)/payments/[paymentId].tsx` | Payments list rows | Active |
| `/receipts` | `mobile/app/(app)/receipts/index.tsx` | More menu, Desktop Sidebar | Active |
| `/receipts/[receiptId]` | `mobile/app/(app)/receipts/[receiptId].tsx` | Receipts list rows, Fee detail receipt button | Active |
| `/schedule` | `mobile/app/(app)/schedule/index.tsx` | More menu, Desktop Sidebar, Dashboard quick action | Active |
| `/reports` | `mobile/app/(app)/reports/index.tsx` | More menu, Desktop Sidebar | Active |
| `/notifications` | `mobile/app/(app)/notifications/index.tsx` | More menu, Desktop Sidebar | Active |
| `/settings` | `mobile/app/(app)/settings/index.tsx` | More menu, Desktop Sidebar | Active |
| `/subscription` | `mobile/app/(app)/subscription/index.tsx` | More menu, Desktop Sidebar | Active |
| `/help` | `mobile/app/(app)/help/index.tsx` | More menu, Desktop Sidebar | Active |
| `/students/[studentId]` | `mobile/app/(app)/students/[studentId]/index.tsx` | Students list rows, Class roster rows | Active |
| `/students/[studentId]/attendance` | `mobile/app/(app)/students/[studentId]/attendance.tsx` | Student Hub "Attendance" card | Active |
| `/students/[studentId]/fees` | `mobile/app/(app)/students/[studentId]/fees.tsx` | Student Hub "Fees" card | Active |
| `/students/[studentId]/homework` | `mobile/app/(app)/students/[studentId]/homework.tsx` | Student Hub "Homework" card | Active |
| `/students/[studentId]/parent` | `mobile/app/(app)/students/[studentId]/parent.tsx` | Student Hub "Parent" card | Active |
| `/students/[studentId]/tests` | `mobile/app/(app)/students/[studentId]/tests.tsx` | Student Hub "Tests" card | Active |
| `/people` | `mobile/app/(app)/people/index.tsx` | More menu, Desktop Sidebar | Active |
| `/people/create` | `mobile/app/(app)/people/create.tsx` | People screen "+ Add employee", EmptyState action | Active |
| `/people/[personId]` | `mobile/app/(app)/people/[personId]/index.tsx` | People list rows, Create redirect | Active |
| `/people/[personId]/edit` | `mobile/app/(app)/people/[personId]/edit.tsx` | Person detail edit button | Active |
| `/groups` | `mobile/app/(app)/groups/index.tsx` | More menu, Desktop Sidebar | Active |
| `/groups/create` | `mobile/app/(app)/groups/create.tsx` | Groups screen "+ Create group", EmptyState action | Active |
| `/groups/[groupId]` | `mobile/app/(app)/groups/[groupId]/index.tsx` | Groups list rows, Create redirect | Active |
| `/groups/[groupId]/edit` | `mobile/app/(app)/groups/[groupId]/edit.tsx` | Group detail edit button | Active |
| `/groups/[groupId]/add-member` | `mobile/app/(app)/groups/[groupId]/add-member.tsx` | Group detail 'Add' member action | Active |
| `/requests` | `mobile/app/(app)/requests/index.tsx` | More menu, Desktop Sidebar | Active |
| `/requests/create` | `mobile/app/(app)/requests/create.tsx` | Requests screen "+ New request", EmptyState action | Active |
| `/requests/[requestId]` | `mobile/app/(app)/requests/[requestId]/index.tsx` | Requests list rows, Create redirect | Active |
| `/tasks` | `mobile/app/(app)/tasks/index.tsx` | More menu, Desktop Sidebar | Active |
| `/tasks/create` | `mobile/app/(app)/tasks/create.tsx` | Tasks screen "+ New task", EmptyState action | Active |
| `/tasks/[taskId]` | `mobile/app/(app)/tasks/[taskId]/index.tsx` | Tasks list rows, Create redirect | Active |

---

## Verification

The route mapping is programmatically verified by `scripts/verify_routes.py`:
```bash
python3 scripts/verify_routes.py
```
This script ensures:
- Every route file in `mobile/app` exists on disk and is cataloged in the route table.
- Zero placeholder screens (`ContextScreen`) remain.
- All dynamic routes match expected parameters.
