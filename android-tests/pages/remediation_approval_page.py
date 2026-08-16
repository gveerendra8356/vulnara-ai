"""
pages/remediation_approval_page.py

Role-gated actions, from lib/screens/remediation_approval_screen.dart:
  - "Approve Fix (Analyst)"  -- visible/enabled for the analyst role only
  - "Mark Executed (Client)" -- visible/enabled for the client role only
  - "Reject remediation"     -- TextButton, analyst role
  - IconButton tooltip 'Copy to clipboard' on the remediation script block
  - When already actioned: "Already {status}." text replaces the action row
"""

from pages.base_page import BasePage

HEADER = "Remediation Review"
SUMMARY_LABEL = "EXECUTIVE SUMMARY"
ACTIONS_LABEL = "REMEDIATION ACTIONS"
APPROVE_LABEL = "Approve Fix (Analyst)"
EXECUTE_LABEL = "Mark Executed (Client)"
REJECT_LABEL = "Reject remediation"


class RemediationApprovalPage(BasePage):
    def is_loaded(self, timeout: float = 15) -> bool:
        return self.is_present(self.by_text(HEADER), timeout=timeout)

    def can_approve(self) -> bool:
        return self.is_present(self.by_text(APPROVE_LABEL), timeout=3)

    def can_execute(self) -> bool:
        return self.is_present(self.by_text(EXECUTE_LABEL), timeout=3)

    def can_reject(self) -> bool:
        return self.is_present(self.by_text(REJECT_LABEL), timeout=3)

    def approve(self):
        self.tap_text(APPROVE_LABEL)

    def mark_executed(self):
        self.tap_text(EXECUTE_LABEL)

    def reject(self):
        self.tap_text(REJECT_LABEL)

    def already_actioned_text(self) -> str | None:
        for t in self.all_texts():
            if t.startswith("Already "):
                return t
        return None

    def copy_script_to_clipboard(self):
        self.driver.find_element(*self.by_content_desc("Copy to clipboard")).click()
