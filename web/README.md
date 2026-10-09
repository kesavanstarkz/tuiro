# Tuiro web client

The primary Tuiro client is a Next.js App Router application. It uses the existing FastAPI API, TanStack Query for server state, React Hook Form plus Zod for validation, and a centralized terminology hook.

```bash
cp .env.example .env.local
npm install
npm run dev
```

Set `NEXT_PUBLIC_API_URL` to the running backend URL. The Phase 1 shell provides real registration, login, terminology editing, module-aware navigation, and notification inbox interactions. Domain modules remain intentionally unavailable until their corresponding backend phases are delivered.
