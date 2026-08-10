# Vulnara

**Vulnara** is a next-generation, AI-powered vulnerability scanner and remediation platform. It provides a complete end-to-end security workflow—from discovering vulnerabilities using active payloads to generating intelligent, actionable fix scripts utilizing Groq. The ecosystem consists of a highly concurrent FastAPI backend, a rich React web dashboard, and a cross-platform Flutter mobile companion app for real-time, on-the-go security management.

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
- **Analyst Review Process:** Security Analysts can review proposed AI scripts and click to explicitly **Approve** or **Reject** them (requiring a justification for rejection).
- **Client Execution:** Once approved by an Analyst, end Clients can access the scripts, apply them to their infrastructure, and click **Mark Executed** to officially close the security loop.

### 4. Interactive Dashboards & Metrics
- **Posture Overview:** At-a-glance metrics on the main dashboard detailing total vulnerabilities, critical-severity issues, and the number of pending remediations requiring attention.
- **Recent Activity Feeds:** Quick links that allow users to immediately jump into recent scans or the remediation queue straight from the landing page.
- **Vulnerability Status Management:** Analysts and Admins can update the state of individual vulnerabilities (e.g., marking an `OPEN` issue as a `FALSE_POSITIVE`).

### 5. Multi-Tiered Role-Based Access Control (RBAC)
Vulnara natively supports complex access control to separate duties between different stakeholders:
- **System Administrator:** Can view all scans, manage overarching system configurations, approve/reject any remediation, and access all administrative features.
- **Security Analyst:** Responsible for triaging. Can view all scans, review complex threat logs, change vulnerability statuses, and act as the gatekeeper for approving AI-generated scripts.
- **Demo Client:** A restricted view where users can only initiate authorized scans for their own infrastructure, view their specific scan results, and mark approved remediations as "Executed".

### 6. The Mobile Companion Experience
- **Cross-Platform:** Available on iOS and Android.
- **Live State Management:** Uses Riverpod and WebSockets to mirror the live state of the web application instantly.
- **On-the-Go Approvals:** Analysts receive push alerts and can review or approve remediation scripts directly from their phone, unblocking clients instantly.

---

## 🏗️ Architecture & Technology Stack

Vulnara leverages a modern, decoupled architecture designed for speed, concurrency, and real-time responsiveness.

### 1. Backend API (`/backend`)
The high-performance core engine that orchestrates scanning, handles AI integration, and broadcasts live events.
- **Framework:** FastAPI (Python 3.x) running on Uvicorn
- **Database:** PostgreSQL utilizing `asyncpg` for non-blocking asynchronous queries
- **ORM:** SQLAlchemy (AsyncIO)
- **AI Integration:** Groq SDK (for analyzing logs and generating remediations)
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

| Role | Email | Password | Capabilities |
|------|-------|----------|--------------|
| **Admin** | `admin@vulnara.com` | `Admin123!` | Full system access, configurations, global approvals. |
| **Analyst**| `analyst@vulnara.com` | `Analyst123!` | View threat logs, approve/reject AI fixes, mark false positives. |
| **Client** | `client@vulnara.com` | `Client123!` | Run authorized scans, view personal scans, execute fixes. |

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
*Note: The mobile app defaults to `10.0.2.2` for Android emulators. To test on a physical device, update the IP in `lib/core/constants.dart`.*

---

## 📚 Further Reading & Testing Workflows

For step-by-step guides on how to test specific workflows (like the closed-loop remediation process or live WebSocket updates), please refer to our detailed documentation:
- [Web Application Testing Guide](./docs/web_app_guide.md)
- [Mobile Application Testing Guide](./docs/mobile_app_guide.md)
