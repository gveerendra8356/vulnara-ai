"""
utils/driver_factory.py

Builds one Appium session per test (function-scoped, see conftest.py --
same isolation rationale as selenium-tests/conftest.py: re-using a driver
across tests would leak login/session state between tests unpredictably).

Automation engine: UiAutomator2, NOT the Flutter driver.
------------------------------------------------------
final_year.md (the KrishiIQ/FitFuel lessons doc this suite was built
against) documents that automationName: 'Flutter' + appium-flutter-driver
is fragile in CI: it needs its own separately-pinned npm driver package,
fails every single test identically at session-start if that package or
its Appium-server-version peer dependency is even slightly off, and its
key_visible()/is_present() helpers do not behave the way their names
suggest. vulnara_mobile_scaffold's widgets also don't declare any
ValueKeys (grep for "Key(" under lib/ returns nothing), which
appium-flutter-driver's finders depend on -- so that driver would need
every screen re-instrumented with keys before a single test could run.

UiAutomator2 avoids all of that: Flutter always builds and exposes an
Android accessibility (semantics) tree once an accessibility service --
which UiAutomator2/instrumentation counts as -- attaches, so every Text,
button label, and TextField hint in this app is reachable as a normal
Android accessibility node by text/content-desc, with zero app code
changes. See pages/base_page.py for the resulting locator strategy.
"""

import logging

from appium import webdriver
from appium.options.android import UiAutomator2Options
from appium.webdriver.appium_connection import AppiumConnection

import config

logger = logging.getLogger(__name__)


def new_driver():
    options = UiAutomator2Options()
    options.platform_name = "Android"
    options.automation_name = "UiAutomator2"
    options.device_name = config.DEVICE_NAME
    options.platform_version = config.PLATFORM_VERSION
    options.app = config.APK_PATH
    options.app_package = config.APP_PACKAGE
    options.app_activity = config.APP_ACTIVITY
    options.new_command_timeout = config.NEW_COMMAND_TIMEOUT
    options.no_reset = False
    options.full_reset = False
    options.auto_grant_permissions = True
    # Flutter apps commonly still report as "loading" right after the first
    # frame; disabling the wait-for-idle heuristic avoids UiAutomator2
    # silently stalling on Flutter's continuous animation ticker.
    options.set_capability("waitForIdleTimeout", 0)
    options.set_capability("disableWindowAnimation", True)
    # Defensive addition after a real CI run surfaced "instrumentation
    # process cannot be initialized" failures (root cause: `pytest -n 2`
    # racing two sessions onto one emulator -- fixed in the CI workflow,
    # not here). Bumping this is cheap insurance against the same class of
    # error under any future genuine slow-start condition (cold emulator,
    # first-launch APK install), since the default 20s launch timeout has
    # little margin on a freshly-booted CI emulator.
    options.set_capability("uiautomator2ServerLaunchTimeout", 60000)
    options.set_capability("uiautomator2ServerInstallTimeout", 60000)

    # --- final_year.md item 4: AppiumConnection timeout wiring ---
    # A bare AppiumConnection.set_timeout(N) classmethod call at import time
    # throws AttributeError: no attribute '_client_config' on
    # Appium-Python-Client 3.x+, and AppiumClientConfig isn't importable
    # either. The working pattern (verified against the pinned client
    # version in requirements.txt -- see README.md "Version verification
    # log"): construct an AppiumConnection instance, set
    # .client_config.timeout directly on THAT instance, then pass the
    # instance as command_executor= to webdriver.Remote.
    connection = AppiumConnection(config.APPIUM_SERVER_URL)
    connection.client_config.timeout = config.NEW_COMMAND_TIMEOUT

    driver = webdriver.Remote(command_executor=connection, options=options)
    driver.implicitly_wait(config.IMPLICIT_WAIT_SECONDS)
    return driver
