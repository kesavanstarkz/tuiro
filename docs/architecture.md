# Tuiro Platform Architecture

## 1. Overview & System Context

Tuiro is transitioning from a multi-tenant tuition-centre SaaS into a unified, modular organization-management and collaboration platform (serving SMBs, corporate teams, educational institutions, training centres, and tuition academies) inspired by the breadth of platforms like Zoho People and Microsoft Teams.

```text
+-----------------------------------------------------------------------------------+
|                                  CLIENT LAYER                                     |
|  +-------------------------------------+   +------------------------------------+  |
|  | Web Application (Target / Phase 1+) |   | Mobile Application (Current MVP)   |  |
|  | Next.js App Router, TypeScript,     |   | Expo 57, React Native 0.86,        |  |
|  | Tailwind CSS, shadcn/ui, TanStack   |   | TanStack Query, Zustand,           |  |
|  | Query, Zod form validation          |   | Expo Router, SecureStore           |  |
|  +-------------------------------------+   +------------------------------------+  |
+-----------------------------------------+-----------------------------------------+
                                          | HTTPS / WebSockets
                                          v
+-----------------------------------------------------------------------------------+
|                                FASTAPI BACKEND                                    |
|  +-----------------------------------------------------------------------------+  |
|  | API Routing Layer (/api/v1, versioned endpoints, OpenAPI docs)              |  |
|  +-----------------------------------------------------------------------------+  |
|  | Authentication & Tenancy Scoping (JWT Bearer, Argon2id, Principal Context)  |  |
|  +-----------------------------------------------------------------------------+  |
|  | Configurable Terminology Engine (Canonical terms -> Org-specific labels)    |  |
|  +-----------------------------------------------------------------------------+  |
|  | RBAC Authorization Matrix (SUPER_ADMIN, OWNER, ADMIN, TEACHER, PARENT, STU)|  |
|  +-----------------------------------------------------------------------------+  |
|  | Core Workflows & Services (People, Groups, Attendance, Requests, Finance)  |  |
|  +-----------------------------------------------------------------------------+  |
|  | Provider Abstractions (Payments: Razorpay, Storage: Local/S3, Email/Notify) |  |
|  +-----------------------------------------------------------------------------+  |
|  | Async Jobs & Scheduled Commands (Fee reminders, receipts, notifications)     |  |
|  +-----------------------------------------------------------------------------+  |
+-----------------------------------------+-----------------------------------------+
                                          | SQLAlchemy 2.0 (ORM)
                                          v
+-----------------------------------------------------------------------------------+
|                                PERSISTENCE LAYER                                  |
|  - PostgreSQL (Primary production, e.g. Neon)                                     |
|  - SQLite (Local development and fast in-memory regression tests)                 |
|  - Alembic Schema Migrations (Strictly additive, verified zero drift)             |
+-----------------------------------------------------------------------------------+
```

---

## 2. Multi-Tenancy Architecture

- **Tenant Isolation**: The `organization_id` is embedded inside the cryptographically signed JWT access token.
- **Scoping Rule**: Every tenant-owned database table includes an `organization_id` foreign key. All queries are strictly scoped by `organization_id == principal.organization_id`.
- **Cross-Tenant Security**: Queries or mutations attempting to access resources belonging to a different tenant immediately return `HTTP 404 Not Found` (never `403` or revealing existence of cross-tenant entities).
- **Multi-Organization Membership**: A single user email can belong to multiple organizations. The `/api/v1/auth/switch-organization` endpoint allows switching context by issuing a new JWT scoped to the chosen organization.

---

## 3. Authentication & Authorization

### 3.1 Token Lifecycle
- **Access Tokens**: Short-lived (15 minutes) HS256 JWT tokens containing `sub` (user_id), `org` (organization_id), and `role`.
- **Refresh Tokens**: Opaque random UUID tokens, stored cryptographically hashed (SHA-256) in the database with 30-day expiration. Rotated on every use; old token is immediately invalidated.
- **Password Security**: Argon2id password hashing via `pwdlib`.
- **Password Reset**: Single-use expiring token; timing-safe response (returns 204 regardless of whether the email exists); revokes all active refresh sessions upon completion.

### 3.2 Role-Based Access Control (RBAC)
- Supported canonical roles: `SUPER_ADMIN`, `OWNER`, `ADMIN`, `TEACHER`, `PARENT`, `STUDENT`.
- Fine-grained permission matrix enforced at route dependencies:
  - `OWNER` / `ADMIN`: Organization administration, finances, rosters, configuration.
  - `TEACHER`: Scoped to assigned classes and students; academic workflows; no financial modification.
  - `PARENT`: Scoped to linked children; attendance, fees, report cards.
  - `STUDENT`: Scoped strictly to own student records and assignments.

---

## 4. Current Domain Models & The Parallel Architecture Defect

In the early tuition-specific codebase, two parallel structures developed:
1. **Class Model**:
   - `classes`, `class_students`, `class_teachers`
   - `attendance_sessions`, `attendance_records`
   - `student_fees`, `payments`, `receipts`, `organization_receipt_counters`
   - `academic_tests`, `test_marks`, `homework`, `schedule_entries`
2. **Group Model**:
   - `groups`, `group_members` (supports soft removal with `removed_at`)
   - `group_attendance_sessions`, `group_attendance_records`
   - `fees`, `fee_payments`
   - `assignments`, `group_schedules`, `chat_channels`, `chat_messages`

In Phase 0, data synchronization bridges (such as `ClassGroup` id synchronization, merged attendance reporting, and unified payments) ensure these models co-exist without breaking current users. In Phase 2, these models are consolidated into a single unified `Group` subsystem.

---

## 5. Mobile Client Architecture

- **Stack**: React Native 0.86, Expo 57, Expo Router (file-based navigation).
- **State Management**:
  - TanStack Query (v5) for server cache, pagination, and invalidation.
  - Zustand for user session, active organization, and local UI preferences.
- **Routing**: 37 verified production routes across Tabs, Auth, Directory, Academics, Finance, and Settings. Zero placeholder screens.
- **Design Tokens**: Standardized palette (`ink`, `sand`, `coral`, `coralSoft`, `surface`), typography, spacing, and responsive layout primitives (`Screen`, `PageHeader`, `Card`, `Button`, `TuiroInput`).

---

## 6. Target Web Client Architecture

- **Stack**: Next.js 14+ (App Router), React, TypeScript.
- **Styling & Components**: Tailwind CSS, shadcn/ui (Radix UI accessible primitives), Lucide React icons.
- **Forms**: React Hook Form + Zod schema validation.
- **Shell**: Modular sidebar responding to enabled organization modules and permissions; top bar with organization switcher, global search, and notifications.
