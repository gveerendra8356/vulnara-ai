# Vulnara: working process and backend logic

**Prepared from the source code in this folder, 28 October 2026.** This is a code review of the implementation, not a claim that a live target, deployed server, or external AI service was successfully exercised. Some older project documents describe intended behavior; where they differ, this report follows the current code.

## 1. What the project does

Vulnara is a vulnerability assessment workflow with three parts:

| Part | Location | Purpose |
| --- | --- | --- |
| Backend | `backend/` | Authenticates users, runs network scans, looks up candidate CVEs, asks an AI model to triage results, optionally probes web inputs, stores findings, and manages remediation review. |
| Web application | `vulnara-web/` | Dashboard for creating scans, reviewing findings and threat logs, managing remediation, and admin screens. Built with React/Vite. |
| Mobile application | `vulnara_mobile_scaffold/` | Flutter client for scans, findings, notifications, remediation decisions, and account views. |

Both clients call the same FastAPI backend. The backend persists data with async SQLAlchemy. `DATABASE_URL` selects the database: the code defaults to a local SQLite file, while the deployment configuration expects a PostgreSQL URL (for example, Neon). WebSocket messages provide live scan events. Firebase Cloud Messaging can deliver critical alerts to registered mobile devices if configured.

## 2. End-to-end process

```text
User signs in
  -> POST /auth/login -> access and refresh JWTs
User enters target, authorization justification, and optional active testing choice
  -> POST /scans -> PENDING scan row + background task
Background task
  -> IN_PROGRESS -> host discovery -> open ports -> service/version/banner detection
  -> normalized host/port data -> NVD keyword CVE candidates
  -> Groq AI triage -> stored vulnerabilities + live events/alerts
  -> COMPLETED scan
If active testing was enabled and web inputs are discovered
  -> controlled SQLi/XSS/command injection probes -> threat logs + live events
User requests a fix for a vulnerability
  -> Groq AI generates a proposed script -> PENDING remediation
Analyst/admin approves or rejects; an approved script may be manually applied
  -> user marks it EXECUTED (the backend records this state)
```

### Authentication and roles

Registration accepts email, full name, password of at least eight characters, and a `client` or `analyst` role. Login checks a bcrypt password hash and issues HS256 JWTs: an access token valid for 60 minutes and a refresh token valid for seven days. Protected REST routes read the bearer access token and load the current user from the database. Refresh creates another access token; logout adds a hash of the refresh token to a denylist. The web client stores tokens in browser `localStorage`; the Flutter client uses secure storage and automatically refreshes an expired access token once after a 401 response.

Clients generally see their own scan data. Analysts and admins can list and inspect scans across users. Admins manage users and admin screens. Analysts and admins can change vulnerability status and approve/reject remediations. A client can mark an approved remediation executed for its own scan. These are route rules, so the UI alone is not the access control boundary.

### Starting a scan: required input

The central input is `POST /scans` with a bearer access token and JSON such as:

```json
{
  "target": "staging.example.com",
  "authorization_confirmed": true,
  "authorization_justification": "Written permission from the system owner for this staging host.",
  "active_testing_enabled": false
}
```

`target` is one domain or IP string, 1–255 characters. The API trims whitespace but does not parse it as a URL; use a host or IP, not a full `https://` URL. `authorization_confirmed` must be true, and the justification must contain 10–2000 nonblank characters. It is stored and audit logged. The code checks the user's attestation; it does not independently verify ownership or the written permission. `active_testing_enabled` defaults to false in the API, web form, and mobile form.

An accepted request returns HTTP 201 with `scan_id`, `target`, `status: "PENDING"`, `active_testing_enabled`, and `created_at`. A failed validation or missing confirmation returns 422. The user can then call `GET /scans/{scan_id}` or subscribe to `/ws/scans/{scan_id}?token=<access_token>`.

### Reconnaissance and normalization

The route writes the scan, then starts `run_scan_task` using `asyncio.create_task`. It changes status to `IN_PROGRESS` and broadcasts that state. If Nmap is installed, discovery uses `-sn -Pn -T4`, followed by version detection (`-sV`), the banner script, and the top 1,000 ports. Nmap XML is parsed into host, port, protocol, service, version, and banner records. If Nmap is unavailable, a Python fallback tries a small list of common TCP ports, checks DNS/liveness, and grabs HTTP or TCP banners. This fallback has narrower coverage and weaker service identification. The normalizer converts either result into one consistent structure for triage.

### CVE lookup and AI triage

For each detected service/port, the backend queries NIST's NVD CVE API using a keyword made from the service name and optional version. It takes up to eight candidates per service. This is broad **keyword matching**, not exact CPE/version matching; candidates can be irrelevant or missed. The NVD client has a process-wide sliding-window limiter (5 requests per 30 seconds without an API key, 50 with one) and retries a 429 once. It extracts descriptions and CVSS scores, preferring CVSS v3.1, then v3.0, then v2.

The backend sends all ports and candidate CVEs for one host to **Groq** (`GROQ_MODEL`, default `openai/gpt-oss-120b`). The model is instructed to decide whether each CVE fits the observed service/version, label false positives, assign severity and confidence, and explain its reasoning. The response must be JSON matching Pydantic schemas; invalid responses trigger correction attempts, and transient Groq errors use exponential backoff. Findings marked `is_false_positive` are skipped. Remaining findings and referenced CVE definitions are stored. A `vulnerability.discovered` event is broadcast per saved finding. HIGH and CRITICAL findings can trigger email; CRITICAL findings also trigger a WebSocket alert and, if configured, an FCM push to the scan owner's registered devices.

**Important accuracy caveat:** a Groq triage failure now fails the scan with a visible `failure_reason`; the backend does not create a mock vulnerability. If the failure happens after earlier hosts were assessed, the scan can contain partial findings. Confidence, CVSS, and severity on AI findings are model outputs and should be reviewed by a human.

The scan is marked `COMPLETED` only after triage and any opted-in active testing finish. The backend emits `scan.status_changed` with the `active_testing` stage while those probes run, then emits `scan.completed` with counts by severity. Cancellation marks the scan `CANCELLED` and cancels its asyncio task; an in-flight Nmap child process is terminated as part of cancellation.

### Optional active web testing

Active testing runs only when the saved scan row has `active_testing_enabled=true` and recon found HTTP-looking services. The task derives HTTP/HTTPS base URLs from service names and ports. The discovery step fetches each base page and extracts HTML form fields and query parameters. It is a one-page discovery pass, not a full web crawler. If there are no discovered inputs, there are no active-test attempts or threat logs.

For each discovered parameter, the engine sends a benign baseline and a small catalog of SQL injection, cross-site scripting, and command injection probes. A fresh random marker helps distinguish a probe's response from static page text. Tests are throttled to about one request per second with jitter, with a default cap of 150 active-test requests per scan (`ACTIVE_TEST_MAX_REQUESTS_PER_SCAN`). Failed and negative attempts are logged as well as positive ones.

| Technique | How the code judges a signal | Main limit |
| --- | --- | --- |
| SQLi, error based | New database error text appears after a quote probe but not in baseline. | Generic error pages hide the signal. |
| SQLi, boolean based | True-condition response resembles baseline more than false-condition response (similarity gap > 0.10). | Dynamic page content can create a misleading difference. |
| SQLi, time based | Payload delay exceeds baseline mean plus three standard deviations and fits the expected two-second delay. | SQL sleep payload is MySQL specific; network jitter can mislead. |
| XSS reflection | Checks for the full unescaped payload in returned text. Optional Playwright code can look for a real title change if installed. | Reflection alone is not browser execution; Playwright is not a default dependency. |
| Command injection | Looks for an output marker or a time delay. | A page that simply echoes the submitted input can imitate command output. |

Only heuristic-positive attempts call Groq for a second, contextual verdict. If that call fails, `ai_verified` is false. Each `threat_logs` row records attack type, URL, parameter, payload, verdict, notes, risk rating, and timestamp. These rows can have `vuln_id=null`: active-test evidence is **not automatically converted into a vulnerability row**. The finding detail page shows the observed service/version/banner, matched CVE source, AI rationale and confidence, and related active-test verification status. Host/port-associated attempts are evidence to review, not proof that a particular CVE is exploitable.

### Remediation workflow

For a saved finding, `POST /vulnerabilities/{vuln_id}/remediations` accepts an optional `target_os` (for example, `ubuntu-22.04`; omit for a generic Linux assumption). The backend sends the finding's host, port, service/version, CVE, severity, score, reasoning, and OS hint to Groq. The response contains an executive summary, a technical script, and an AI confidence value. It is saved as `PENDING` and returned with its ID. If the AI generation fails, the route returns 502.

Analysts/admins use `POST /remediations/{id}/approve` or `/reject` (reject requires a `reason` field). Only analysts/admins can mark an approved remediation as executed. Approval and rejection only accept a `PENDING` remediation. **The backend never runs the generated script**: marking executed only updates database status and timestamp, after someone has applied it outside the platform. The rejection reason is accepted by the API but currently not stored. The generated script should be checked against the real system before use.

## 3. Outputs the user can inspect

| Operation | Output |
| --- | --- |
| Login | Access token, refresh token, expiry duration, user profile/role. |
| Create scan | Scan ID and initial `PENDING` state. |
| Scan status | Target, owner ID, status (`PENDING`, `IN_PROGRESS`, `COMPLETED`, `FAILED`, `CANCELLED`), failure reason when present, timestamps, active-test flag, authorization justification, and counts by severity. |
| Scan vulnerabilities | Finding IDs, host/port/service/version/banner, CVE and CVSS if present, severity, AI confidence/reasoning, status, discovery time. |
| Active threat logs | Each tested URL/parameter, attack type, exact payload, AI verdict and explanation, risk rating, time. |
| Remediation | Executive summary, proposed technical script, AI confidence, status (`PENDING`, `APPROVED`, `REJECTED`, `EXECUTED`), reviewer and timestamps. |
| Live WebSocket | `scan.status_changed`, `recon.progress`, `vulnerability.discovered`, `alert.critical`, `scan.completed`, `active_test.attempt`, or `scan.failed`. |

The dashboard aggregates scan and finding data; a result with zero findings can mean no applicable issues were found **or** no open ports, no useful banners, missing NVD candidates, or an incomplete triage path. It is not proof that a target is secure.

## 4. How the web and mobile applications participate

The React web app uses Axios for HTTP, React Query for caching/refetching, React Router for pages, and WebSockets for scan events. It offers login/registration, scan creation and lists, finding details, threat logs, remediation queue/review, profile, and admin pages. It defaults to the real API; set `VITE_USE_MOCK=true` to opt into mock data. `VITE_API_BASE_URL` and `VITE_WS_BASE_URL` must point to the actual backend. The web router is configured with `/vulnara-ai/` as its base path.

The Flutter app uses Dio repositories for REST calls, Riverpod providers for state, GoRouter for navigation, WebSockets for live scan updates, and secure storage for tokens. Firebase Messaging and local notifications handle critical alerts when Firebase and device registration are configured. Its current API constants point to `10.0.2.2:8000`, which works for an Android emulator talking to a backend running on the development computer. A physical phone or deployed backend needs a reachable URL and matching WebSocket scheme.

## 5. API input/output quick reference

All private REST calls require `Authorization: Bearer <access_token>`. FastAPI exposes its generated API explorer at `/docs` when the server runs.

| Endpoint | Input | Main output |
| --- | --- | --- |
| `POST /auth/register` | Email, password, full name, client/analyst role | Created user. |
| `POST /auth/login` | Email, password | Tokens and user. |
| `POST /auth/refresh` | Refresh token | New access token. |
| `POST /scans` | Target, authorization confirmation and justification, active-test flag | New scan ID, `PENDING`. |
| `GET /scans`, `GET /scans/{id}` | Optional ID | Scan list or status/counts. |
| `POST /scans/{id}/cancel` | Scan ID | Updated scan row. |
| `GET /scans/{id}/vulnerabilities` | Scan ID; optional severity filter | Finding list. |
| `GET /vulnerabilities/{id}` | Finding ID | Finding detail. |
| `PATCH /vulnerabilities/{id}` | Status text; analyst/admin | Updated finding. |
| `GET /scans/{id}/threat-logs` | Scan ID | Active probe evidence. |
| `POST /vulnerabilities/{id}/remediations` | Optional target OS | Proposed summary/script. |
| `GET /remediations`, `GET /remediations/{id}` | Optional status or ID | Remediation queue/detail. |
| `POST /remediations/{id}/approve` or `/reject` | ID; rejection reason for reject | Reviewed status. |
| `POST /remediations/{id}/mark-executed` | Approved remediation ID | Recorded `EXECUTED` state. |
| `POST /devices/register` | Mobile FCM token/platform | Registered device. |
| `GET /admin/users`, `/admin/config`, `/admin/cve-definitions` | Admin token | Users, config display, cached CVEs. |

The current list endpoints generally return plain arrays, not the paginated `{items, total}` form described in some older API documents. The web adapter wraps arrays as `{items: ...}` for its UI.

## 6. Configuration and running locally

1. Install Python dependencies from `backend/requirements.txt`, set the needed environment variables, and run `uvicorn app.main:app --reload` from `backend/` (default port 8000). Set `DATABASE_URL` to a prepared PostgreSQL database for the intended backend setup. The code's SQLite default does not establish that every PostgreSQL-specific operation, especially CVE upsert, will work in SQLite.
2. Install web packages with `npm install` in `vulnara-web/`; set `VITE_USE_MOCK=false`, `VITE_API_BASE_URL=http://127.0.0.1:8000`, and `VITE_WS_BASE_URL=ws://127.0.0.1:8000`; start with `npm run dev`. Set backend `CORS_ORIGINS` to the web origin.
3. Install Flutter dependencies with `flutter pub get` in `vulnara_mobile_scaffold/`; set the API/WS constants to the address reachable by the emulator or phone; run `flutter run`.

Key backend settings are `DATABASE_URL`, `VULNARA_SECRET_KEY`, `GROQ_API_KEY`, optional `GROQ_MODEL`, optional `NVD_API_KEY`, `CORS_ORIGINS`, `ACTIVE_TEST_MAX_REQUESTS_PER_SCAN`, Firebase credentials for push, and email settings for alerts. Nmap must be installed and on `PATH` for full Nmap scanning. NVD and Groq require outbound network access. A real scan requires a reachable authorized target; examples such as `example.com` are illustrations, not promised findings.

## 7. Current implementation limits and report interpretation

- The older architecture/API documents sometimes say **Gemini**, but the current AI client calls **Groq**. The old module/class names remain.
- AI triage failures no longer create synthetic findings; failed scans expose a user-facing failure reason. Partial findings may remain if failure occurs after some hosts have completed triage.
- Cancellation stops the in-memory asyncio task and terminates an active Nmap subprocess. Scan tasks and WebSocket subscriptions still live in one process, so a restart can lose in-progress work and live subscribers; multiple workers do not share these events.
- Scan tasks and WebSocket subscriptions live in one server process. A restart can lose in-progress work and live subscribers; multiple workers do not share these events.
- NVD uses keyword search, and the AI judges candidate applicability. Neither CVE matches nor AI explanations are independently verified by the code against a product's actual installed version.
- Admin configuration edits are persisted. Manual NVD synchronization is not implemented; the admin UI labels it unavailable and the endpoint returns 501.
- Finding details and remediation creation check scan ownership for client accounts; remediation detail/list routes are also tenant-scoped for clients.
- The scan target is only length/blank checked; the backend does not restrict it to an approved hostname or IP range. Authorization is an attestation logged by the user.
- The default local database setting is SQLite, while triage uses PostgreSQL-specific `INSERT ... ON CONFLICT` logic. Production configuration should use the prepared PostgreSQL schema/migrations.
- The `/health` route reports `status: "ok"` even if its separate `db` field says `"unreachable"`; check both fields.

## 8. Source map

This report was grounded primarily in `backend/app/main.py`, `backend/app/api/routes/`, `backend/app/scanner/`, `backend/app/triage/`, `backend/app/active_testing/`, `backend/app/remediation/`, `backend/app/models/`, `vulnara-web/src/lib/`, `vulnara-web/src/pages/`, and `vulnara_mobile_scaffold/lib/`. Existing `docs/` files provide design background but may describe future or earlier behavior.
