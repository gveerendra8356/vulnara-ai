# Vulnara — Web App (Task 7)

React + Vite dashboard for Vulnara: the full threat matrix, scan history/trends,
remediation review, and admin config/CVE management, consuming the same
FastAPI REST + WebSocket API the Flutter app uses.

## 1. Why this exists / what it's for

Vulnara's mobile app is deliberately thin — trigger a scan, watch it live,
get pushed critical alerts, do a quick approve/reject. Everything that
needs screen space and deep review — filtering hundreds of findings,
comparing scans over time, reading a full AI-generated remediation script
before approving it, tuning AI thresholds — lives here instead. This is
the app your reviewer (or a client's security team) would actually sit in
front of for 20 minutes, not the one they glance at on a phone.

## 2. IMPORTANT — read before you run it: backend status vs. this app

I checked your uploaded `vulnara.zip` backend before building this. As of
the end of Task 5, your FastAPI backend implements:

- `POST /scans`, `GET /scans/{id}`, `WSS /ws/scans/{id}` (Task 3)
- `POST /vulnerabilities/{id}/remediations` (Task 4)
- `POST /devices/register` (Task 6, mobile push)

It does **not** yet implement, per `app/core/auth.py`'s own docstring and
what's missing from `app/api/routes/`:

- Real auth (`/auth/login`, `/auth/register`, `/auth/me`, `/auth/refresh`,
  `/auth/logout`) — `get_current_user` is currently a stub that accepts
  any bearer token and fabricates a random user
- `GET /scans` (list/history), `POST /scans/{id}/cancel`
- `GET /scans/{id}/vulnerabilities`, `GET /vulnerabilities/{id}`,
  `PATCH /vulnerabilities/{id}`
- `GET /scans/{id}/threat-logs`, `GET /threat-logs/{id}`
- `GET/POST /remediations/{id}/approve|reject|mark-executed`,
  `GET /scans/{id}/remediations`
- `GET/PATCH /admin/config`, `GET /admin/cve-definitions*`
- The WebSocket handler exists but only ever accepts the connection —
  `run_scan_task`/the triage pipeline don't yet push `recon.progress`,
  `vulnerability.discovered`, `alert.critical`, etc. over it

**So this web app ships with a "Mock Mode"** (`VITE_USE_MOCK=true` in
`.env`, on by default) that runs entirely against realistic in-memory
data with a simulated live scan (status transitions, findings streaming
in, a critical alert, an active-test log entry) so every screen — login,
dashboard, threat matrix, live event stream, remediation review, admin —
is fully clickable **today**, in parallel with you building the rest of
the backend and the Flutter app.

Every function in `src/lib/mockApi.js` matches the same signature as
`src/lib/realApi.js`, and both match the Task 2 API contract exactly. When
your backend catches up (auth + the remaining routes above), flip one
line in `.env`:

```
VITE_USE_MOCK=false
```

...and the entire app switches to hitting your real FastAPI backend. No
page or component needs to change — they only ever import from
`src/lib/api.js`, which picks the transport.

## 3. How to run it

**Prerequisites:** Node.js 18+ and npm.

```bash
cd vulnara-web
npm install
cp .env.example .env
npm run dev
```

Open the URL Vite prints (usually `http://localhost:5173`). You're in
Mock Mode by default — sign in with **any** email/password (try
`analyst@vulnara.dev` for a normal user or `admin@vulnara.dev` to also
see the Admin nav section — the mock backend keys the role off the email
you type).

**To point it at your real backend later:**

1. Finish real JWT auth + the remaining routes in the backend (see §2).
2. In `.env`, set:
   ```
   VITE_API_BASE_URL=http://<your-oracle-vm-ip-or-domain>:8000
   VITE_WS_BASE_URL=ws://<your-oracle-vm-ip-or-domain>:8000
   VITE_USE_MOCK=false
   ```
3. `npm run dev` again (or `npm run build && npm run preview` to test the
   production build locally).

**Production build / deploy to Vercel:**

```bash
npm run build       # outputs to dist/
npm run preview     # sanity-check the production build locally
```

On Vercel: import the `vulnara-web` folder as the project root, framework
preset "Vite", and set `VITE_API_BASE_URL`, `VITE_WS_BASE_URL`,
`VITE_USE_MOCK=false` as Environment Variables in the Vercel dashboard
(this is exactly the step your Task 8 deployment prompt covers).

## 4. Project structure

```
vulnara-web/
  src/
    lib/
      api.js          # the ONLY module pages import — picks mock or real
      mockApi.js       # in-memory implementation of the full contract
      mockData.js      # seed data (scans, findings, CVEs, remediations...)
      realApi.js        # axios/WebSocket implementation against FastAPI
      httpClient.js     # axios instance, JWT header injection, error shape
    context/
      AuthContext.jsx   # current user, login/register/logout
    hooks/
      useScanSocket.js  # subscribes to /ws/scans/{id}, returns event log
    components/
      AppLayout.jsx      # sidebar + topbar shell
      ProtectedRoute.jsx # redirects to /login if signed out
      VulnTable.jsx       # TanStack Table threat matrix (filter/sort)
      ConfirmDialog.jsx   # modal used for reject / mark-executed
      Primitives.jsx       # SeverityBadge, StatusPill, ConfidenceBar, etc.
    pages/
      LoginPage.jsx / RegisterPage.jsx
      DashboardPage.jsx          # overview stats + charts + recent scans
      ScansListPage.jsx          # full scan history, filter by status/target
      NewScanPage.jsx             # the authorization-gate submission form
      ScanDetailPage.jsx           # live status, threat matrix, logs, remediation tab
      VulnerabilityDetailPage.jsx  # AI reasoning, CVE detail, generate remediation
      RemediationQueuePage.jsx      # cross-scan remediation queue
      RemediationReviewPage.jsx     # the high-stakes approve/reject/execute screen
      AdminConfigPage.jsx            # tune AI thresholds at runtime
      AdminCvePage.jsx                # browse cached CVE database, manual sync
```

## 5. What's on each screen, and why

**Login / Register** — Standard email+password auth against `/auth/*`.
Registration lets a `client` or `analyst` self-signup; `admin` accounts
are created by an existing admin (matches your API contract's note on
endpoint 1.6), so there's no "admin" option in the signup role dropdown.

**Dashboard** — The 30-second answer to "how exposed are we right now":
total/in-progress scan counts, open critical findings, remediations
waiting on review, a severity-distribution donut, and a findings-per-scan
trend bar chart across your last 6 completed scans. This is the page a
client or manager opens, not the analyst doing the work.

**Scans → New scan** — This form *is* the authorization gate from your
non-negotiable design principles, made visible: target, a required
justification field (client-side minimum length, but the real
enforcement is server-side in `scans.py`), an explicit checkbox that must
be ticked before the button even attempts a request, and a separate
opt-in checkbox for active testing (SQLi/XSS) — off by default, exactly
as specified. Nothing about this form can accidentally start a scan
against an unauthorized target.

**Scans → list / detail** — The list is your full scan history with
status/target filters. The detail page is the busiest screen in the app:
a live status pill with a pulsing "live" indicator while `IN_PROGRESS`
(polling the REST endpoint as a fallback and subscribing to the
WebSocket for push updates), four severity count cards, and four tabs —
Overview (with a raw live event stream, useful for demoing/debugging the
WebSocket itself), Threat matrix (the filterable/sortable finding table),
Active testing log (SQLi/XSS attempts, or an explanatory empty state if
active testing wasn't enabled for that scan), and Remediation (fixes
generated so far for this scan's findings).

**Threat matrix (`VulnTable`)** — Built with TanStack Table. Filter by
one or more severities at once, filter by disposition status, sort any
column (severity uses a proper CRITICAL→INFO rank, not alphabetical).
Every row shows the AI confidence as a small bar, not just a number —
the point is to make "how sure is the AI" visually impossible to ignore,
per your non-negotiable design principle that AI output is never
presented as certain.

**Vulnerability detail** — Full AI reasoning text (why this was flagged,
in plain language), the matched CVE record if any, related active-test
log entries, a disposition control (OPEN / REMEDIATED / ACCEPTED_RISK /
FALSE_POSITIVE — this is how an analyst tells the system "I've looked at
this and here's the outcome"), and the "Generate remediation" action with
a target-OS picker.

**Remediation queue** — Every remediation across every scan, filterable
by status, defaulting to PENDING so the reviewer's queue is the first
thing they see.

**Remediation review** — The highest-stakes screen in the app, treated
that way deliberately: executive summary and technical script are shown
in full (never truncated, never auto-run), a warning banner reminds the
reviewer that approval authorizes execution but doesn't perform it,
Reject asks for an optional reason, and — the one place in the whole app
with a "type to confirm" pattern — marking a remediation EXECUTED requires
typing the word `EXECUTED` into a field before the button unlocks. That's
intentional friction: this status is treated as ground truth everywhere
else in the system, so it should be hard to set by accident.

**Admin → Configuration** — Inline-editable key/value table for the
`Configurations` rows that tune AI reasoning thresholds without a backend
restart (e.g. `ai_confidence_threshold`, the active-testing rate limit).
Admin-only route, hidden from the sidebar for non-admins.

**Admin → CVE definitions** — Read/search view of the locally cached NVD
data your AI triage step matches findings against, plus a manual "Sync
now" button for `POST /admin/cve-definitions/sync` alongside the
scheduled background job.

## 6. Design notes

Dark "operator console" aesthetic on purpose — this is a tool an analyst
stares at during a live scan, not a marketing page. Teal is the one
interactive accent color; the five severity colors
(critical/high/medium/low/info) are the only other color signal in the
app and are used identically everywhere a finding appears (badges, stat
cards, chart segments) so the eye learns the mapping once. A monospace
face (IBM Plex Mono) is reserved specifically for raw system data — scan
IDs, hosts, ports, CVE IDs, script contents — so it's visually obvious
when you're looking at something the system reported verbatim versus UI
copy describing it.

## 7. Libraries used (per your Task 7 brief)

- **Routing:** `react-router-dom`
- **Data fetching / caching:** `@tanstack/react-query` — handles
  loading/error state, background refetch (the scan detail page polls
  every 4s while a scan is PENDING/IN_PROGRESS as a fallback alongside
  the WebSocket), and cache invalidation when a WebSocket event or a
  mutation (approve/reject/etc.) changes server state
- **Tables:** `@tanstack/react-table` for the threat matrix
- **Charts:** `recharts` for the severity donut and findings trend bar
  chart
- **HTTP:** `axios`, with a JWT-injecting interceptor and normalized
  error messages
