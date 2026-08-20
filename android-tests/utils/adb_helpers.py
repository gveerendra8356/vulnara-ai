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

    PERMISSION NOTE: On Android API 34 with SELinux enforcing, the ADB
    shell user (uid=2000) cannot write to /data/data/<package>/ even with
    `-rf`. We use `run-as <package>` to re-execute rm as the app's own
    UID -- this is only available on debuggable (debug) builds, which is
    exactly what CI produces. Each path is deleted in a separate call
    because mobile:shell's args array maps 1-to-1 onto execv() tokens, so
    passing two paths to a single rm call would need sh -c, which adds the
    shell-quoting ambiguity we want to avoid entirely.

    The calls are wrapped in try/except so a fresh emulator (where the
    directories have never been created yet) doesn't crash the fixture.
    """
    import config
    # Force-stop clears all in-memory state including Riverpod providers
    driver.execute_script("mobile: shell", {
        "command": "am", "args": ["force-stop", config.APP_PACKAGE],
    })
    # Delete persistent JWT storage as the app's own UID via run-as, so
    # SELinux enforcement on API 34 doesn't block the deletion.
    for subdir in ("shared_prefs", "files"):
        try:
            driver.execute_script("mobile: shell", {
                "command": "run-as",
                "args": [
                    config.APP_PACKAGE,
                    "rm", "-rf",
                    f"/data/data/{config.APP_PACKAGE}/{subdir}",
                ],
            })
        except Exception:
            # Directory may not exist yet on a freshly-booted emulator
            # (first test run before the app has ever written any data).
            # Silently continue -- force-stop above already cleared
            # all in-memory auth state.
            pass


def rotate_device(driver, orientation: str):
    """orientation: 'PORTRAIT' or 'LANDSCAPE'. UiAutomator2 supports
    driver.orientation natively (unlike background_app/network_connection),
    so this is a thin wrapper kept here just for a single import surface
    across responsive tests."""
    driver.orientation = orientation
