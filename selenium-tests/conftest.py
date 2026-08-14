"""
conftest.py

- One fresh Chrome session per test (function-scoped `driver` fixture).
  Mock Mode resets its in-memory state on a real page load, so re-using a
  driver across tests would leak login state between tests unpredictably.
  A fresh driver per test costs a few seconds but buys total isolation --
  worth it at 400+ tests run across `-n auto` workers.
- `pytest_runtest_makereport` captures a screenshot for any failed test,
  named after the sanitized nodeid (utils/screenshot.py).
- The JSON execution report is written from `pytest_sessionfinish`, guarded
  to the xdist MASTER node only (`workerinput` absent). Workers must never
  race on the same output file -- this mirrors the fix documented in
  final_year.md item 3 for the sibling KrishiIQ/FitFuel suites.
- `generate_reports.py` (Excel + HTML dashboard) runs as its own step in CI,
  AFTER pytest, reading execution-results.json -- never inside a pytest hook.
"""

import json
import logging
import os
import time
import uuid

import pytest

from config import BASE_URL, CREDENTIALS, MOCK_PASSWORD, HEALTHCHECK_RETRIES, HEALTHCHECK_DELAY_SECONDS
from utils.driver_factory import new_driver
from utils.screenshot import capture
from pages.login_page import LoginPage
from pages.register_page import RegisterPage

REPORTS_DIR = os.environ.get("REPORTS_DIR", "reports")
SCREENSHOTS_DIR = os.path.join(REPORTS_DIR, "screenshots")
LOGS_DIR = os.path.join(REPORTS_DIR, "logs")

_session_results = []
_session_start = None


def pytest_addoption(parser):
    parser.addoption("--base-url", action="store", default=None, help="Override BASE_URL for this run")


@pytest.fixture(scope="session", autouse=True)
def _configure_base_url(request):
    override = request.config.getoption("--base-url")
    if override:
        os.environ["BASE_URL"] = override.rstrip("/") + "/"


@pytest.fixture(scope="session", autouse=True)
def _wait_for_server():
    """Curl-style retry health check -- the preview server may still be
    starting up when the first worker connects."""
    import urllib.request
    import urllib.error

    for attempt in range(HEALTHCHECK_RETRIES):
        try:
            urllib.request.urlopen(BASE_URL, timeout=3)
            return
        except (urllib.error.URLError, ConnectionError, OSError):
            time.sleep(HEALTHCHECK_DELAY_SECONDS)
    pytest.exit(f"Preview server at {BASE_URL} never became healthy after "
                f"{HEALTHCHECK_RETRIES * HEALTHCHECK_DELAY_SECONDS}s", returncode=2)


@pytest.fixture(scope="session", autouse=True)
def _make_dirs():
    os.makedirs(SCREENSHOTS_DIR, exist_ok=True)
    os.makedirs(LOGS_DIR, exist_ok=True)


@pytest.fixture
def test_logger(request):
    """Per-test log file, mirroring the sample report's logs/<nodeid>.console.log layout."""
    from utils.screenshot import sanitize_filename
    name = sanitize_filename(request.node.nodeid) + ".console.log"
    path = os.path.join(LOGS_DIR, name)
    logger = logging.getLogger(request.node.nodeid)
    logger.setLevel(logging.INFO)
    handler = logging.FileHandler(path)
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
    logger.addHandler(handler)
    yield logger
    logger.removeHandler(handler)
    handler.close()


@pytest.fixture
def driver(request, test_logger):
    d = new_driver()
    test_logger.info(f"Session started for {request.node.nodeid} against {BASE_URL}")
    yield d
    test_logger.info("Session ending")
    try:
        d.quit()
    except Exception:
        pass


def _unique_email(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:10]}@vulnara.dev"


def _assert_landed_on_dashboard(page: LoginPage, context: str):
    """Fail loudly and specifically HERE if login didn't complete, instead
    of silently returning an unauthenticated driver. Without this, a login
    that never navigated away from /login surfaces 10+ tests downstream as
    confusing, unrelated "couldn't find element X" failures against
    whatever page the test happens to try next -- all with the same root
    cause hidden a layer down. This fixture is the one place that actually
    knows what should have happened, so it's the right place to say so."""
    if not page.on_route(""):
        current = page.driver.current_url
        raise AssertionError(
            f"{context}: login did not land on the dashboard within the wait "
            f"window (still at {current}). This fixture failing here -- "
            f"rather than a downstream test failing on an unrelated locator "
            f"-- means the problem is the login step itself, not the page "
            f"the test actually wanted to exercise."
        )


@pytest.fixture
def login_as_analyst(driver):
    page = LoginPage(driver)
    page.open()
    page.login(CREDENTIALS["analyst"]["email"], CREDENTIALS["analyst"]["password"])
    _assert_landed_on_dashboard(page, "login_as_analyst")
    return driver


@pytest.fixture
def login_as_admin(driver):
    page = LoginPage(driver)
    page.open()
    page.login(CREDENTIALS["admin"]["email"], CREDENTIALS["admin"]["password"])
    _assert_landed_on_dashboard(page, "login_as_admin")
    return driver


@pytest.fixture
def login_as_client(driver):
    """Mock login() matches by email against seeded mockUsers; no seeded
    client account exists, so we register one live and log in with it,
    within this same browser session (mock state is per-tab / in-memory)."""
    email = _unique_email("client")
    reg = RegisterPage(driver)
    reg.open()
    reg.register(full_name="QA Client", email=email, password=MOCK_PASSWORD, role="client")
    _assert_landed_on_dashboard(reg, "login_as_client")
    return driver


@pytest.fixture(params=["analyst", "admin", "client"])
def login_as_any_role(request, driver):
    role = request.param
    if role == "client":
        email = _unique_email("client")
        reg = RegisterPage(driver)
        reg.open()
        reg.register(full_name="QA Client", email=email, password=MOCK_PASSWORD, role="client")
        _assert_landed_on_dashboard(reg, f"login_as_any_role[{role}]")
    else:
        page = LoginPage(driver)
        page.open()
        page.login(CREDENTIALS[role]["email"], CREDENTIALS[role]["password"])
        _assert_landed_on_dashboard(page, f"login_as_any_role[{role}]")
    return driver, role


# --------------------------------------------------------------------- hooks
#
# Why this is split across two hooks (and why the split matters):
#
# pytest-rerunfailures reruns a failed test by calling
# `runtestprotocol(item, ..., log=False)` internally -- which runs setup,
# call, and teardown (including the `driver` fixture's teardown, i.e.
# driver.quit()) and triggers `pytest_runtest_makereport` for each phase --
# and only AFTER that full protocol call returns does it decide whether to
# mark a report `outcome = "rerun"` and hand it to
# `item.ihook.pytest_runtest_logreport(report=report)`.
#
# That ordering means:
#   - `pytest_runtest_makereport` fires too EARLY to ever see
#     `report.outcome == "rerun"` -- by the time that hook runs, the
#     rerun-vs-final decision hasn't been made yet. A first attempt at
#     filtering on this hook (an earlier revision of this file) silently
#     recorded every rerun attempt as a normal pass/fail, doubling the
#     reported test count whenever a rerun actually fired.
#   - `pytest_runtest_logreport` fires at exactly the right time to see
#     `report.outcome == "rerun"` on superseded attempts -- but by then the
#     `driver` fixture has ALREADY been torn down for that attempt, so a
#     screenshot can no longer be captured from within it.
#
# So: screenshots/error text are captured eagerly in `makereport` (while the
# driver is still alive), keyed by nodeid and overwritten on each attempt so
# only the final attempt's data survives; the actual pass/fail/error
# bookkeeping -- where double-counting would happen -- is done in
# `logreport`, which is rerun-aware.

_meta_by_nodeid = {}
_last_screenshot = {}
_last_error = {}


def pytest_collection_modifyitems(session, config, items):
    for item in items:
        _meta_by_nodeid[item.nodeid] = {
            "test_id": item.name.split("[")[0],
            "full_name": item.name,
            "module": item.nodeid.split("::")[0].split("/")[-1].replace("test_", "").replace(".py", ""),
            "markers": [m.name for m in item.iter_markers()],
        }


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    outcome = yield
    report = outcome.get_result()
    setattr(item, f"rep_{report.when}", report)

    if report.failed and report.when in ("setup", "call"):
        driver = item.funcargs.get("driver")
        if driver is not None:
            _last_screenshot[report.nodeid] = capture(driver, item.nodeid, SCREENSHOTS_DIR)
        _last_error[report.nodeid] = str(report.longrepr)


def pytest_runtest_logreport(report):
    # Superseded attempts (about to be retried) are marked "rerun" -- skip
    # them so a retried test is recorded exactly once, using its final
    # outcome. See the module-level comment above for why this can't be
    # done in pytest_runtest_makereport.
    if getattr(report, "outcome", None) == "rerun":
        return

    meta = _meta_by_nodeid.get(report.nodeid, {
        "test_id": report.nodeid.split("::")[-1].split("[")[0],
        "full_name": report.nodeid.split("::")[-1],
        "module": report.nodeid.split("::")[0].split("/")[-1].replace("test_", "").replace(".py", ""),
        "markers": [],
    })

    if report.when == "call":
        status = "PASSED" if report.passed else ("FAILED" if report.failed else "SKIPPED")
        _session_results.append({
            "nodeid": report.nodeid,
            "test_id": meta["test_id"],
            "full_name": meta["full_name"],
            "module": meta["module"],
            "markers": meta["markers"],
            "status": status,
            "duration": round(report.duration, 3),
            "screenshot": _last_screenshot.get(report.nodeid) if report.failed else None,
            "error": _last_error.get(report.nodeid) if report.failed else None,
        })
    elif report.when == "setup" and report.failed:
        _session_results.append({
            "nodeid": report.nodeid,
            "test_id": meta["test_id"],
            "full_name": meta["full_name"],
            "module": meta["module"],
            "markers": meta["markers"],
            "status": "ERROR",
            "duration": round(report.duration, 3),
            "screenshot": _last_screenshot.get(report.nodeid),
            "error": _last_error.get(report.nodeid, str(report.longrepr)),
        })


def pytest_sessionstart(session):
    global _session_start
    _session_start = time.time()


def pytest_sessionfinish(session, exitstatus):
    # xdist workers must never write the shared file -- only the master
    # (workerinput absent on master) or a non-xdist run does.
    if hasattr(session.config, "workerinput"):
        # Write a per-worker partial file instead; ci_generate_reports merges them.
        worker_id = session.config.workerinput["workerid"]
        os.makedirs(REPORTS_DIR, exist_ok=True)
        partial_path = os.path.join(REPORTS_DIR, f"execution-results-{worker_id}.json")
        with open(partial_path, "w") as f:
            json.dump(_session_results, f, indent=2)
        return

    os.makedirs(REPORTS_DIR, exist_ok=True)

    # Merge any per-worker partials (present when this run used pytest-xdist)
    merged = list(_session_results)
    if os.path.isdir(REPORTS_DIR):
        for fname in os.listdir(REPORTS_DIR):
            if fname.startswith("execution-results-gw") and fname.endswith(".json"):
                try:
                    with open(os.path.join(REPORTS_DIR, fname)) as f:
                        merged.extend(json.load(f))
                    os.remove(os.path.join(REPORTS_DIR, fname))
                except Exception:
                    pass

    passed = sum(1 for r in merged if r["status"] == "PASSED")
    failed = sum(1 for r in merged if r["status"] == "FAILED")
    skipped = sum(1 for r in merged if r["status"] == "SKIPPED")
    errors = sum(1 for r in merged if r["status"] == "ERROR")
    total = len(merged)
    pass_rate = round((passed / total) * 100, 2) if total else 0.0

    payload = {
        "run_at": time.strftime("%Y-%m-%dT%H:%M:%S+00:00", time.gmtime()),
        "base_url": BASE_URL,
        "duration_seconds": round(time.time() - _session_start, 2) if _session_start else None,
        "total": total,
        "passed": passed,
        "failed": failed,
        "skipped": skipped,
        "errors": errors,
        "pass_rate": pass_rate,
        "results": merged,
    }
    with open(os.path.join(REPORTS_DIR, "execution-results.json"), "w") as f:
        json.dump(payload, f, indent=2)
