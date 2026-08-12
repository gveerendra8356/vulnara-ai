# Vulnara: Production Deployment Guide

Moving Vulnara from a local development environment to a live, production-ready system involves deploying three distinct components: the Backend API, the Frontend Web Dashboard, and the Mobile Companion App.

This guide details the exact steps and best practices required to successfully deploy the entire Vulnara ecosystem.

---

## Phase 1: Deploying the Backend API (FastAPI → Render + Neon)

The backend is deployed on **Render** (free-tier Web Service) backed by **Neon** (serverless Postgres). No VM management is required. Render auto-deploys on every `git push` via the `render.yaml` Blueprint in the repo root.

### 1. Database Setup — Neon (Serverless Postgres)

1. Create a free account at [neon.tech](https://neon.tech/).
2. Create a new **Project** and copy the Postgres connection string from the dashboard.
3. Convert the connection string to the `asyncpg` driver prefix:
   ```
   # Neon gives you: postgres://user:pass@host/db?sslmode=require
   # Change it to:
   postgresql+asyncpg://user:pass@host/db
   ```
   > **Note:** `sslmode=` is a `psycopg2`/libpq parameter that `asyncpg` rejects. `core/db.py` strips it and passes `ssl="require"` via `connect_args` instead — so just remove the `?sslmode=require` suffix from the URL you paste into the env var.

### 2. Environment Variables

Set the following in the **Render dashboard → Environment** tab (or let the Blueprint prompt you for the `sync: false` ones):

| Variable | Value | Source |
|---|---|---|
| `DATABASE_URL` | `postgresql+asyncpg://user:pass@host/db` | Neon dashboard |
| `VULNARA_SECRET_KEY` | auto-generated | Render `generateValue: true` |
| `GROQ_API_KEY` | your key | [console.groq.com](https://console.groq.com) |
| `CORS_ORIGINS` | `https://<your-pages-site>.github.io,http://localhost:5173` | Frontend URL(s) |

### 3. Deploying via Render Blueprint

The repo contains a `render.yaml` at the backend level. Render reads this file and provisions the service automatically.

```bash
# 1. Push backend code (including render.yaml) to GitHub
git push

# 2. On Render: New → Blueprint → connect the repo
# 3. Fill in DATABASE_URL and GROQ_API_KEY when prompted
# 4. Deploy
```

Verify the deployment:
```
GET https://<your-app>.onrender.com/health
# Expected: {"status": "ok", "db": "ok"}
```

> **`/health` behavior:** The endpoint runs a real `SELECT 1` against Neon, so it simultaneously acts as a keep-alive ping for both Render and Neon's compute node.

### 4. Keep the Service Awake (Render Free Tier)

Render's free tier spins down after **15 minutes** of inactivity. Solve this with a free cron:

1. Create a free account at [cron-job.org](https://cron-job.org/).
2. Create a job that hits `GET https://<your-app>.onrender.com/health` every **5 minutes**.
3. This prevents both Render's sleep and Neon's compute suspend simultaneously.

### Known Limitations

- Cold start is ~20–30 s if the keep-alive cron is interrupted.
- Free-tier Render does not support raw socket access (i.e., `nmap`). For active scanning, a full VM is required (see [free_deployment_guide.md](./free_deployment_guide.md)).

---

## Phase 2: Deploying the Frontend (React / Vite → GitHub Pages)

The web dashboard compiles to pure static HTML/CSS/JS and is hosted for free on **GitHub Pages** using a GitHub Actions workflow.

### 1. Configure Vite for GitHub Pages

In `vulnara-web/vite.config.js`, the `base` must match your repository name:

```js
export default defineConfig({
  plugins: [react()],
  base: '/vulnara-ai/',   // ← your repo name
  server: { port: 5173 },
});
```

### 2. Set Environment Variables

Create `vulnara-web/.env.production` (do **not** commit secrets here — these values are baked into the static bundle at build time):

```env
VITE_API_BASE_URL=https://<your-app>.onrender.com
VITE_WS_BASE_URL=wss://<your-app>.onrender.com
VITE_USE_MOCK=false
```

### 3. Deploy via GitHub Actions

The repo contains `.github/workflows/deploy-frontend.yml`. On every push to `main` it:
1. Runs `npm ci && npm run build` inside `vulnara-web/`.
2. Publishes the `dist/` folder to the `gh-pages` branch.

Enable Pages in your GitHub repo:
- **Settings → Pages → Source:** `Deploy from a branch` → branch: `gh-pages`, folder: `/ (root)`.

The site will be live at:
```
https://<github-username>.github.io/vulnara-ai/
```

### 4. Update CORS on Render

Once Pages is live, add its URL to the `CORS_ORIGINS` env var on Render:
```
https://<github-username>.github.io,http://localhost:5173
```

### SPA Routing Fix (React Router)

GitHub Pages doesn't support client-side routing natively. Add a `404.html` redirect shim (already included in `vulnara-web/public/404.html`) so deep links like `/scans/123` work correctly.

---

## Phase 3: Deploying the Mobile App (Flutter)

Deploying a mobile application requires generating the respective binaries for Android and iOS and submitting them to the App Stores.

### 1. Update Production Constants

Open `vulnara_mobile_scaffold/lib/core/constants.dart` and point to your Render backend:

```dart
const String baseUrl = "https://<your-app>.onrender.com";
const String wsBaseUrl = "wss://<your-app>.onrender.com/ws";
```

### 2. Building for Android (Google Play Store)

To upload to the Google Play Store, generate an App Bundle (`.aab`):

```bash
flutter build appbundle --release
```

- **Output:** `build/app/outputs/bundle/release/`
- **Deployment:** Upload to Google Play Console and submit for review.

### 3. Building for iOS (Apple App Store)

*(Requires a Mac with Xcode installed.)*

```bash
flutter build ipa --release
```

Open `ios/Runner.xcworkspace` in Xcode, configure Signing & Capabilities, then **Product → Archive** and distribute via Xcode Organizer.

---

## 🏁 Post-Deployment Checklist

- [ ] `GET /health` returns `{"status": "ok", "db": "ok"}` on Render.
- [ ] GitHub Pages site loads at `https://<username>.github.io/vulnara-ai/`.
- [ ] Login works — JWT round-trips to the Render backend.
- [ ] CORS is set correctly: Render accepts requests from the Pages domain.
- [ ] cron-job.org keep-alive is active and firing every 5 minutes.
- [ ] **Test Real-Time Sync:** Open the web app and mobile app simultaneously; confirm WebSocket scan-status updates propagate in real time.
- [ ] **Check Groq API:** Ensure the production key has sufficient quota.
