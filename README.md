# Vulnara

**Vulnara** is a next-generation, AI-powered vulnerability scanner and remediation platform for organizations. It provides a complete end-to-end security workflow—from discovering vulnerabilities using active payloads to generating intelligent, actionable fix scripts utilizing Groq—with an organization-wide **Network Activity** overview and **multi-department, role-based access control** so each analyst sees only their department while admins oversee everything. The ecosystem consists of a highly concurrent FastAPI backend, a rich React web dashboard, and a cross-platform Flutter mobile companion app (sharing the same backend and database) for real-time, on-the-go security management.

---

## 🌟 Comprehensive Feature Set

Vulnara is built to provide an unparalleled security auditing and remediation experience. Below is a detailed breakdown of its core capabilities:

### 1. Advanced Vulnerability Scanning & Active Testing
- **Targeted Scanning:** Initiate deep scans against specific IP addresses, domains, or subnets.
- **Strict Authorization Gating:** Built-in compliance checks require users to explicitly authorize and justify scans before they begin, ensuring accountability.
- **Active Exploit Testing:** Optionally enable active testing where the scanner fires safe, controlled exploit payloads (e.g., SQLi, XSS, Command Injection) to verify if vulnerabilities are truly exploitable, minimizing false positives.
- **Real-Time Scan Tracking:** Powered by WebSockets, scan statuses transition seamlessly (`PENDING` ➔ `IN PROGRESS` ➔ `COMPLETED`) on both web and mobile clients without the need to refresh the page.

### 2. AI-Driven Analysis & Threat Logs
- **Intelligent Reasoning:** Every discovered vulnerability includes a detailed modal explaining the AI's reasoning for flagging the issue.
- **Detailed Threat Logs:** View the exact attack vectors and payloads that were tested during active scanning, alongside the AI's verification notes determining whether the attack was successful.
- **Granular Vulnerability Data:** Track CVSS scores, severity levels, and specific affected services and ports for every identified issue.

### 3. Automated Remediation & The Closed-Loop Workflow
- **AI-Generated Fix Scripts:** The system doesn't just find problems; it writes the solutions. Vulnara generates highly specific, technical scripts (e.g., Python code, Bash commands, firewall rules) tailored to remediate the exact vulnerability found.
- **Global Remediation Queue:** A centralized hub to track all AI-generated fixes across the entire organization, filterable by their current status (`PENDING`, `APPROVED`, `REJECTED`, `EXECUTED`).
- **Analyst Review Process:** Security Analysts (and Admins) can review proposed AI scripts and click to explicitly **Approve** or **Reject** them (requiring a justification for rejection).
- **Execution Tracking:** Once a script is approved, an Analyst or Admin applies it to the infrastructure and clicks **Mark Executed** to officially close the security loop.

### 4. Interactive Dashboards & Metrics
- **Posture Overview:** At-a-glance metrics on the main dashboard detailing total vulnerabilities, critical-severity issues, and the number of pending remediations requiring attention.
- **Recent Activity Feeds:** Quick links that allow users to immediately jump into recent scans or the remediation queue straight from the landing page.
- **Vulnerability Status Management:** Analysts and Admins can update the state of individual vulnerabilities (e.g., marking an `OPEN` issue as a `FALSE_POSITIVE`).

### 5. Organization Network Activity (Security Overview)
A dedicated **Network Activity** view (web and mobile) gives a single, organization-wide picture of security posture, built from scan data:
- **Headline metrics:** total scans, assets discovered, open findings, and critical-severity counts.
- **Discovered-asset inventory:** every host → port → service found across scans, with finding counts and the highest CVSS score per asset.
- **Recent activity feed:** who scanned what, status, and finding counts — click through to any scan.
- **Findings-by-severity** breakdown and a **per-department** scan breakdown (admins).
- **Scoping:** admins see the whole organization; analysts see only their own department's activity.

### 6. Multi-Department Access Control (RBAC)
Vulnara is built for organizations, using **departments** as the unit of scoping and two roles.

**Roles**
- **System Administrator:** sees every scan and all network activity across **every** department; manages users, departments, and system configuration; and can approve/reject/execute any remediation.
- **Security Analyst:** scoped to a **single department** — sees only that department's scans, assets, and activity. Runs scans, triages findings, reviews threat logs, approves/rejects AI fix scripts, and marks remediations **Executed**.

**Departments** — Admins create departments (e.g. Finance, IT, HR) from a dedicated **Departments** screen and assign each analyst to one. New scans are automatically tagged to the creator's department, so analysts only ever see their own department's data while admins retain full visibility.

> Self-registration creates **Analyst** accounts only; **Admin** accounts are provisioned by an existing admin.

### 7. Account Recovery (Forgot / Reset Password)
A self-service password-reset flow on both web and mobile:
- Request a reset link from the **Forgot password?** page by entering your registered email.
- Receive a **secure, single-use link that expires in 30 minutes** and set a new password.
- Log back in with the new password.

Responses are intentionally generic (they never reveal whether an email is registered), preventing account enumeration. Delivery uses SMTP when configured (see [Environment Variables](#-environment-variables)); otherwise the link is logged server-side for local testing.

### 8. The Mobile Companion Experience
- **Cross-Platform:** Available on iOS and Android.
- **Full Feature Parity:** Network Activity overview, department-scoped scans, admin Departments management, and the forgot-password flow — all mirrored from the web.
- **Shared Database:** The app talks to the **same backend and database as the web app**, so both always show identical data in real time.
- **Live State Management:** Uses Riverpod and WebSockets to mirror the live state of the web application instantly.
- **On-the-Go Approvals:** Analysts and Admins receive push alerts and can review, approve, or mark remediation scripts executed directly from their phone.

---

## 🧠 How the AI Works

Vulnara's intelligence is **two complementary layers**, not a single black box. A large **pretrained LLM** does open-ended reasoning, and **three small models we trained ourselves** add fast, interpretable, independent verdicts that cross-check it. The raw *detection* of what's on a host (open ports, service versions, CVE matches) is done by the deterministic scanner + NVD lookup — the models reason **about** those findings.

### Layer 1 — Pretrained LLM (used as-is, in a RAG pipeline)
- **Model:** `openai/gpt-oss-120b` (OpenAI's open-weight 120B model) served via the **Groq API**. It is **not fine-tuned** — it's steered with system instructions + strict JSON schemas (with validation and self-correction retries), not training.
- **Retrieval-Augmented Generation (triage):** for each host, Vulnara scans ports + grabs service banners → **retrieves** candidate CVEs from the **NVD** database → feeds both to the LLM, which decides which are real vulnerabilities, assigns severity/CVSS/confidence, filters false positives, and explains its reasoning.
- **Remediation:** generates an executive summary + technical fix script, always saved as `PENDING` — *"AI proposes, human disposes."* No code path can execute a generated script.
- **Active-test verification:** confirms whether a probe's differential response genuinely indicates a vulnerability.

### Layer 2 — Trained ML models (classic supervised ML, our own)
Three scikit-learn models, trained offline and exported to **pure-numpy JSON** so production needs **no scikit-learn at runtime**. Each was chosen by comparing Logistic Regression, Decision Tree and Random Forest with 5-fold cross-validation and deploying the best per task.

| Model | Task | Type | Deployed | Test-set performance |
|---|---|---|---|---|
| **Priority predictor** | How urgently to act (exploit-likelihood) | Binary | Logistic Regression | Accuracy 0.85 · F1 0.81 · ROC-AUC 0.91 |
| **Vulnerability detection** | Genuine vulnerability vs likely false positive | Binary | Logistic Regression | Accuracy 0.88 · F1 0.90 · ROC-AUC 0.92 |
| **Patch-technique recommender** | Which of 8 remediation classes fits | Multi-class | Decision Tree | Accuracy 0.92 · F1 0.87 |

- **Patch classes:** `VERSION_UPGRADE`, `PATCH_AND_RESTART`, `CREDENTIAL_ROTATION`, `ACCESS_CONTROL`, `DISABLE_SERVICE`, `NETWORK_SEGMENTATION`, `WAF_RULE`, `CONFIG_HARDENING`. (The patch target is a rule cascade, so a Decision Tree beats a linear model — F1 0.87 vs 0.61 — and stays interpretable as an explicit decision path.)
- **Why synthetic data?** Labelled real-world exploitation/fix outcomes are proprietary and scarce, so — as the public EPSS project motivates — each model learns a **transparent, documented domain labelling function** with realistic features and added label noise. The whole process is reproducible (fixed random seed).

### How the layers combine
On the **vulnerability detail** screen (web + mobile), the LLM's reasoning sits next to three ML cards — **ML Priority**, **AI Detection**, and **Recommended Patch** — so you can see the models **agree or disagree** with the LLM, giving a defensible second opinion rather than trusting one model alone. The combined verdict is served by `POST /ml/analyze`.

### Reproduce the models
```bash
cd backend/ml
python generate_dataset.py          && python train.py                   # priority model
python generate_security_datasets.py && python train_security_models.py  # detection + patch models
```
Evaluation reports and metrics for the write-up: `backend/ml/EVALUATION.md`, `backend/ml/EVALUATION_SECURITY.md`, `backend/ml/metrics.json`, `backend/ml/security_metrics.json`.

---

## 🏗️ Architecture & Technology Stack

Vulnara leverages a modern, decoupled architecture designed for speed, concurrency, and real-time responsiveness.

### 1. Backend API (`/backend`)
The high-performance core engine that orchestrates scanning, handles AI integration, and broadcasts live events.
- **Framework:** FastAPI (Python 3.x) running on Uvicorn
- **Database:** PostgreSQL utilizing `asyncpg` for non-blocking asynchronous queries
- **ORM:** SQLAlchemy (AsyncIO)
- **AI Integration:** Groq SDK (LLM triage & remediation) **+ trained scikit-learn models** (priority, vulnerability-detection & patch-technique) exported to pure-numpy for runtime — see [How the AI Works](#-how-the-ai-works)
- **Real-Time Communication:** WebSockets
- **Authentication & Security:** JWT (JSON Web Tokens) with passlib & bcrypt
- **Push Notifications:** Firebase Admin SDK (FCM)

### 2. Web Application (`/vulnara-web`)
The primary administration panel designed for deep data visualization and workflow management.
- **Framework:** React 18 & Vite
- **Styling:** Tailwind CSS (featuring a sleek, modern, dark-mode prioritized aesthetic)
- **Routing:** React Router DOM
- **Data Management:** Tanstack React Query (for caching and asynchronous state) & Axios
- **Data Visualization:** Recharts
- **Tables:** Tanstack React Table

### 3. Mobile Companion App (`/vulnara_mobile_scaffold`)
The native mobile application ensuring security teams are always connected.
- **Framework:** Flutter (Dart)
- **State Management:** Riverpod
- **Networking:** Dio (HTTP requests) & `web_socket_channel` (Live updates)
- **Secure Storage:** `flutter_secure_storage` for managing JWTs
- **Push Notifications:** Firebase Messaging & Flutter Local Notifications
- **Design System:** Cupertino Icons & Google Fonts (Outfit / Inter)

---

## 🔑 Test Credentials

The database comes pre-seeded with test accounts so you can immediately explore the different RBAC workflows. 

**Administrator**

| Email | Password | Scope |
|-------|----------|-------|
| `admin@vulnara.com` | `Admin123!` | Full access across **all departments**; manages users, departments & configuration. |

**Department Analysts** — each sees only their own department's scans and network activity (all use password `Analyst123!`):

| Email | Password | Department |
|-------|----------|------------|
| `it.analyst@vulnara.com` | `Analyst123!` | IT Security |
| `finance.analyst@vulnara.com` | `Analyst123!` | Finance |
| `hr.analyst@vulnara.com` | `Analyst123!` | Human Resources |
| `eng.analyst@vulnara.com` | `Analyst123!` | Engineering |
| `ops.analyst@vulnara.com` | `Analyst123!` | Operations |
| `analyst@vulnara.com` | `Analyst123!` | *(unassigned — sees only its own scans)* |

> Log in as **different department analysts** to see the scoping in action: each only sees their department's data, while the admin sees every department. Create more departments or reassign analysts from the admin **Departments** screen.

---

## 🔐 Environment Variables

Set these in `backend/.env` for local development, or in the Render dashboard for production:

| Variable | Purpose |
|---|---|
| `DATABASE_URL` | Postgres connection string (Neon). Defaults to local SQLite if unset. |
| `VULNARA_SECRET_KEY` | JWT signing secret (also signs password-reset tokens). |
| `GROQ_API_KEY` | Groq API key — required for AI triage and remediation. |
| `CORS_ORIGINS` | Comma-separated allowed origins (e.g. the GitHub Pages URL). |
| `APP_BASE_URL` | Public web app URL — used to build password-reset links. |
| `SMTP_HOST` / `SMTP_PORT` / `SMTP_USER` / `SMTP_PASSWORD` | SMTP server for vulnerability-alert and password-reset emails (e.g. Gmail + App Password). When unset, those emails are skipped/logged instead. |

---

## ⚙️ Getting Started (Local Development)

### 1. Running the Backend
Ensure you have Python 3.10+ and PostgreSQL running.
```bash
cd backend
# Install dependencies
pip install -r requirements.txt
# Run the FastAPI development server
uvicorn app.main:app --reload
```
*The backend API will be available at `http://localhost:8000`.*

### 2. Running the Web App
Ensure you have Node.js 18+ installed.
```bash
cd vulnara-web
# Install Node modules
npm install
# Start the Vite development server
npm run dev
```
*The web dashboard will be available at `http://localhost:5173`.*

### 3. Running the Mobile App
Ensure you have the Flutter SDK installed and an Android/iOS emulator running.
```bash
cd vulnara_mobile_scaffold
# Fetch Flutter packages
flutter pub get
# Run the application
flutter run
```
*Note: The mobile app points at the **deployed Render backend** by default (the same database the web app uses), so it works out of the box on emulators and physical devices. To run it against a local backend instead, set `baseUrl`/`wsBaseUrl` in `lib/core/constants.dart` to `http://10.0.2.2:8000` (Android emulator) or your machine's LAN IP (physical device).*

---

## 📚 Further Reading & Testing Workflows

For step-by-step guides on how to test specific workflows (like the closed-loop remediation process or live WebSocket updates), please refer to our detailed documentation:
- [Web Application Testing Guide](./docs/web_app_guide.md)
- [Mobile Application Testing Guide](./docs/mobile_app_guide.md)
- [Deployment Guide (Render + Neon + GitHub Pages)](./docs/deployment_guide.md)
- [Free Deployment Guide (current stack)](./docs/free_deployment_guide.md)

---

## 🚀 Production Deployment

Vulnara is deployed using a fully free stack:

| Component | Service | URL |
|---|---|---|
| **Backend API** | [Render](https://render.com) (Blueprint via `render.yaml`) | `https://<app>.onrender.com` |
| **Database** | [Neon](https://neon.tech) serverless Postgres | — |
| **Frontend** | [GitHub Pages](https://pages.github.com) (via GitHub Actions) | `https://<username>.github.io/vulnara-ai/` |
| **Keep-alive** | [cron-job.org](https://cron-job.org) pings `/health` every 5 min | — |

Frontend deploys automatically on every push to `main` via `.github/workflows/deploy-frontend.yml`.

See [docs/deployment_guide.md](./docs/deployment_guide.md) for full setup instructions.
