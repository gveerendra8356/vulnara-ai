"""
diag_dump_tree.py - dumps the UiAutomator2 accessibility tree to file.
Run while emulator + Appium are already up.
Usage:  python diag_dump_tree.py
"""
import sys, time, re
sys.path.insert(0, ".")

from appium import webdriver
from appium.options.android import UiAutomator2Options
from appium.webdriver.appium_connection import AppiumConnection
import config

options = UiAutomator2Options()
options.platform_name = "Android"
options.automation_name = "UiAutomator2"
options.device_name = config.DEVICE_NAME
options.platform_version = config.PLATFORM_VERSION
options.app = config.APK_PATH
options.app_package = config.APP_PACKAGE
options.app_activity = config.APP_ACTIVITY
options.no_reset = False
options.full_reset = False
options.auto_grant_permissions = True
options.set_capability("waitForIdleTimeout", 0)
options.set_capability("disableWindowAnimation", True)
options.set_capability("uiautomator2ServerLaunchTimeout", 60000)
options.set_capability("uiautomator2ServerInstallTimeout", 60000)
options.set_capability("ensureSemanticsEnabled", True)
options.set_capability("allowInvisibleElements", True)

print("Connecting to Appium...")
conn = AppiumConnection(config.APPIUM_SERVER_URL)
conn.client_config.timeout = config.NEW_COMMAND_TIMEOUT
driver = webdriver.Remote(command_executor=conn, options=options)
driver.implicitly_wait(0)

print("Session started. Waiting 15s for app + semantics tree to load...")
time.sleep(15)

print("Dumping page source...")
src = driver.page_source

# Save full XML
out_path = "reports/page_source_dump.xml"
with open(out_path, "w", encoding="utf-8") as f:
    f.write(src)
print(f"Full page source saved to: {out_path}")

# Extract & print all unique text= and content-desc= values
texts = sorted(set(re.findall(r'text="([^"]+)"', src)))
descs = sorted(set(re.findall(r'content-desc="([^"]+)"', src)))
classes = sorted(set(re.findall(r'class="([^"]+)"', src)))

print(f"\n=== text= values ({len(texts)}) ===")
for t in texts:
    print(f"  '{t}'")

print(f"\n=== content-desc= values ({len(descs)}) ===")
for d in descs:
    print(f"  '{d}'")

print(f"\n=== class names ({len(classes)}) ===")
for c in classes[:20]:
    print(f"  {c}")

print(f"\nTotal XML size: {len(src)} chars")
driver.quit()
print("Done.")
