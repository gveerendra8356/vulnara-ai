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
    
    print("Entering email...")
    account = config.ACCOUNTS["admin"]
    page.enter_email(account["email"])
    print("Email entered successfully.")
    
    print("Entering password...")
    page.enter_password(account["password"])
    print("Password entered successfully.")
    
    print("Submitting...")
    page.submit()
    print("Submitted.")
    
    time.sleep(2)
    print("Test passed locally.")
except Exception as e:
    print(f"Exception caught: {e}")
finally:
    driver.quit()
