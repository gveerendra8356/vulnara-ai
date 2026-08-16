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
    driver.execute_script("mobile: shell", {
        "command": "monkey",
        "args": ["-p", config.APP_PACKAGE, "-c", "android.intent.category.LAUNCHER", "1"],
    })


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
    """Wipes flutter_secure_storage/shared prefs -- used by session-management
    tests that need a truly cold, logged-out app state without a full
    reinstall (no_reset stays False on the driver capabilities; this is for
    mid-test resets)."""
    import config
    driver.execute_script("mobile: shell", {
        "command": "pm", "args": ["clear", config.APP_PACKAGE],
    })


def rotate_device(driver, orientation: str):
    """orientation: 'PORTRAIT' or 'LANDSCAPE'. UiAutomator2 supports
    driver.orientation natively (unlike background_app/network_connection),
    so this is a thin wrapper kept here just for a single import surface
    across responsive tests."""
    driver.orientation = orientation
