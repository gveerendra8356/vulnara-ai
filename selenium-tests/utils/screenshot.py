"""
Screenshot capture on failure.

GitHub Actions artifact upload silently drops files whose names contain
/ \\ : * ? " < > | -- and pytest nodeids (which we use as the filename) are
full of those characters once parametrize IDs are involved, e.g.:
    tests/test_authorization.py::TestX::test_y[admin@vulnara.dev]
Sanitize before ever touching the filesystem.
"""

import os
import re

INVALID_CHARS = re.compile(r'[\\/*?:"<>|]')


def sanitize_filename(nodeid: str) -> str:
    name = nodeid.replace("::", "__").replace(" ", "_")
    name = INVALID_CHARS.sub("_", name)
    return name[:200]  # keep filesystem-safe length


def capture(driver, nodeid: str, out_dir: str) -> str | None:
    os.makedirs(out_dir, exist_ok=True)
    filename = sanitize_filename(nodeid) + ".png"
    path = os.path.join(out_dir, filename)
    try:
        driver.save_screenshot(path)
        return path
    except Exception:
        return None
