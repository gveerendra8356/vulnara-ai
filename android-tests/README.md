# Vulnara Mobile — Android Test Automation Suite

Appium + pytest test suite for `vulnara_mobile_scaffold` (the Flutter
Android app in `gveerendra8356/vulnara-ai`). Built the same way the
KrishiIQ and FitFuel suites were: analyze the actual repo and actual
installed package versions first, don't assume from memory or from a
different project's config. `final_year.md` (included) is the lessons
document this suite was built against — every numbered item in it maps to
a specific, commented decision in this codebase. Read the comments in
`utils/driver_factory.py`, `pages/bottom_nav.py`, and
`.github/workflows/android-tests.yml` for the "why," not just the "what."

## What's here

```
android-tests/
  config.py                 accounts, routes, env-driven settings
  conftest.py                Appium session fixtures, JSON report writer
  pytest.ini
  requirements.txt           versions verified against PyPI on 2026-08-15
  utils/
    driver_factory.py        builds the UiAutomator2 session
    adb_helpers.py            background/foreground, airplane mode, pm clear
    screenshot.py
  pages/                      11 page objects, one per screen
  tests/                      14 modules, 405 collected test cases
  reports/
    generate_reports.py       -> Automation_Test_Report.xlsx + HTML/MD
.github/workflows/
  android-tests.yml           4-shard CI: build APK, backend, emulator, Appium
```

405 tests collected and verified with `pytest --collect-only` (not just
claimed — see "Verification log" below). Broken down by module:

| Module | Tests | Covers |
|---|---:|---|
| `test_authentication.py` | 41 | login screen labels, valid/invalid credentials, email-format handling, repeated failures |
| `test_authorization.py` | 48 | RBAC across admin/analyst/client, unauthenticated redirects, go_router's login-page guard |
| `test_navigation.py` | 42 | bottom nav taps, back button, deep-link landing, app-bar chrome |
| `test_scan_creation_forms.py` | 41 | New Target Configuration form fields, checkbox/switch, blocked submits |
| `test_scan_lifecycle_crud.py` | 17 | scan creation → status → list, WebSocket live status, pull-to-refresh |
| `test_remediation_workflow.py` | 21 | analyst approve/reject, client execute, vulnerability detail |
| `test_notifications.py` | 9 | Alerts Hub load, empty state, repeat visits |
| `test_profile.py` | 12 | profile load, role chip, logout |
| `test_audit_log.py` | 9 | audit log reachability, table columns, scrolling |
| `test_session_management.py` | 12 | background/foreground persistence, `pm clear`, role-switch isolation |
| `test_input_validation.py` | 75 | boundary/fuzz input on every text field (SQLi-shaped strings, XSS-shaped strings, unicode, empty, very long, etc.) |
| `test_error_handling.py` | 12 | airplane-mode-induced backend-unreachable scenarios, recovery, resubmission |
| `test_accessibility.py` | 26 | content-description coverage — **includes tests documenting a real defect, see below** |
| `test_responsive_orientation.py` | 25 | portrait/landscape rendering and rotation |
| **Total** | **405** | |

## A real finding, not a testing gap: bottom nav has no accessibility labels

`lib/widgets/vulnara_bottom_nav.dart` wraps each of the 4 tab icons in an
`InkWell` with a bare `Icon(...)` — no `tooltip`, no `Semantics`, no
`semanticLabel`. Flutter's accessibility bridge exposes text and
tooltip-derived content-descriptions automatically to UiAutomator2, but
there's nothing for it to expose here. `test_accessibility.py`'s
`test_bottom_nav_icons_lack_content_description` asserts on this directly
and is **expected to fail** until the app adds labels — that's
intentional, not a bug in the suite. It'll show up as a real FAILED row
in the Excel report, the same way a genuine screen-reader accessibility
gap should.

Also documented (as an `xfail`, not silently ignored):
`remediation_approval_screen.dart`'s Approve/Execute/Reject buttons have
no client-side role guard in the widget tree — any enforcement is
happening at the backend API layer only. `test_authorization.py`'s
`test_no_client_side_role_guard_on_remediation_buttons` flags this so a
future UI-level guard being added shows up as a change worth reviewing,
not a silent pass either way.

## Why UiAutomator2, not the Flutter driver

The app has **zero `ValueKey`s** anywhere in `lib/` (`grep -rn "Key(" lib`
returns nothing). `final_year.md` documents that
`automationName: 'Flutter'` + `appium-flutter-driver` needs its own
separately-pinned npm package with a specific `peerDependencies.appium`
match, and fails every single test identically at session-start if that's
even slightly off — plus its `key_visible()`/`is_present()` helpers don't
behave the way their names suggest.

Instead, this suite runs on plain **UiAutomator2**. Flutter always builds
and exposes its semantics tree as native Android accessibility nodes the
moment an accessibility service (which UiAutomator2 counts as) attaches —
no app code changes needed. Every `Text`, button label, and `TextField`
hint in this app is reachable by `@text`/content-description with zero
instrumentation. See `pages/base_page.py`'s docstring for the exact
locator strategy, and `utils/adb_helpers.py` for how
`background_app()`/`set_network_connection()` (Flutter-driver-only
methods) were reproduced via `mobile: shell` instead.

## Running locally

**1. Build the APK with the backend URL patched:**
```bash
cd vulnara_mobile_scaffold
sed -i "s#https://[a-zA-Z0-9.-]*\.onrender\.com#http://10.0.2.2:8000#g" lib/core/constants.dart
flutter pub get
flutter build apk --debug
```

**2. Start the backend** (mirrors `backend-tests/conftest.py`'s own
ephemeral-server bootstrap — schema, then seed, then serve):
```bash
cd backend
export DATABASE_URL="sqlite+aiosqlite:///./vulnara.db"
export VULNARA_SECRET_KEY="local-dev-secret-key"
pip install -r requirements.txt
python3 apply_migration.py
PYTHONPATH="$(pwd)" python3 ../backend-tests/seed_test_accounts.py
PYTHONPATH="$(pwd)" python3 ../backend-tests/seed_fixture_data.py
python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

**3. Start an emulator** (API 34, `google_apis`, x86_64) and **Appium**:
```bash
npm install -g appium@3.6.0
appium driver install uiautomator2@8.4.0
appium --relaxed-security &
```

**4. Run the suite:**
```bash
cd android-tests
pip install -r requirements.txt
export APK_PATH=../vulnara_mobile_scaffold/build/app/outputs/flutter-apk/app-debug.apk
pytest -n 2 --reruns 2 --reruns-delay 3
python3 reports/generate_reports.py
```
Open `reports/Automation_Test_Report.xlsx` — same 6-sheet layout as the
reference report you supplied (`Executed Tests`, `Passed`, `Failed`,
`Skipped`, `Execution Metrics`, `Defect Summary`).

## CI (`.github/workflows/android-tests.yml`)

Four parallel shards, each running its own emulator + backend + Appium
stack end to end (same 4-shard pattern as `selenium-tests.yml`). Drop this
file into `.github/workflows/` at the repo root. Every `final_year.md`
lesson maps to an inline comment in the workflow at the exact step it
applies to — search the file for `final_year.md item` to jump to each
one. Summary:

1. **Secrets** — checked; nothing gitignored that the build needs (Firebase
   is initialized via `DefaultFirebaseOptions.currentPlatform` in Dart, no
   `google-services.json`/Gradle plugin involved).
2. **SDK floor** — `channel: stable` on `subosito/flutter-action`, verified
   against `pubspec.yaml`'s `>=3.3.0` floor and both Firebase packages'
   own (lower) floors.
3. **Package pins** — `appium@3.6.0` / `appium-uiautomator2-driver@8.4.0`
   checked for peer-dependency compatibility via `npm view`;
   `Appium-Python-Client==5.3.1` checked against PyPI.
4. **`AppiumConnection` timeout fix** — implemented in
   `utils/driver_factory.py`, smoke-tested against the actually-installed
   client before being written into the framework.
5. **`ubuntu-latest` + `x86_64` + explicit KVM-enable step**, not
   `macos-latest`.
6. **`android-emulator-runner`'s `script:` block** is a single `&&`-chained
   line — everything the emulator step needs (cd, env exports, pytest
   invocation) lives on one line, since separate bare lines don't share
   working directory or env in that action's DSL.
7. **Matrix test-path lists** have full `tests/...` paths baked into each
   shard's `matrix.include` entry, not a prefix applied once outside the
   matrix.
8. Backend bootstrap order (schema → seed accounts → seed fixture data →
   serve) was read directly out of `backend-tests/conftest.py` rather than
   assumed, since that's the one place in the repo that had already solved
   "how do you get this backend from an empty checkout to a servable,
   seeded state."

## Verification log

Facts below were checked against the real repo/registries during
development, not recalled from training data — consistent with
`final_year.md`'s "don't assume, check" instruction:

- `grep -rn "Key(" vulnara_mobile_scaffold/lib` → no matches (zero
  ValueKeys anywhere) → ruled out `appium-flutter-driver`.
- `lib/widgets/vulnara_bottom_nav.dart` → no `Text`, `tooltip:`, or
  `Semantics(` → confirmed bottom-nav accessibility gap.
- `AppiumConnection.__init__` signature + a live `client_config.timeout =
  240` smoke test on the actually-installed `Appium-Python-Client`
  version → confirmed the fix pattern works as written.
- `npm view appium-uiautomator2-driver peerDependencies` → confirmed
  `^3.0.0-rc.2` is satisfied by `appium@3.6.0`.
- `.gitignore` + `android/app/build.gradle.kts` → confirmed no
  `google-services.json` / `com.google.gms.google-services` plugin
  dependency exists.
- `backend-tests/conftest.py` → read directly for the schema/seed/serve
  bootstrap order and the exact `seed_fixture_data.py` requirement (no
  `POST /vulnerabilities` endpoint exists — vulnerabilities only come from
  the scan pipeline, so remediation/vulnerability-detail tests need that
  fixture data or they cleanly `pytest.skip()` instead of failing for the
  wrong reason).
- `pip index versions` / PyPI JSON API → `pytest==9.1.1` required by
  `pytest-rerunfailures==16.5`'s own `pytest!=8.2.2,>=8.2` constraint.

## Known gaps / next steps

- Several page-object locators (scan list FAB, remediation list item rows)
  use structural fallbacks (`instance(0)`, first-matching-text-node)
  because those specific widgets have no distinguishing text or
  content-description in source. They work, but are more brittle than a
  labeled element would be — a good first PR into the app itself would be
  adding `key:`/`tooltip:`/`semanticLabel` to the FAB, list item rows, and
  the bottom nav icons (the same accessibility gap this suite already
  documents as a finding).
- `test_error_handling.py`'s airplane-mode tests assume the AVD image
  supports `cmd connectivity airplane-mode` — true for all standard
  Google APIs images on API 30+, not guaranteed on every custom image.

## CI debugging log

**2026-08-16, first real CI run (405 total, 9 passed, 386 failed, 341 as
setup ERROR):** Nearly every test that touches the `driver` fixture failed
with `WebDriverException: The instrumentation process cannot be
initialized`. The only 9 passing tests were the ones with zero Appium
dependency (`test_authorization.test_remediation_action_buttons_visible_regardless_of_role`),
which was the tell — this wasn't scattered flakiness, every session-start
attempt was failing, uniformly across all 4 independent shards.

Root cause: `.github/workflows/android-tests.yml` ran
`pytest -n 2 ...` (2 parallel xdist workers) against a single emulator per
shard. UiAutomator2 can run exactly one instrumentation session per
device — two workers racing to start sessions on the same device lose
almost every time. Fixed by dropping `-n 2` (the emulator-runner step now
runs serially per shard); true parallelism would require one emulator per
worker, not a shared one. `uiautomator2ServerLaunchTimeout`/
`uiautomator2ServerInstallTimeout` were also bumped to 60s in
`utils/driver_factory.py` as cheap insurance against slow-start conditions
on a cold CI emulator, independent of the root cause above.

Also fixed: `pages/login_page.py`'s `is_loaded()` was missing the
`timeout` parameter every other page object has, which
`test_authorization.py` called with `timeout=15` — a real
`TypeError`, caught in the same run (2 occurrences, masked by the larger
failure above for everything else).

