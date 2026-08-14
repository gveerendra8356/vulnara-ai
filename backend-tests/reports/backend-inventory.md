# Backend Stack Inventory -- vulnara-ai

Generated: 2026-08-14T10:42:28.301496+00:00

## Framework & runtime
- **Language:** Python 3.12
- **Web framework:** FastAPI (>=0.111), served by Uvicorn (>=0.30)
- **ORM:** SQLAlchemy 2.x, async engine (`sqlalchemy[asyncio]`)
- **Database:** Postgres in production (`asyncpg`), SQLite (`aiosqlite`) for local/dev/CI
- **Auth:** Custom JWT implementation (`python-jose[cryptography]`), bcrypt password hashing (`passlib[bcrypt]`)
- **Email validation:** `email-validator` via Pydantic's `EmailStr`
- **Realtime:** raw `websockets` for scan-progress streaming
- **AI integration:** Groq-hosted Gemini-compatible client for remediation generation
- **Push notifications:** `firebase-admin`
- **Scanning engine:** `nmap` invoked via `asyncio.create_subprocess_exec` (argument list, not shell)

## API surface (no version prefix)
All routes are mounted directly on the app with **no `/api/v1` prefix** --
e.g. `POST /auth/login`, not `POST /api/v1/auth/login`. See
`endpoint-inventory.xlsx` for the full list of 27 REST endpoints + 1 WebSocket.

## Roles
Three roles exist: `client`, `analyst`, `admin`. Self-registration
(`POST /auth/register`) only allows `client`/`analyst` -- the first `admin`
account must always be created out-of-band (mirrored in this suite by
`seed_test_accounts.py`, the same way the repo's own `seed_db.py` does it
for local dev).

## Test harness approach
This test suite spins up the actual `app.main:app` via a real `uvicorn`
subprocess against a throwaway SQLite database for every test run (see
`conftest.py`), rather than testing route handlers in isolation. This
exercises the full stack per request: CORS middleware, JSON body parsing,
the real JWT auth dependency, and real async DB round trips.

## Environment notes for this run
- `nmap` is not installed in this CI/sandbox environment, so any scan's
  background task fails fast (`status=FAILED`) after creation. This does
  not affect any test in this suite -- every test asserts against the
  synchronous API response, never the background scan outcome.
- No live Gemini/Groq API credentials are configured, so
  `POST /vulnerabilities/{id}/remediations` returns `502` in this
  environment once past authorization -- expected and asserted for directly
  where relevant.
