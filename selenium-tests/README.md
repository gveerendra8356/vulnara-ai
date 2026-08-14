# Vulnara — Selenium Web Test Suite (GitHub-Actions-only)

A 420-test Selenium suite for `vulnara-web` (the React/Vite frontend in
`gveerendra8356/vulnara-ai`), built to run **entirely inside GitHub Actions**
— nothing here needs to run on your machine.

```
selenium-tests/
  config.py                 # routes, seeded credentials/IDs, timeouts
  conftest.py                # driver fixture, auth fixtures, JSON report writer
  pytest.ini
  requirements.txt
  pages/                     # Page Objects, one per route
  tests/                     # 12 test files, 420 tests total
  utils/                     # driver factory, screenshot capture
  reports/
    generate_reports.py      # builds the .xlsx / .html / .md reports
.github/workflows/
  selenium-tests.yml         # the whole CI pipeline
```

## How to install this into your repo

1. Copy `selenium-tests/` and `.github/workflows/selenium-tests.yml` into
   the root of `vulnara-ai` (next to `vulnara-web/`, `backend/`, `docs/`).
2. Commit and push. The workflow runs automatically on every push/PR to
   `main`, and can also be triggered manually from the **Actions** tab
   ("Run workflow").
3. Download the `vulnara-selenium-report` artifact from the finished run —
   that's your `Automation_Test_Report.xlsx`, `dashboard.html`,
   `execution-report.html`, and `summary.md`, in the same layout as your
   sample report.

Nothing needs installing locally. If you *do* want to sanity-check a test
file's syntax on your own machine first, `pip install -r
selenium-tests/requirements.txt && pytest --collect-only -q` from inside
`selenium-tests/` doesn't need Chrome or a running server — but this is
optional, not required for CI to work.

## Why the app is built with Mock Mode ON, served by `vite preview`/`serve` — not tested against GitHub Pages

This wasn't assumed — it came out of reading the actual source:

- `vulnara-web` has a built-in **Mock Mode** (`VITE_USE_MOCK`), which the
  repo's own `docs/testing_guide.md` describes as what makes the app "fully
  clickable" without a real backend. `.env.production` ships with
  `VITE_USE_MOCK=false` for the real deployed site.
- The deployed GitHub Pages site talks to a free-tier Render backend that
  cold-starts and can take 30–50s or 502 on first request — that would make
  CI flaky for reasons that have nothing to do with the web app.
- So the workflow builds the app with `VITE_USE_MOCK=true` **overriding**
  `.env.production`, then serves the static build from *inside* the GitHub
  Actions runner (`http://127.0.0.1:4173/vulnara-ai/`) — no external network
  calls, fully deterministic, fast. This mirrors the base-URL pattern already
  visible in your own sample `Automation_Test_Report.xlsx`
  (`http://localhost:4173/fitfuel-final/`).
- Every seeded id/credential the tests use (`scan-1001`, `vuln-2001`,
  `rem-4001`, `analyst@vulnara.dev`, `admin@vulnara.dev`, etc.) comes
  directly from `vulnara-web/src/lib/mockData.js` — nothing is invented.

## What's actually being tested (and two real findings along the way)

Reading the source turned up two genuine, verifiable behaviors baked into
the app that the tests treat as **facts to assert on**, not as test bugs:

1. **Mock Mode has no persisted session.** `mockApi.login()` keeps the
   session in an in-memory JS variable only — it never writes to
   `localStorage` (only the real API transport does). So reloading any
   protected page in Mock Mode always bounces back to `/login`. The
   `test_session_management.py` suite asserts this directly, with the
   reasoning written into the file's docstring.
2. **The sidebar nav has no mobile fallback.** It's `className="hidden
   md:flex"` with no hamburger/drawer anywhere in the component tree — below
   768px wide, the entire primary navigation is inaccessible. Rather than
   silently pass or hand-wave this, `test_responsive.py` has a
   `TestMobileViewportKnownGap` class that documents it as real, current
   behavior.

## Test breakdown (420 tests across 12 files)

| File | Tests | Covers |
|---|---:|---|
| `test_authentication.py` | 56 | Login/register structure, native email validation, logout, Mock Mode token behavior |
| `test_authorization.py` | 47 | ProtectedRoute redirects, admin-only gating, role-based nav visibility |
| `test_navigation.py` | 34 | Sidebar presence, active-state highlighting, click-through nav |
| `test_ui_validation.py` | 56 | Page chrome, titles, console errors, empty/loading states |
| `test_forms.py` | 36 | Field mechanics across every form in the app |
| `test_crud_operations.py` | 40 | Create/read scans, remediation approve/reject/execute, admin config edits |
| `test_input_validation.py` | 40 | Boundary values, XSS/SQLi-shaped input, the 10-char justification minimum |
| `test_error_handling.py` | 22 | 404 page + recovery, nonexistent seeded IDs, blocked-submission recovery |
| `test_session_management.py` | 19 | Reload behavior, fake-token handling, multi-tab isolation |
| `test_search_filter.py` | 19 | Scans list search + status filters, header search bar's real (unwired) behavior |
| `test_accessibility.py` | 26 | Alt text, heading structure, keyboard nav, ARIA labels |
| `test_responsive.py` | 25 | Desktop/tablet/mobile viewports, the sidebar mobile gap above |

Run `pytest --collect-only -q` from `selenium-tests/` to see the exact list
and re-verify the count any time.

## CI pipeline (`.github/workflows/selenium-tests.yml`)

```
build-web-app        → npm ci, VITE_USE_MOCK=true npm run build, upload dist/
selenium-tests (×4)  → download dist/, serve it locally, run 1/4 of the
                        suite per shard (pytest -n auto inside each shard,
                        pytest-split across shards), upload each shard's
                        results
merge-and-report      → merge all 4 shards' JSON, run generate_reports.py,
                        post summary.md to the job summary, upload the final
                        Automation_Test_Report.xlsx / dashboard.html /
                        execution-report.html, enforce the pass-rate gate
```

- **Parallelism:** 4 GitHub Actions shards × `pytest -n auto` inside each
  shard = fast wall-clock time even at 420 tests.
- **Flake tolerance:** `--reruns 1 --reruns-delay 2` — a test that fails
  once and passes on rerun is marked `RERUN` in the Excel report, same as
  your sample.
- **Quality gate:** controlled by `GATE_THRESHOLD` (workflow input, default
  `70`). The job fails if the merged pass rate falls below it, after all
  artifacts are already uploaded — so you always get the report even on a
  failing run. Raise this once the suite has had a few runs against a
  stable build.
- **Screenshots:** any failed test gets a screenshot saved under
  `reports/screenshots/`, named after its sanitized pytest nodeid, and
  shipped in the final artifact.

## Viewing results

Every run, go to **Actions → (the run) → Artifacts → `vulnara-selenium-report`**:

- `Automation_Test_Report.xlsx` — same 6-sheet layout as your sample
  (`Executed Tests`, `Passed`, `Failed`, `Skipped`, `Execution Metrics`,
  `Defect Summary`, with the same severity-by-module mapping).
- `dashboard.html` — open directly in a browser for a pass-rate bar + a
  per-module breakdown chart.
- `execution-report.html` — full sortable-by-eye table of every test.
- `summary.md` — also posted straight into the GitHub Actions job summary
  page, no download needed.
- `screenshots/`, `logs/` — per-test failure screenshots and console logs.

## Local sanity-check (optional, not required)

```bash
cd selenium-tests
pip install -r requirements.txt
pytest --collect-only -q        # verify all 420 collect with zero import errors
```

Actually running the suite locally needs Chrome + a running preview server,
which is exactly what the CI workflow sets up for you — that's the point of
this being GitHub-Actions-only.
