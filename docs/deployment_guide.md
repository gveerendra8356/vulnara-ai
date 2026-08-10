# Vulnara: Production Deployment Guide

Moving Vulnara from a local development environment to a live, production-ready system involves deploying three distinct components: the Backend API, the Frontend Web Dashboard, and the Mobile Companion App. 

This guide details the exact steps and best practices required to successfully deploy the entire Vulnara ecosystem.

---

## Phase 1: Deploying the Backend API (FastAPI)

The backend is the most critical piece. Because it handles heavy asynchronous port scanning and persistent WebSocket connections, it should ideally be deployed to a scalable VPS (like AWS EC2, DigitalOcean Droplet) or a containerized environment (AWS ECS, Google Cloud Run).

### 1. Database Setup
You must migrate from a local PostgreSQL database to a managed cloud database.
* **Options:** AWS RDS, Supabase, or DigitalOcean Managed Databases.
* **Important:** Ensure your database supports high concurrency, as `asyncpg` will open numerous connections.

### 2. Environment Variables
On your production server, create a `.env` file with your production secrets:
```env
DATABASE_URL=postgresql+asyncpg://user:password@your-db-host.com/vulnara
JWT_SECRET_KEY=generate_a_very_long_secure_random_string_here
GROQ_API_KEY=your_production_groq_api_key
FIREBASE_SERVICE_ACCOUNT_JSON=/path/to/secure/firebase.json
```

### 3. Running with Gunicorn & Uvicorn
In development, you run `uvicorn app.main:app --reload`. In production, you must use **Gunicorn** as a process manager with Uvicorn worker classes to handle crashes and parallel processing.
```bash
# Install gunicorn
pip install gunicorn
# Run with 4 asynchronous workers
gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
```

### 4. Setting up the Reverse Proxy (Nginx)
You cannot expose Uvicorn directly to the open web. You must place Nginx in front of it to handle SSL (HTTPS) and route WebSocket (WSS) traffic appropriately.
* Use **Certbot (Let's Encrypt)** to secure your domain with SSL.
* **Nginx WebSocket Config:** Ensure your Nginx configuration allows protocol upgrades for WebSockets:
```nginx
location /ws {
    proxy_pass http://localhost:8000;
    proxy_http_version 1.1;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection "Upgrade";
}
```

---

## Phase 2: Deploying the Frontend (React / Vite)

The web dashboard is a Single Page Application (SPA). Because it compiles down to pure static HTML/CSS/JS, it is incredibly cheap and easy to host using modern CDN providers.

### 1. Production Environment Variables
Before building, ensure you have an environment file (e.g., `.env.production`) at the root of `/vulnara-web` pointing to your new production backend:
```env
VITE_API_URL=https://api.yourdomain.com
VITE_WS_URL=wss://api.yourdomain.com/ws
```

### 2. Building the App
Run the Vite build command to generate the highly optimized, minified production assets:
```bash
npm install
npm run build
```
This creates a `/dist` folder containing your entire compiled web application.

### 3. Hosting (Vercel, Netlify, or AWS S3)
* **Vercel / Netlify:** The easiest method. Simply connect your GitHub repository to Vercel/Netlify, set the build command to `npm run build`, and the publish directory to `dist`.
* **AWS S3 + CloudFront:** Upload the contents of the `/dist` folder to an S3 bucket and serve it globally using CloudFront. Ensure you set up a fallback routing rule so that any 404 errors redirect to `index.html` (since React Router DOM handles the routing internally).

---

## Phase 3: Deploying the Mobile App (Flutter)

Deploying a mobile application requires generating the respective binaries for Android and iOS and submitting them to the App Stores.

### 1. Update Production Constants
Open `vulnara_mobile_scaffold/lib/core/constants.dart` and ensure your `baseUrl` and `wsBaseUrl` point to your production Nginx server, not `10.0.2.2`.
```dart
const String baseUrl = "https://api.yourdomain.com";
const String wsBaseUrl = "wss://api.yourdomain.com/ws";
```

### 2. Building for Android (Google Play Store)
To upload to the Google Play Store, you need to generate an App Bundle (`.aab`):
```bash
flutter build appbundle --release
```
* **Output:** This generates an `.aab` file in `build/app/outputs/bundle/release/`.
* **Deployment:** Upload this file to the Google Play Console, fill out your store listing, and submit for review.

### 3. Building for iOS (Apple App Store)
*(Note: You must be using a Mac with Xcode installed to build for iOS).*
1. Run the iOS build command:
   ```bash
   flutter build ipa --release
   ```
2. Open `ios/Runner.xcworkspace` in Xcode.
3. Ensure your App Store Provisioning Profiles and Signing Certificates are configured correctly in the "Signing & Capabilities" tab.
4. Go to **Product > Archive**, and then use the Xcode Organizer to directly distribute the app to **TestFlight** or the **App Store Connect**.

---

## 🏁 Post-Deployment Checklist

- [ ] **Test Real-Time Sync:** Open the deployed Web App and Mobile App simultaneously. Request a scan on the Web App and ensure the Mobile App immediately shows the `IN PROGRESS` state via WebSockets.
- [ ] **Verify Threat Logs:** Ensure the backend container has outbound network access to the internet to actively ping test targets.
- [ ] **Check Groq API:** Ensure your Groq production API key has a sufficient billing limit to handle organizational-level threat log analysis.
- [ ] **Firebase Setup:** Ensure the production Apple Push Notification service (APNs) and Firebase Cloud Messaging (FCM) keys are uploaded so Analysts receive notifications on production devices.
