import logging
import time

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
    options.set_capability("uiautomator2ServerLaunchTimeout", 120000)
    options.set_capability("uiautomator2ServerInstallTimeout", 120000)

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

