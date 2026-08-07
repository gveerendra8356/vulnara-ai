# Integration and Fixes

## Overview
This document summarizes the current state of integration between the three core components of the Vulnara platform:
1. **Backend** (FastAPI)
2. **Web** (React / Vite)
3. **Mobile** (Flutter)

After thoroughly analyzing the codebase, several missing links and necessary adjustments were identified to enable full end-to-end communication.

## Identified Issues and Applied Fixes

### 1. Missing Backend CORS Configuration
**Issue:** The FastAPI backend did not have Cross-Origin Resource Sharing (CORS) configured. As a result, the Web application (running on `localhost:5173`) was blocked by browsers from making requests to the API on `localhost:8000`.
**Fix:** Added the `CORSMiddleware` in `backend/app/main.py` to allow all origins, methods, and headers for development purposes.

### 2. Implemented Authentication & Core Endpoints in Backend
**Issue:** The Web and Mobile apps were initially designed against the full "Task 2 API Contract", which includes endpoints like `/auth/login`, `/auth/register`, and more. However, the backend only exposed `/scans` and `/remediations` endpoints. This meant the mobile app was unable to log in, and the web app relied entirely on mock data.
**Fix:** The full `/auth` module was implemented in the backend. 
- **Models & Security**: Mapped the `users` and `token_denylist` tables and securely managed passwords using `bcrypt` and JWTs for access/refresh tokens.
- **API Endpoints**: Fully implemented `/auth/register`, `/auth/login`, `/auth/me`, `/auth/refresh`, `/auth/logout`, and `/auth/users`.
**Impact:**
- **Web App:** You can now set `VITE_USE_MOCK=false` in the `.env` file to fully communicate with the real backend.
- **Mobile App:** The mobile application will now correctly authenticate users and progress past the login screen using the actual FastAPI backend.

### 3. Mobile App API Configuration
**Issue:** The Mobile app's `lib/core/constants.dart` pointed to a generic placeholder URL (`https://your-vulnara-backend.example.com`).
**Fix:** Updated the `baseUrl` and `wsBaseUrl` to point to `http://10.0.2.2:8000`, which is the correct loopback address to reach your host machine's `localhost:8000` from an Android emulator. *(Note: If you run the Flutter app on iOS simulator, web, or desktop, you will need to change this back to `http://localhost:8000`).*

---

## How to Run All Components

Here are the commands to run each component locally. It is recommended to open **three separate terminals**, one for each part of the stack.

### 1. Backend (FastAPI)
The backend runs on Python and uses `uvicorn` as the server. 

```bash
cd backend
# Create and activate a virtual environment (optional but recommended)
python -m venv venv
# On Windows:
venv\Scripts\activate
# On Mac/Linux:
# source venv/bin/activate

# Install requirements
pip install -r requirements.txt

# IMPORTANT: Ensure your DATABASE_URL environment variable is set
# Apply database migrations
python apply_migration.py

# Run the server (starts on http://localhost:8000)
uvicorn app.main:app --reload
```

### 2. Web App (React / Vite)
The web app is a modern React application. It currently uses "Mock Mode" by default so you can test the UI fully without the backend.

```bash
cd vulnara-web
# Install dependencies
npm install

# Run the development server (starts on http://localhost:5173)
npm run dev
```
*(To test against the newly implemented real backend, copy `.env.example` to `.env` and set `VITE_USE_MOCK=false`).*

### 3. Mobile App (Flutter)
The mobile app is a Flutter project designed for Android and iOS.

```bash
cd vulnara_mobile_scaffold
# Fetch all Flutter dependencies
flutter pub get

# Run the application on an available device/emulator
flutter run
```
*(Make sure you have an Android emulator running or a device connected via USB. The backend must be running for login to work!)*
