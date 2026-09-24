# Tuiro

Manage Your Classes. Simply.

Tuiro is a mobile-first, multi-tenant management platform for tuition centres, tutoring businesses, and learning providers.

## Repository

- `mobile/`: Expo Router React Native app
- `backend/`: FastAPI service and domain logic
- `docs/`: architecture, database, and delivery contracts

The mobile app communicates with the backend over HTTPS. It never connects directly to PostgreSQL or Neon.

## Current implementation

The repository now includes the Phase 2-7 MVP vertical slice: JWT authentication with refresh rotation, tenant-scoped people and class APIs, Alembic-managed PostgreSQL-compatible models, attendance sessions, idempotent fee generation, transactional partial/full payments with receipts, reminders, homework, tests/marks, schedules, reports, settings, class assignments, a configurable subscription model, and a real Expo client for auth, dashboard, students, and pending fees.

The backend currently defaults to SQLite for local smoke tests. Set `DATABASE_URL` to a PostgreSQL/Neon URL for deployed environments. The mobile client communicates only with FastAPI.

## Local setup

### Backend

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
alembic upgrade head
python scripts/seed.py # optional: development data
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000 # or: python run.py
```

The development API is available at `http://127.0.0.1:8000`; OpenAPI is at `/docs`.
The optional seed account is `owner@tuiro.example.com` / `tuiro-development`.

### Mobile

```bash
cd mobile
npm install
npx expo start
```

Set `EXPO_PUBLIC_API_URL` in `mobile/.env` for a device or simulator.

For this Expo 57 workspace, use Node 24+ and run `npm install`, `npm run typecheck`, and `npx expo-doctor` from `mobile/`. Start with `npx expo start -c`.

## Configuration

Copy `backend/.env.example` to `backend/.env`. SQLite is the supported local-development default; reserve Neon/PostgreSQL configuration for deployment.

See [docs/architecture.md](docs/architecture.md) for the system contract and [docs/er-diagram.md](docs/er-diagram.md) for the initial relational model.
See [docs/mobile-endpoint-workflows.md](docs/mobile-endpoint-workflows.md) for the mobile endpoint-to-workflow map and query-cache policy.

## Environment variables

Backend: `DATABASE_URL`, `JWT_SECRET`, `JWT_REFRESH_SECRET`, `ENVIRONMENT`, and `CORS_ORIGINS`.

Mobile: `EXPO_PUBLIC_API_URL`. This value is public application configuration; never put database credentials, JWT secrets, provider tokens, or payment secrets in `EXPO_PUBLIC_*` variables.

## Validation

```bash
cd backend
.venv/bin/pytest -q
.venv/bin/python -m compileall -q app
.venv/bin/alembic current

cd ../mobile
npm run typecheck
npx expo-doctor
```
# tuiro
