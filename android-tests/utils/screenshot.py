"""utils/screenshot.py -- mirrors selenium-tests/utils/screenshot.py so the
two suites' CI artifacts look and behave the same way."""

import os
import re


def _sanitize(nodeid: str) -> str:
    name = re.sub(r"[^A-Za-z0-9_.\[\]-]+", "_", nodeid)
    return name[:180]  # keep filenames well under ext4/NTFS limits


def capture(driver, nodeid: str, screenshots_dir: str) -> str | None:
    os.makedirs(screenshots_dir, exist_ok=True)
    path = os.path.join(screenshots_dir, f"{_sanitize(nodeid)}.png")
    try:
        driver.save_screenshot(path)
        return path
    except Exception:
        return None
