import time
import os
import subprocess
from appium.webdriver.common.appiumby import AppiumBy
from utils.driver_factory import new_driver
from pages.login_page import LoginPage
import config

print("Starting debug_crash.py...")

# Clear old logcat
subprocess.run(["adb", "logcat", "-c"])

driver = new_driver()
try:
    page = LoginPage(driver)
    assert page.is_loaded()
    
    account = config.ACCOUNTS["admin"]
    page.enter_email(account["email"])
    page.enter_password(account["password"])
    page.submit()
    
    print("Submitted, waiting 5s for navigation...")
    time.sleep(5)
    
    print("Dumping logcat...")
    subprocess.run("adb logcat -d > crash_logcat.txt", shell=True)
    
    # Try to see if we left the screen
    left = page.wait_gone(page.by_text("INITIALIZE SESSION"), timeout=5)
    print(f"Left login screen? {left}")
    
except Exception as e:
    print(f"Exception: {e}")
    subprocess.run("adb logcat -d > crash_logcat.txt", shell=True)
finally:
    try:
        driver.quit()
    except:
        pass
    print("Done.")
