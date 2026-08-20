"""
utils/adb_helpers.py

driver.background_app(seconds) and driver.set_network_connection(...) are
part of appium-flutter-driver's MobileCommand surface, not UiAutomator2's --
final_year.md documents this exact incompatibility from the KrishiIQ suite
(automationName: 'Flutter' was needed for background_app()/
set_network_connection() to exist at all, which then dragged in every other
appium-flutter-driver problem). Since this suite intentionally runs on
UiAutomator2 (see driver_factory.py), the same *behaviors* are reproduced
here directly via `mobile: shell`, which UiAutomator2 exposes as a session
execute_script extension wrapping `adb shell` -- no separate adb binary/
subprocess management needed, and it works identically on a CI runner or a
local emulator since Appium already owns the device connection.
"""


def send_to_background(driver, seconds: int = 3):
    """Equivalent of driver.background_app(seconds) on UiAutomator2."""
    driver.execute_script("mobile: shell", {
        "command": "input", "args": ["keyevent", "KEYCODE_HOME"],
    })
    import time
    time.sleep(seconds)
    bring_to_foreground(driver)


def bring_to_foreground(driver):
    import config
    import time
    driver.execute_script("mobile: shell", {
        "command": "monkey",
        "args": ["-p", config.APP_PACKAGE, "-c", "android.intent.category.LAUNCHER", "1"],
    })
    # monkey is fire-and-forget -- give the process time to start before
    # the caller tries to interact with any UI elements.
    time.sleep(1)


def set_airplane_mode(driver, enabled: bool):
    """Equivalent of driver.set_network_connection(AIRPLANE_MODE) on
    UiAutomator2. Requires the emulator's airplane-mode broadcast receiver,
    present on all standard AVD images."""
    state = "enable" if enabled else "disable"
    driver.execute_script("mobile: shell", {
        "command": "cmd", "args": ["connectivity", "airplane-mode", state],
    })


def force_stop_app(driver):
    import config
    driver.execute_script("mobile: shell", {
        "command": "am", "args": ["force-stop", config.APP_PACKAGE],
    })


def clear_app_data(driver):
    """Resets the app's auth state (flutter_secure_storage/shared prefs)
    without wiping the UiAutomator2 instrumentation server state.

    IMPORTANT: `pm clear <package>` wipes ALL package data including the
    UiAutomator2 server APK's own cached state since it runs in the app's
    process context. This causes 'instrumentation process cannot be
    initialized' on the very next new_driver() call. Instead, we force-stop
    the app (which clears in-memory Riverpod auth state) and clear only the
    shared_prefs directory (where flutter_secure_storage writes the JWT token)
    via a targeted `rm -rf` -- leaving UiAutomator2's data untouched.

    NOTE: Do NOT pass multiple paths to a single `sh -c 'rm -rf a b'`
    invocation via mobile:shell. Appium wraps the -c argument in single
    quotes when constructing the adb shell command line, which causes
    Android's /system/bin/sh to mis-parse a multi-argument rm call and
    report "rm: Needs 1 argument". Issue two separate rm calls instead --
    one per directory -- to avoid this quoting ambiguity entirely.
    """
    import config
    # Force-stop clears all in-memory state including Riverpod providers
    driver.execute_script("mobile: shell", {
        "command": "am", "args": ["force-stop", config.APP_PACKAGE],
    })
    # Clear the app's shared_prefs (flutter_secure_storage JWT location)
    # without touching io.appium.uiautomator2.server data.
    # Two separate rm calls -- one per path -- to avoid the multi-argument
    # quoting issue described above.
    driver.execute_script("mobile: shell", {
        "command": "rm",
        "args": ["-rf", f"/data/data/{config.APP_PACKAGE}/shared_prefs"],
    })
    driver.execute_script("mobile: shell", {
        "command": "rm",
        "args": ["-rf", f"/data/data/{config.APP_PACKAGE}/files"],
    })


def rotate_device(driver, orientation: str):
    """orientation: 'PORTRAIT' or 'LANDSCAPE'. UiAutomator2 supports
    driver.orientation natively (unlike background_app/network_connection),
    so this is a thin wrapper kept here just for a single import surface
    across responsive tests."""
    driver.orientation = orientation
