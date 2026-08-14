"""
Remediation review page object.
Source: vulnara-web/src/pages/RemediationReviewPage.jsx
Actions differ by current remediation status:
  PENDING  -> Reject / Approve Script buttons visible
  APPROVED -> Mark Executed button visible
  REJECTED -> read-only "Rejected by ..." notice
"""

from selenium.webdriver.common.by import By

from .base_page import BasePage


class RemediationReviewPage(BasePage):
    HEADING = (By.CSS_SELECTOR, "h2.font-code-sm")
    APPROVE_BUTTON = (By.XPATH, "//button[contains(.,'Approve Script') or contains(.,'Approving')]")
    REJECT_BUTTON = (By.XPATH, "//button[normalize-space()='Reject']")
    MARK_EXECUTED_BUTTON = (By.XPATH, "//button[contains(.,'Mark Executed') or contains(.,'Executed')]")
    COPY_SCRIPT_BUTTON = (By.XPATH, "//button[contains(.,'Copy')]")
    REJECT_REASON_TEXTAREA = (By.CSS_SELECTOR, "textarea")
    CONFIRM_DIALOG_CONFIRM = (By.XPATH, "//button[contains(.,'Reject') and not(contains(.,'this remediation'))]")
    CONFIDENCE_HEADING = (By.XPATH, "//h3[contains(text(),'AI Confidence')]")
    CONTEXT_HEADING = (By.XPATH, "//h3[contains(text(),'Context')]")

    def open(self, remediation_id: str):
        self.goto(f"remediations/{remediation_id}")
        return self

    def is_loaded(self) -> bool:
        return self.exists(*self.HEADING) or self.exists(*self.CONFIDENCE_HEADING)

    def open_reject_dialog(self):
        self.click(*self.REJECT_BUTTON)
        return self

    def type_reject_reason(self, text: str):
        self.type_into(*self.REJECT_REASON_TEXTAREA, text)
        return self

    def approve(self):
        self.click(*self.APPROVE_BUTTON)
        return self
