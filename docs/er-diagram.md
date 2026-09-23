# Initial PostgreSQL ER Model

The schema is tenant-aware. Every organization-owned table carries `organization_id`; repositories and foreign keys must prevent cross-tenant references. UUIDs are used for public identifiers. Timestamps are stored in UTC.

```mermaid
erDiagram
    ORGANIZATIONS ||--o{ ORGANIZATION_MEMBERS : has
    USERS ||--o{ ORGANIZATION_MEMBERS : joins
    ORGANIZATIONS ||--o{ STUDENTS : owns
    ORGANIZATIONS ||--o{ PARENTS : owns
    ORGANIZATIONS ||--o{ TEACHERS : owns
    ORGANIZATIONS ||--o{ CLASSES : owns
    STUDENTS ||--o{ STUDENT_PARENTS : linked
    PARENTS ||--o{ STUDENT_PARENTS : linked
    CLASSES ||--o{ CLASS_STUDENTS : enrolls
    STUDENTS ||--o{ CLASS_STUDENTS : attends
    CLASSES ||--o{ CLASS_TEACHERS : assigned
    TEACHERS ||--o{ CLASS_TEACHERS : teaches
    CLASSES ||--o{ ATTENDANCE_SESSIONS : has
    ATTENDANCE_SESSIONS ||--o{ ATTENDANCE_RECORDS : records
    STUDENTS ||--o{ ATTENDANCE_RECORDS : receives
    STUDENTS ||--o{ FEES : billed
    FEES ||--o{ PAYMENTS : paid_by
    PAYMENTS ||--o| RECEIPTS : produces
    USERS ||--o{ AUDIT_LOGS : creates
    ORGANIZATIONS ||--o{ AUDIT_LOGS : contains

    ORGANIZATIONS {
      uuid id PK
      text name
      text country_code
      text currency_code
      text timezone
      text locale
      jsonb settings
      text status
      timestamptz created_at
    }
    USERS {
      uuid id PK
      text email UK
      text password_hash
      text display_name
      text status
      timestamptz created_at
    }
    ORGANIZATION_MEMBERS {
      uuid id PK
      uuid organization_id FK
      uuid user_id FK
      text role
      jsonb permissions
      timestamptz created_at
    }
    STUDENTS {
      uuid id PK
      uuid organization_id FK
      text student_number
      text first_name
      text last_name
      text school
      text academic_level
      date date_of_birth
      text status
      date joining_date
      timestamptz created_at
    }
    PARENTS {
      uuid id PK
      uuid organization_id FK
      text first_name
      text last_name
      text relationship
      text phone
      text email
      text preferred_language
    }
    STUDENT_PARENTS {
      uuid student_id FK
      uuid parent_id FK
      boolean is_primary
      text relationship
    }
    TEACHERS {
      uuid id PK
      uuid organization_id FK
      uuid user_id FK
      text employee_number
      text status
      date joining_date
    }
    CLASSES {
      uuid id PK
      uuid organization_id FK
      text name
      text subject
      text academic_level
      integer capacity
      numeric fee_amount
      text status
    }
    CLASS_STUDENTS {
      uuid class_id FK
      uuid student_id FK
      date enrolled_on
      date ended_on
    }
    CLASS_TEACHERS {
      uuid class_id FK
      uuid teacher_id FK
      boolean is_primary
    }
    ATTENDANCE_SESSIONS {
      uuid id PK
      uuid organization_id FK
      uuid class_id FK
      date session_date
      uuid created_by FK
    }
    ATTENDANCE_RECORDS {
      uuid id PK
      uuid session_id FK
      uuid student_id FK
      text status
      text remarks
    }
    FEES {
      uuid id PK
      uuid organization_id FK
      uuid student_id FK
      text billing_period
      numeric amount
      numeric discount
      numeric fine
      numeric amount_due
      date due_date
      text status
    }
    PAYMENTS {
      uuid id PK
      uuid organization_id FK
      uuid fee_id FK
      uuid student_id FK
      numeric amount
      date payment_date
      text payment_method
      text transaction_reference
      uuid recorded_by FK
    }
    RECEIPTS {
      uuid id PK
      uuid organization_id FK
      uuid payment_id FK
      text receipt_number
      timestamptz issued_at
    }
    AUDIT_LOGS {
      uuid id PK
      uuid organization_id FK
      uuid user_id FK
      text action
      text entity_type
      uuid entity_id
      jsonb metadata
      timestamptz created_at
    }
```

## Required constraints and indexes

- `organization_members`: unique `(organization_id, user_id)`.
- `students`: unique `(organization_id, student_number)`.
- `student_parents`: primary key `(student_id, parent_id)`.
- `class_students`: primary key `(class_id, student_id)`.
- `class_teachers`: primary key `(class_id, teacher_id)`.
- `attendance_sessions`: unique `(organization_id, class_id, session_date)`.
- `attendance_records`: unique `(session_id, student_id)`.
- `fees`: unique `(organization_id, student_id, billing_period)`.
- `payments`: unique `(organization_id, transaction_reference)` when the reference is present.
- `receipts`: unique `(organization_id, receipt_number)` and unique `payment_id`.
- Check constraints enforce non-negative money, positive capacity, and valid status enums.
- Index all `organization_id` columns; add composite indexes for `(organization_id, status)`, `(organization_id, due_date)`, `(organization_id, payment_date)`, `(organization_id, session_date)`, and searchable student identifiers.

Foreign keys that connect two organization-owned records should be implemented with composite tenant-aware keys where practical, or validated in the service transaction before insertion.
