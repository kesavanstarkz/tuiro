# Tuiro mobile endpoint workflows

The mobile app has one rule: a screen calls a React Query hook, the hook calls a domain API service, and the service calls FastAPI. UI components never call `fetch` directly.

## Identity and workspace

| Mobile flow | Endpoint | Client surface |
| --- | --- | --- |
| Register, login, refresh, logout | `POST /auth/register`, `/auth/login`, `/auth/refresh`, `/auth/logout` | `store/auth.ts`, `api/client.ts` |
| Restore current workspace | `GET /me` | `store/auth.ts` |
| Centre preferences | `GET/PATCH /settings` | `settingsApi`, `useSettings`, `useUpdateSettings` |
| Plan and capacity | `GET /subscription`, `/subscription/plans` | `subscriptionApi`, `useSubscription`, `useSubscriptionPlans` |

## People and classes

| Mobile flow | Endpoint | Client surface |
| --- | --- | --- |
| Student CRUD | `GET/POST /students`, `GET/PATCH/DELETE /students/{id}` | `studentsApi`, student hooks |
| Parent CRUD and linked students | `GET/POST /parents`, `GET/PATCH/DELETE /parents/{id}`, `GET /parents/{id}/students` | `parentsApi`, parent hooks |
| Link/unlink parent | `POST/GET/DELETE /students/{id}/parents` | `parentsApi.linkStudent`, `unlinkStudent`, `studentParents` |
| Teacher CRUD | `GET/POST /teachers`, `GET/PATCH/DELETE /teachers/{id}` | `teachersApi` |
| Class CRUD | `GET/POST /classes`, `GET/PATCH/DELETE /classes/{id}` | `classesApi` |
| Roster assignment | `POST/GET/DELETE /classes/{id}/students` | `classesApi.assignStudent`, `students`, `removeStudent` |
| Teacher assignment | `POST/GET/DELETE /classes/{id}/teachers` | `classesApi.assignTeacher`, `teachers`, `removeTeacher` |

## Daily tuition operations

| Mobile flow | Endpoint | Client surface |
| --- | --- | --- |
| View/save attendance | `GET /attendance/sessions`, `GET /attendance/session`, `POST /attendance/sessions` | `attendanceApi`, attendance hooks |
| Student attendance history | `GET /attendance/student/{id}` | `attendanceApi.studentHistory` |
| Create/list fee records | `POST/GET /fees`, `POST /fees/generate`, `GET /fees/pending` | `feesApi`, fee hooks |
| Record/list payments | `POST/GET /payments` | `paymentsApi`, `useCreatePayment` |
| Receipts and sharing | `GET /receipts`, `GET /receipts/{id}`, `/pdf`, `POST /send` | `receiptsApi`, `useSendReceipt` |
| Homework CRUD | `GET/POST/PATCH/DELETE /homework` | `homeworkApi` |
| Tests, marks and results | `GET/POST/PATCH/DELETE /tests`, `GET/POST /tests/{id}/marks` | `testsApi`, `useTestMarks`, `useSaveTestMark` |
| Weekly timetable CRUD | `GET/POST/PATCH/DELETE /schedule` | `schedulesApi`, schedule hooks |
| Notifications and fee reminders | `GET/POST /notifications`, `POST /notifications/fee-reminder/{feeId}` | `notificationsApi`, `useCreateFeeReminder` |

## Reporting and dashboard

| Mobile flow | Endpoint | Client surface |
| --- | --- | --- |
| Live dashboard | `GET /dashboard` | `reportsApi.dashboard`, `useDashboard` |
| Fee and attendance reports | `GET /reports/fees`, `/reports/attendance` | `reportsApi` |
| CSV export | `GET /reports/fees/export.csv`, `/reports/attendance/export.csv` | `reportsApi.feeCsv`, `attendanceCsv` |

## Cache invalidation policy

Mutations invalidate the screens whose numbers or lists can change. For example, a payment invalidates `payments`, `fees`, `pending-fees`, `dashboard`, and `receipts`; an attendance save invalidates that class/date session and the dashboard; a class assignment invalidates its roster and dashboard.
