# MVP API Contract

All endpoints are under `/api/v1` and require `Authorization: Bearer <access_token>` except auth endpoints.

| Method | Path | Purpose |
|---|---|---|
| POST | `/auth/register` | Create user and initial organization context |
| POST | `/auth/login` | Issue access and refresh tokens |
| POST | `/auth/refresh` | Rotate refresh token and issue access token |
| POST | `/auth/logout` | Revoke current refresh session |
| GET | `/me` | Return current user and organization context |
| GET/POST | `/students` | List or create tenant-scoped students |
| GET/PATCH/DELETE | `/students/{id}` | Read, update, or archive a student |
| GET/POST | `/parents` | List or create parents |
| GET/POST | `/teachers` | List or create teachers |
| GET/POST | `/classes` | List or create classes |
| POST | `/attendance/sessions` | Create or replace one class/date attendance session |
| GET | `/attendance` | Query attendance history and statistics |
| GET | `/fees` | List fees with status/date/student filters |
| POST | `/fees/generate` | Idempotently generate monthly fees |
| GET | `/fees/pending` | Return actionable outstanding balances |
| POST | `/payments` | Record a validated payment transactionally |
| GET | `/payments` | List immutable payment history |
| GET | `/receipts/{id}` | Return receipt metadata |
| GET | `/receipts/{id}/pdf` | Stream an authorized receipt PDF |
| GET | `/dashboard` | Return organization-configured KPI snapshot |

## Request/response rules

Create and update requests use dedicated Pydantic schemas. Responses use public response schemas and omit password hashes, refresh token hashes, and internal provider data. Collection endpoints accept `limit` and `cursor` and return `{items, next_cursor}`.

Payment creation requires `fee_id`, positive `amount`, `payment_date`, `payment_method`, and optional `transaction_reference`. The service locks the fee, rejects cross-tenant IDs, rejects amounts above the outstanding balance, and updates status to `PARTIAL` or `PAID`. A repeated transaction reference returns a conflict without creating another payment.

Errors follow:

```json
{
  "success": false,
  "error": {
    "code": "FEE_NOT_FOUND",
    "message": "Fee not found."
  }
}
```

Authorization is enforced in dependencies plus services. A `TEACHER` can access assigned classes and attendance but cannot access fees or subscription data unless a permission explicitly grants it. A `PARENT` query is always joined through `student_parents` for the authenticated parent identity.
