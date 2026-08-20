"""
conftest.py

Adapted line-for-line from ../selenium-tests/conftest.py's xdist/rerun
report-collection pattern (same double-counting bug it documents, same
fix), swapped from a Selenium `driver` to an Appium `driver`:

- One fresh Appium session per test (function-scoped `driver` fixture).
  The app's Riverpod auth state is process-local, not reset by navigation
  alone the way a page reload resets JS state -- a fresh install-free
  session with `pm clear` (see utils/adb_helpers.clear_app_data, used by
  the login fixtures below) is what actually guarantees isolation here.
- `pytest_runtest_makereport` captures a screenshot for any failed test.
- The JSON execution report is written from `pytest_sessionfinish`, guarded
  to the xdist CONTROLLER only, for the exact reason documented in
  selenium-tests/conftest.py: an earlier, unguarded version of this same
  pattern double-counted every result once via the worker and once via the
  controller's relayed copy.
- `reports/generate_reports.py` runs as its own step in CI, after pytest.
"""

import json
import logging
import os
import time
import urllib.error
import urllib.request
import uuid

import pytest

import config
from utils.adb_helpers import bring_to_foreground, clear_app_data, force_stop_app
from utils.driver_factory import new_driver
from utils.screenshot import capture
from pages.login_page import LoginPage

REPORTS_DIR = os.environ.get("REPORTS_DIR", "reports")
SCREENSHOTS_DIR = os.path.join(REPORTS_DIR, "screenshots")
LOGS_DIR = os.path.join(REPORTS_DIR, "logs")

_session_results = []
_session_start = None
_am_xdist_controller = False


def pytest_addoption(parser):
    parser.addoption("--backend-url", action="store", default=None,
                      help="Override BACKEND_BASE_URL for this run")


def pytest_configure(config):  # noqa: F811 -- pytest hookspec requires this exact
    # parameter name; shadows the `config` module imported above within this
    # function's scope only (nothing else in this file needs the module
    # inside pytest_configure).
    global _am_xdist_controller
    is_worker = hasattr(config, "workerinput")
    numprocesses = getattr(config.option, "numprocesses", None)
    _am_xdist_controller = (not is_worker) and bool(numprocesses)


@pytest.fixture(scope="session", autouse=True)
def _configure_backend_url(request):
    override = request.config.getoption("--backend-url")
    if override:
        os.environ["BACKEND_BASE_URL"] = override.rstrip("/")


@pytest.fixture(scope="session", autouse=True)
def _wait_for_backend():
    """The backend (and its /health endpoint) must be up and seeded before
    the first login attempt -- see .github/workflows/android-tests.yml's
    'Wait for backend health' step, which does the same check before the
    emulator job even starts installing the APK. This fixture is a second,
    cheap safety net for local runs where the two aren't sequenced by CI."""
    url = f"{config.BACKEND_BASE_URL}/health"
    for _ in range(config.HEALTHCHECK_RETRIES):
        try:
            urllib.request.urlopen(url, timeout=3)
            return
        except (urllib.error.URLError, ConnectionError, OSError):
            time.sleep(config.HEALTHCHECK_DELAY_SECONDS)
    pytest.exit(
        f"Backend at {url} never became healthy after "
        f"{config.HEALTHCHECK_RETRIES * config.HEALTHCHECK_DELAY_SECONDS}s",
        returncode=2,
    )


@pytest.fixture(scope="session", autouse=True)
def _make_dirs():
    os.makedirs(SCREENSHOTS_DIR, exist_ok=True)
    os.makedirs(LOGS_DIR, exist_ok=True)


@pytest.fixture
def test_logger(request):
    from utils.screenshot import _sanitize
    name = _sanitize(request.node.nodeid) + ".console.log"
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
    test_logger.info(f"Appium session started for {request.node.nodeid}")
    # With no_reset=True (see driver_factory.py), Appium no longer calls
    # `pm clear` during session startup. Tests using the plain `driver`
    # fixture expect an unauthenticated cold-start state -- no stored JWT.
    # We reset the app explicitly here (force-stop + clear auth data +
    # relaunch) so that any token left over from a previous test in the
    # same session pool doesn't bleed into this test's initial app state.
    clear_app_data(d)
    force_stop_app(d)
    bring_to_foreground(d)
    import time
    time.sleep(4)  # wait for cold-start + TalkBack semantics tree
    yield d
    test_logger.info("Session ending")
    try:
        d.quit()
    except Exception:
        pass


def _assert_landed_past_login(page: LoginPage, context: str):
    """Fail loudly and specifically HERE if login didn't complete -- mirrors
    selenium-tests/conftest.py's _assert_landed_on_dashboard rationale
    exactly: an unnoticed failed login otherwise surfaces as 10+ unrelated
    "couldn't find element" failures on whatever screen each test tries
    next, all hiding the same root cause."""
    if not page.wait_gone(page.by_text("INITIALIZE SESSION"), timeout=15):
        raise AssertionError(
            f"{context}: login did not navigate away from the login screen "
            f"within the wait window. This fixture failing here -- rather "
            f"than a downstream test failing on an unrelated locator -- "
            f"means the problem is the login step itself."
        )


def _login_fixture_factory(role: str):
    @pytest.fixture
    def _fixture(driver):
        # The `driver` fixture already performed clear_app_data + force_stop +
        # bring_to_foreground + a 4s sleep before yielding, so the app is in a
        # clean, unauthenticated cold-start state by the time we get here.
        # We just need to do the login.
        page = LoginPage(driver)
        assert page.is_loaded(), f"login_as_{role}: login screen never appeared"
        account = config.ACCOUNTS[role]
        page.login(account["email"], account["password"])
        _assert_landed_past_login(page, f"login_as_{role}")
        return driver
    return _fixture


login_as_admin = _login_fixture_factory("admin")
login_as_analyst = _login_fixture_factory("analyst")
login_as_client = _login_fixture_factory("client")


@pytest.fixture(params=["admin", "analyst", "client"])
def login_as_any_role(request, driver):
    role = request.param
    # The `driver` fixture already performed clear_app_data + force_stop +
    # bring_to_foreground + a 4s sleep before yielding, so the app is in a
    # clean, unauthenticated cold-start state by the time we get here.
    page = LoginPage(driver)
    assert page.is_loaded(), f"login_as_any_role[{role}]: login screen never appeared"
    account = config.ACCOUNTS[role]
    page.login(account["email"], account["password"])
    _assert_landed_past_login(page, f"login_as_any_role[{role}]")
    return driver, role


# --------------------------------------------------------------------- hooks
# See selenium-tests/conftest.py's module-level comment above the identical
# block for the full rationale (pytest-rerunfailures timing, xdist relay
# double-counting). Reproduced here unchanged because this suite hits the
# exact same two hooks for the exact same reasons.

_meta_by_nodeid = {}
_last_screenshot = {}
_last_error = {}


def pytest_collection_modifyitems(session, config, items):  # noqa: F811
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
        drv = item.funcargs.get("driver")
        if drv is not None:
            _last_screenshot[report.nodeid] = capture(drv, item.nodeid, SCREENSHOTS_DIR)
        _last_error[report.nodeid] = str(report.longrepr)


def pytest_runtest_logreport(report):
    if _am_xdist_controller:
        return
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
    if hasattr(session.config, "workerinput"):
        worker_id = session.config.workerinput["workerid"]
        os.makedirs(REPORTS_DIR, exist_ok=True)
        partial_path = os.path.join(REPORTS_DIR, f"execution-results-{worker_id}.json")
        with open(partial_path, "w") as f:
            json.dump(_session_results, f, indent=2)
        return

    os.makedirs(REPORTS_DIR, exist_ok=True)

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
        "base_url": f"android emulator @ {config.APPIUM_SERVER_URL}",
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