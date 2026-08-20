import time
from appium.webdriver.common.appiumby import AppiumBy
from utils.driver_factory import new_driver
from pages.login_page import LoginPage
import config

print("Connecting...")
driver = new_driver()
try:
    page = LoginPage(driver)
    print("Waiting for page load...")
    assert page.is_loaded()
    
    account = config.ACCOUNTS["admin"]
    page.enter_email(account["email"])
    page.enter_password(account["password"])
    page.submit()
    
    print("Submitted. Waiting 5s...")
    time.sleep(5)
    
    error = page.error_text()
    if error:
        print(f"Error shown on screen: {error}")
    else:
        print("No error text found.")
        
    left = page.wait_gone(page.by_text("INITIALIZE SESSION"), timeout=2)
    print(f"Left login screen? {left}")

except Exception as e:
    print(f"Exception caught: {e}")
finally:
    driver.quit()
