from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
import time
import traceback
from datetime import datetime

def log(msg, level="INFO", symbol=""):
    ts = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    prefix = f"[{ts}] [{level}]"
    if symbol:
        print(f"{prefix} {symbol} {msg}")
    else:
        print(f"{prefix} {msg}")

class ShadowDOMHandler:
    def __init__(self, driver, wait):
        self.driver = driver
        self.wait = wait

    def find_and_click_easy_apply(self):
        """Find and click Easy Apply button or wait for application-submitted tag in shadow DOM."""
        log("Attempting to find Easy Apply button or application-submitted tag in shadow DOM...", "INFO", "🔍")
        try:
            shadow_host = self.wait.until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "apply-button-wc.hydrated"))
            )
            log("Found shadow host element", "SUCCESS", "✅")

            # Wait for either the Easy Apply button or application-submitted tag
            apply_button = self.wait_for_shadow_element(shadow_host, 'button.btn.btn-primary')
            application_submitted = self.wait_for_shadow_element(shadow_host, 'application-submitted')

            if application_submitted:
                log("Application already submitted - detected application-submitted tag", "INFO", "⏩")
                return "application_already_submitted"

            if apply_button:
                self.driver.execute_script("arguments[0].click();", apply_button)
                log("Successfully clicked Easy Apply button", "SUCCESS", "✅")
                return "easy_apply_button_clicked"

            log("Easy Apply button not found and application-submitted tag not detected", "WARNING", "⚠️")
            return "no_action_possible"

        except Exception as e:
            log(f"Error interacting with shadow DOM: {str(e)}", "ERROR", "❌")
            traceback.print_exc()
            return f"error_occurred: {str(e)}"

    def wait_for_shadow_element(self, shadow_host, selector, timeout=10):
        """Wait for an element within a shadow DOM"""
        for _ in range(timeout):
            element = self.driver.execute_script(f"""
                const shadowHost = arguments[0];
                const shadowRoot = shadowHost.shadowRoot;
                return shadowRoot.querySelector('{selector}');
            """, shadow_host)
            if element:
                return element
            time.sleep(1)
        return None