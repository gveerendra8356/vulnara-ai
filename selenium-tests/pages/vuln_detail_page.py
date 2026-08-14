"""
Vulnerability detail page object.
Source: vulnara-web/src/pages/VulnerabilityDetailPage.jsx
"""

from selenium.webdriver.common.by import By

from .base_page import BasePage


class VulnDetailPage(BasePage):
    def open(self, vuln_id: str):
        self.goto(f"vulnerabilities/{vuln_id}")
        return self

    def is_loaded(self) -> bool:
        return self.exists(By.TAG_NAME, "h2") or self.exists(By.TAG_NAME, "h1")
