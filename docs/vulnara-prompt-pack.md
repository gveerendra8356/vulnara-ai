# VULNARA — Prompt Pack

How to use this: In every new AI chat, paste **PROMPT 0 (Main Context)** first,
then paste **one task prompt** (Task 1, 2, 3...) right after it in the same
message or as your next message. Do this once per chat. Save each output
before moving to the next task — later tasks assume earlier ones exist.

---

## PROMPT 0 — MAIN CONTEXT (paste this at the start of every chat)

```
PROJECT CONTEXT — VULNARA: AI-Augmented Vulnerability Intelligence Platform

Vulnara is a final-year engineering/CS project: a three-tier system that
automates the workflow of a junior penetration tester for a client. It
scans a target (domain/IP the client owns or has explicit permission to
test), collects raw network/service data, uses an AI reasoning layer to
triage and prioritize real vulnerabilities out of noisy scanner output,
optionally tests common web vulnerabilities (SQLi, XSS) in a controlled
opt-in way, generates human-readable risk reports, and generates
remediation scripts that require human approval before execution.

ARCHITECTURE
- Flutter mobile app (Android primary): lightweight, action-oriented —
  trigger scans, view live scan status, push alerts on critical findings,
  approve/reject remediation someone already reviewed on web.
- React + Vite web app: the data-dense "real work" surface — full threat
  matrix with filtering/sorting, scan history and trend comparison, full
  remediation script review before execution, system config/CVE management.
- FastAPI backend (Python): single REST + WebSocket API consumed
  identically by both clients. All business logic lives here — clients are
  thin, no duplicated logic between them.

FIVE CORE DATA FLOWS
1. Target input & recon — user submits domain/IP, confirms authorization
   (logged, required) → host discovery, port enum, banner grabbing → scan
   record created, status IN_PROGRESS, live-updated via WebSocket.
2. Banner/port data → AI triage — raw telemetry normalized to JSON → AI
   cross-references service/version against CVE data (NVD API), scores
   severity/CVSS/confidence, filters false positives → prioritized threat
   matrix.
3. Active testing (opt-in, rate-limited) — controlled SQLi/XSS-style
   payloads against discovered forms/params → AI verifies actual
   reflection/execution (not just pattern match) → logged by attack type
   with risk rating.
4. Config & CVE sync — scan rules and CVE definitions kept current via NVD
   API → tunes AI reasoning thresholds without backend restart.
5. Remediation — user triggers "generate fix" for a finding → AI
   synthesizes a patch/script tailored to the vuln + target OS → stays
   PENDING until human reviews on web and approves execution → dual output:
   executive summary (non-technical) + technical script.

NON-NEGOTIABLE DESIGN PRINCIPLES
- Explicit authorization/scope gate before any scan or active test, logged
  with justification.
- Active testing is opt-in per scan, never default-on.
- Remediation execution always requires human approval — AI proposes,
  human disposes.
- AI outputs always carry a confidence rating, never presented as certain.
- Built and demoed only against systems the user/client owns or has
  explicit written permission to test.

LOCKED TECH STACK (all free tier, no expiring trials — built for real
client handover, not just a demo)
- Mobile: Flutter (Android primary)
- Mobile distribution: Firebase App Distribution
- Web: React + Vite
- Web hosting: Vercel (free tier)
- Backend: FastAPI, Dockerized, hosted on Oracle Cloud Free Tier VM
  (always-on, root access for nmap's raw-socket requirements — not a PaaS
  like Render/HF Spaces, which sleep on inactivity and restrict raw
  sockets)
- Database: Neon (serverless Postgres, auto-wake on query, free tier)
- AI reasoning: Gemini free tier (primary); Ollama self-hosted as optional
  offline fallback
- CVE data: NVD API (free, official)
- Scanner engine: nmap + custom-built payload testing module
- HTTPS/CORS: Let's Encrypt or Cloudflare Tunnel in front of the backend;
  CORS configured for the Vercel domain

Acknowledge this context, then wait for my specific task prompt below.
```

---

## PROMPT 1 — Abstract, Architecture Diagram, DB Schema

```
TASK 1: FOUNDATION DOCUMENTS

Using the Vulnara context above, produce:

1. A one-paragraph abstract (150-200 words) suitable for a thesis/report
   cover page.
2. A system architecture description: list every component (Flutter app,
   React app, FastAPI backend, Neon DB, Gemini API, NVD API, nmap module)
   and describe exactly how data flows between them for a single scan,
   start to finish. Write it so it can be turned into a diagram later.
3. A complete logical database schema for Postgres/Neon covering these
   tables: Scans, Vulnerabilities, Threat_Logs, Configurations,
   CVE_Definitions, Remediations, and Users (add Users even though it
   wasn't in my original flows — I need basic auth).
   For each table: field name, data type, constraints (PK/FK/NOT NULL/
   UNIQUE), and a one-line purpose. Then describe the relationships
   between tables (which fields link to which).
4. Output the schema also as raw SQL CREATE TABLE statements I can run
   directly on Neon.

Be specific to Vulnara's actual data flows, not generic scanner schema
boilerplate.
```

---

## PROMPT 2 — API Contract

```
TASK 2: REST + WEBSOCKET API CONTRACT

Using the Vulnara context above and this database schema [PASTE YOUR
SCHEMA FROM TASK 1 OUTPUT HERE], design the complete API contract that
both the Flutter mobile app and React web app will consume identically.

For each endpoint, give me:
- HTTP method + path
- Purpose (one line)
- Request body/params (with types)
- Response shape (with types)
- Which client(s) use it (mobile, web, or both)
- Auth requirement (public, authenticated, admin-only)

Cover at minimum: auth (login/register/token refresh), scan lifecycle
(create, get status, list, cancel), vulnerabilities (list/filter by scan,
get detail), threat logs (list/filter), remediation (generate, review,
approve, mark executed), config/CVE management (admin endpoints), and a
WebSocket endpoint for live scan status updates (describe the message
format sent over the socket at each stage of a scan).

Output as a clean reference table/list I can literally build against.
```

---

## PROMPT 3 — Backend: Scanner Module

```
TASK 3: BACKEND SCANNER MODULE (FastAPI + nmap)

Using the Vulnara context above and this API contract [PASTE RELEVANT
SCAN ENDPOINTS FROM TASK 2 OUTPUT HERE], help me build the recon/scanning
module of the FastAPI backend.

I need:
1. A Python module design that wraps nmap (via python-nmap or subprocess)
   to perform host discovery, port enumeration, and service banner
   grabbing, given a target domain/IP.
2. How to structure this as an async background task in FastAPI so the
   API can respond immediately with a scan_id while scanning continues,
   pushing progress over the WebSocket endpoint we defined.
3. How to normalize raw nmap output into the structured JSON format that
   will be stored in the Vulnerabilities/Scans tables.
4. Guidance on what nmap flags/privileges are needed on the Oracle Cloud
   VM (raw socket permissions, running as non-root safely with
   capabilities) since I don't want to run the whole backend as root.
5. Explicit code for the authorization/scope confirmation gate — this
   must block scan creation unless the user has confirmed authorization,
   and log that confirmation with a timestamp.

Give me working, well-commented Python code, not pseudocode.
```

---

## PROMPT 4 — Backend: AI Triage + Remediation Module

```
TASK 4: AI REASONING LAYER (Triage + Remediation)

Using the Vulnara context above and this schema/API [PASTE RELEVANT PARTS
OF TASK 1 & 2 OUTPUT], help me build the AI reasoning layer that:

1. Takes normalized scan JSON (service names, versions, banners) and
   queries the NVD API for matching CVEs, then calls the Gemini API to:
   - Assess whether each match is a real risk or likely false positive
     given the context
   - Assign a confidence_rating and severity
   - Produce a plain-English explanation of the finding
   Give me the actual prompt template I should send to Gemini for this
   step, plus the Python code to call the Gemini free-tier API and parse
   a structured JSON response reliably.

2. Takes a specific vulnerability_id and target OS, and generates:
   - An executive summary (non-technical, for a report)
   - A technical remediation script (Bash/shell)
   Give me the Gemini prompt template for this, and the Python code that
   stores the result in the Remediations table with status PENDING.

3. Explain how to design the Gemini prompts so outputs stay
   consistent/structured (JSON mode or strict formatting instructions)
   since I'll be parsing these programmatically, not just reading them.

4. A short note on rate limits for Gemini's free tier and how to handle
   failures/retries gracefully in the backend.
```

---

## PROMPT 5 — Backend: Active Payload Testing Module

```
TASK 5: ACTIVE PAYLOAD TESTING MODULE

Using the Vulnara context above, help me build the opt-in active testing
module (flow 3) that:

1. Takes discovered forms/URL parameters from the recon phase and injects
   a controlled set of test payloads (SQLi, XSS, common command injection
   patterns) — give me a safe, minimal starter payload set (not an
   exhaustive attack library) appropriate for a defensive/educational
   student project.
2. Captures the target's response and determines whether the payload was
   reflected or actually executed (not just present in output) — explain
   the verification logic clearly.
3. Structures results into the Threat_Logs table format from our schema,
   categorized by attack type with a risk rating.
4. Includes rate-limiting/throttling so this module doesn't hammer the
   target, and a hard opt-in flag that must be explicitly set per scan
   before this module runs at all.

Give me working Python code with clear comments, and flag anywhere the
logic could produce false positives so I can address it in my thesis's
limitations section.
```

---

## PROMPT 6 — Flutter Mobile App

```
TASK 6: FLUTTER MOBILE APP

Using the Vulnara context above and this API contract [PASTE MOBILE-
RELEVANT ENDPOINTS FROM TASK 2 OUTPUT], help me build the Flutter mobile
app.

Scope for mobile (confirmed): scan trigger + authorization confirmation
screen, live scan status view (consuming the WebSocket), push
notifications for critical findings, a simplified threat summary
(severity counts + top findings only, not the full table), and a
lightweight approve/reject screen for remediation already reviewed on
web.

I need:
1. Recommended folder/module structure (state management: Riverpod).
2. The data models (Dart classes) matching our API response shapes.
3. The API/repository layer (Dio-based) for calling the FastAPI backend
   and connecting to the WebSocket.
4. Screen-by-screen breakdown with what state each screen needs.
5. How to set up Firebase Cloud Messaging for the critical-finding push
   notifications, triggered from the backend.

Give me a build order (which screen/feature first) and actual Dart code
for the core pieces, not just descriptions.
```

---

## PROMPT 7 — React Web App

```
TASK 7: REACT WEB APP (Vite)

Using the Vulnara context above and this API contract [PASTE WEB-RELEVANT
ENDPOINTS FROM TASK 2 OUTPUT], help me build the React web dashboard.

Scope for web (confirmed): full threat matrix with filtering/sorting by
severity/type/date, scan history and trend comparison between scans, full
remediation script review screen (view generated script + executive
summary, approve/reject/mark executed), and admin screens for
config/CVE_Definitions management.

I need:
1. Recommended project structure (React + Vite + TypeScript, routing
   library, state/data-fetching approach — e.g. TanStack Query).
2. Which library to use for the data tables (e.g. TanStack Table) and
   charts (e.g. Recharts) for the scan trend comparison view.
3. The API client layer (typed, matching our contract) and auth/token
   handling.
4. Page-by-page breakdown with what data each page fetches.
5. The remediation review page in detail — this is the highest-stakes
   screen (approving execution of a generated script), so include a
   clear confirm/warning UI pattern before a user can mark something
   EXECUTED.

Give me a build order and actual code for the core pieces.
```

---

## PROMPT 8 — Deployment & Handover

```
TASK 8: DEPLOYMENT & CLIENT HANDOVER

Using the Vulnara context above, help me deploy and hand this project
over to a client so it runs independently of my own laptop/accounts.

I need:
1. Step-by-step Oracle Cloud Free Tier VM setup: creating the instance,
   Docker installation, deploying the FastAPI backend as a Docker
   container with restart-on-reboot (systemd or Docker restart policy),
   and firewall/security group rules for the ports we need (API, nmap
   scanning traffic).
2. HTTPS setup in front of the backend — compare Let's Encrypt (Certbot)
   direct on the VM vs. Cloudflare Tunnel, and recommend one for our case
   with steps.
3. CORS configuration in FastAPI to allow only our Vercel domain.
4. Neon database setup: creating the project, connection string handling
   via environment variables, and a simple keep-alive/scheduled job so
   the free project doesn't sit fully idle for extended periods.
5. Vercel deployment steps for the React app (env vars for API base URL).
6. Firebase App Distribution setup for pushing the Android APK to the
   client without the Play Store.
7. A clear checklist of what needs to move to the CLIENT's own accounts
   (Oracle, Neon, Vercel, Firebase, Gemini API key) vs. what can stay on
   mine, and why doing this handover properly matters (so I'm not
   personally liable for hosting their production tool indefinitely).

Give me this as a step-by-step runbook I can literally follow.
```

---

## PROMPT 9 — Thesis Sections (Challenges, Ethics, Report Writing)

```
TASK 9: THESIS SUPPORT SECTIONS

Using the Vulnara context above, help me write the academic-facing parts
of my final year report.

I need:
1. A list of the 5-8 hardest technical/academic challenges in building
   Vulnara and how I addressed (or plan to address) each — for a
   "Challenges & Limitations" chapter. Be specific to Vulnara's actual
   design (AI-based false-positive filtering, active payload
   verification, remediation script safety) not generic project-report
   boilerplate.
2. A dedicated section on how the authorization-gate, opt-in active
   testing, and human-approval-before-execution design choices address
   the ethical/legal concerns inherent in building a scanning/exploitation
   tool — written so it holds up under questioning in a viva.
3. A short "Related Work / Comparison" framing showing how Vulnara differs
   from existing tools (Nessus, OpenVAS, Burp Suite) — specifically the
   AI-reasoning-layer differentiator — suitable for a literature review
   section.
4. A future-work section listing realistic next steps (e.g. iOS support,
   multi-target scanning, integration with a SIEM) that sound credible,
   not just a wishlist.

Write this in formal academic report language, not conversational tone.
```
