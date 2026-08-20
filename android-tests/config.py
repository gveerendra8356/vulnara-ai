"""
config.py

Central, environment-driven config for the vulnara_mobile_scaffold Android
test suite. Mirrors the pattern used by selenium-tests/config.py and
backend-tests/conftest.py in this repo: everything overridable comes from
os.environ so the same test code runs unmodified locally and in CI.

Test accounts match backend-tests/seed_test_accounts.py exactly (the four
QA accounts are seeded into the same ephemeral SQLite DB the backend
service uses in CI -- see ../.github/workflows/android-tests.yml). Do not
change these values without also updating that seed script.
"""

import os

# APK under test. The CI workflow builds this from vulnara_mobile_scaffold/
# and exports it to this path before pytest runs; locally, build it the
# same way (see README.md "Running locally").
APK_PATH = os.environ.get(
    "APK_PATH",
    os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "..", "vulnara_mobile_scaffold", "build", "app", "outputs", "flutter-apk", "app-debug.apk",
    ),
)

APP_PACKAGE = os.environ.get("APP_PACKAGE", "com.vulnara.vulnara_mobile")
APP_ACTIVITY = os.environ.get("APP_ACTIVITY", ".MainActivity")

APPIUM_SERVER_URL = os.environ.get("APPIUM_SERVER_URL", "http://127.0.0.1:4723")
DEVICE_NAME = os.environ.get("DEVICE_NAME", "Android Emulator")
# Leave PLATFORM_VERSION empty to let Appium auto-detect the connected emulator's
# Android version. Hardcoding "16" here works locally (Android 16 AVD) but
# fails in CI where api-level: 34 = Android 14, producing:
# "Unable to find an active device or emulator with OS 16" even though the
# emulator is running fine. Auto-detection removes this mismatch entirely.
PLATFORM_VERSION = os.environ.get("PLATFORM_VERSION", "")
NEW_COMMAND_TIMEOUT = int(os.environ.get("NEW_COMMAND_TIMEOUT", "240"))

# CI builds the APK with ApiConfig.baseUrl patched to point at the backend
# service running on the SAME runner -- 10.0.2.2 is the emulator's alias
# for the host loopback interface, so this reaches localhost:8000 on the
# runner without the app needing any --dart-define support (it has none;
# see lib/core/constants.dart). Kept here only for tests that need to talk
# to the backend directly (health checks, seeding assertions), not for
# driving the app UI.
BACKEND_BASE_URL = os.environ.get("BACKEND_BASE_URL", "http://127.0.0.1:8000")

# Kept in sync with backend-tests/seed_test_accounts.py -- do not edit one
# without the other.
ACCOUNTS = {
    "admin": {
        "email": "admin.qa@vulnara-qa-suite.com",
        "password": "AdminQA123!",
        "role": "admin",
    },
    "analyst": {
        "email": "analyst.qa@vulnara-qa-suite.com",
        "password": "AnalystQA123!",
        "role": "analyst",
    },
    "client": {
        "email": "client1.qa@vulnara-qa-suite.com",
        "password": "Client1QA123!",
        "role": "client",
    },
    "client2": {
        "email": "client2.qa@vulnara-qa-suite.com",
        "password": "Client2QA123!",
        "role": "client",
    },
}

# Routes from lib/router.dart, used by navigation/authorization tests that
# need every named screen. Parametrized routes (scanId/remediationId/vulnId)
# are exercised separately once a scan exists (see test_scan_lifecycle_crud.py),
# not looped over here.
STATIC_ROUTES = [
    "login",
    "dashboard",
    "scans",
    "scans/new",
    "notifications",
    "profile",
    "audit-log",
]

# Screens every authenticated role can reach via the bottom nav bar
# (VulnaraBottomNav) per docs/mobile_app_guide.md role descriptions.
NAV_SCREENS = ["scans", "dashboard", "notifications", "profile"]

HEALTHCHECK_RETRIES = int(os.environ.get("HEALTHCHECK_RETRIES", "20"))
HEALTHCHECK_DELAY_SECONDS = float(os.environ.get("HEALTHCHECK_DELAY_SECONDS", "1.5"))

IMPLICIT_WAIT_SECONDS = float(os.environ.get("IMPLICIT_WAIT_SECONDS", "12"))
