# Vulnara: Architecture & Technology Overview (A to Z)

Welcome to the complete internal architecture and technology guide for **Vulnara**, the AI-powered vulnerability scanner. 

This document provides a comprehensive A to Z breakdown of the entire platform, including an exhaustive tech stack table, detailed workflows, and the exact reasoning behind every architectural decision made across the Backend, Web Dashboard, and Mobile Companion App.

---

## 🛠️ Comprehensive Tech Stack Matrix

Below is the complete technology stack used across the Vulnara ecosystem, categorized by component.

| Component | Technology / Library | Version / Detail | Primary Purpose (Why we used it) |
| :--- | :--- | :--- | :--- |
| **Backend** | **Python** | 3.10+ | Core programming language for the backend API. |
| | **FastAPI** | `>=0.111` | High-performance, async web framework. Used for fast API routing and automatic OpenAPI documentation. |
| | **Uvicorn** | `[standard]>=0.30` | ASGI web server implementation for Python. Required to run FastAPI asynchronously. |
| | **PostgreSQL** | Relational DB | Primary database. Chosen for robust relational integrity (Users -> Scans -> Remediations). |
| | **asyncpg** | `>=0.29` | Database interface library designed specifically for PostgreSQL and Python/asyncio. Extremely fast, non-blocking I/O. |
| | **SQLAlchemy** | `[asyncio]>=2.0` | ORM used to map Python classes to database tables without blocking the event loop. |
| | **WebSockets** | `>=12.0` | Bidirectional communication protocol to push live status updates to Web and Mobile clients instantly. |
| | **Groq API** | `>=0.4` | LLM API used to analyze raw threat logs, verify vulnerabilities, and write technical remediation scripts. |
| | **Firebase Admin** | `>=6.5` | SDK used to push background notifications to Analysts on the mobile app. |
| | **passlib / python-jose** | JWT & Bcrypt | Handles secure password hashing and generating JSON Web Tokens for stateless authentication. |
| **Frontend (Web Dashboard)** | **React** | `^18.3.1` | Component-based UI library. Used for building a highly modular and reactive dashboard. |
| | **Vite** | `^5.3.4` | Next-generation build tool. Chosen over Webpack for instantaneous Hot Module Replacement (HMR) and fast builds. |
| | **Tailwind CSS** | `^3.4.9` | Utility-first CSS framework. Used to rapidly build a premium, custom, dark-mode aesthetic. |
| | **Tanstack React Query** | `^5.51.1` | Asynchronous state management. Handles caching, deduping, and background refetching of API data (eliminates complex `useEffect` chains). |
| | **Axios** | `^1.7.2` | HTTP client used alongside React Query to simplify header injection (JWTs) and request interception. |
| | **React Router DOM** | `^6.25.1` | Standard routing library for navigating between dashboard views securely. |
| | **Recharts** | `^2.12.7` | Composable charting library for building the dynamic metrics graphs on the main dashboard. |
| | **Tanstack React Table**| `8.20.5` | Headless data grid library for creating the highly sortable and filterable vulnerability list. |
| **Mobile App** | **Flutter / Dart** | SDK `>=3.3.0` | Cross-platform framework. Allows compiling native iOS and Android apps from a single codebase with a 60FPS render engine. |
| | **Riverpod** | `^2.5.1` | Compile-safe state management. Crucial for syncing the live WebSocket state stream with the UI seamlessly. |
| | **web_socket_channel** | `^2.4.0` | Dart's official package for raw WebSocket connections, syncing perfectly with the FastAPI backend. |
| | **Dio** | `^5.4.3` | Powerful HTTP client for Dart, managing REST API calls and JWT interceptors. |
| | **Firebase Messaging** | FCM | Handles inbound push notifications even when the app is terminated or in the background. |
| | **flutter_secure_storage**| `^9.2.2` | Encrypts and securely stores the user's JWT session token in the iOS Keychain / Android Keystore. |
| | **go_router** | `^14.1.4` | Declarative routing package for Flutter, handling deep linking and role-based redirects. |

---

## 🔄 The Complete End-to-End Workflow (A to Z)

To truly understand how these technologies synchronize, here is the complete lifecycle of Vulnara in action:

1. **Authentication (JWT):** A user (Admin, Analyst, or Client) logs into the Web or Mobile app. The Backend verifies the credentials using `passlib(bcrypt)` and returns a JWT via `python-jose`. The client stores this securely (`flutter_secure_storage` on mobile).
2. **Scan Initiation & Gating:** A Client requests a scan on a target IP. The frontend enforces an Authorization checkbox and justification. The backend validates the JWT role and saves the `PENDING` scan to PostgreSQL via `SQLAlchemy(asyncpg)`.
3. **Active Engine & WebSockets:** The scanner engine picks up the job. It immediately broadcasts an `IN_PROGRESS` status over the `WebSockets` layer. The Web App (via standard WebSocket API) and Mobile App (via `web_socket_channel` + `Riverpod`) instantly update the user's screen without a page refresh.
4. **Threat Payload Injection:** The scanner actively fires safe payloads (SQLi, XSS) at the target. It logs the raw HTTP responses (Threat Logs).
5. **AI Inference:** The backend sends the raw Threat Logs to `Groq`. The LLM returns a JSON payload containing:
   - A human-readable verification note.
   - A custom Bash/Python remediation script designed specifically for the target's architecture.
6. **Push Notification:** Once vulnerabilities are logged, the backend triggers `Firebase Admin`. An Analyst receives a push notification on their iOS/Android device via `Firebase Messaging`.
7. **Analyst Triage:** The Analyst opens the Mobile App, views the AI-generated Python script, and clicks "Approve". This sends a REST `PATCH` request (via `Dio`) to the backend.
8. **Client Execution:** The Client sees the Approved status (live updated via WebSockets), views the script, applies it to their servers, and marks it `EXECUTED`. The loop is closed.

---

## 🏗️ Deep Dive: Architectural Decisions

### 1. The Backend Core (`/backend`)
The backend requires extremely high concurrency to handle simultaneous port scans, open WebSocket connections, and slow external AI API calls.
* **Why FastAPI + Asyncpg?** Standard Python frameworks (like Django or Flask with psycopg2) use synchronous, blocking workers. If a scan takes 5 minutes, that worker is blocked. By using FastAPI with `asyncpg`, all I/O bound tasks are asynchronous. A single server instance can handle thousands of simultaneous WebSocket connections and scans without blocking the main event loop.

### 2. The Frontend (`/vulnara-web`)
The frontend web dashboard is a heavy data-visualization client designed for deep analytical workflows.
* **Why React Query + Vite?** Managing loading states, error states, and background polling manually with `useEffect` leads to spaghetti code. `Tanstack React Query` completely abstracts this, caching vulnerability data automatically. `Vite` was chosen over Webpack because its ES-module based dev server starts in under 500ms, vastly improving developer velocity.
* **Why Tailwind CSS?** It allows us to implement our strict, premium dark-mode design system directly in the JSX, avoiding the cascading nightmares of traditional CSS files and ensuring total consistency.

### 3. The Mobile Companion App (`/vulnara_mobile_scaffold`)
The Mobile App is strictly for on-the-go triaging—allowing Analysts to unblock Clients without needing a laptop.
* **Why Flutter?** Maintaining separate Swift (iOS) and Kotlin (Android) codebases for a companion app is too resource-intensive. Flutter provides near-native performance and custom pixel-perfect rendering engine, which allows us to match the Web Dashboard's premium aesthetic flawlessly on any device.
* **Why Riverpod?** Standard Flutter state management (Provider or setState) struggles with complex, asynchronous streams (like listening to a WebSocket and updating a specific vulnerability card in a list). Riverpod provides a compile-safe, robust architecture to listen to our WebSocket stream and surgically rebuild only the necessary UI widgets.

---

## 🔐 Security & RBAC Implementation

Security is handled at both the API boundary and the Client UI level:
- **API Boundary:** Every FastAPI endpoint requires a JWT `Depends()` injection. If a Client attempts to hit the `/remediations/approve` endpoint, the backend strictly rejects it with a 403 Forbidden.
- **UI Boundary:** Both the React and Flutter apps decode the JWT payload to check the `role` claim. Based on this, they dynamically render or hide UI elements (e.g., the "Approve Remediation" button simply does not exist in the DOM/Widget Tree for a Client).
