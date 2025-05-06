from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
import time
from datetime import datetime

def log(msg, level="INFO", symbol=""):
    ts = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    prefix = f"[{ts}] [{level}]"
    if symbol:
        print(f"{prefix} {symbol} {msg}")
    else:
        print(f"{prefix} {msg}")

class SearchAndFilter:
    def __init__(self, driver, wait, filters=None):
        self.driver = driver
        self.wait = wait
        # Initialize filters with user preferences or empty dict
        self.filters = filters if filters is not None else {}

    def perform_search(self, keyword, location):
        """Check for search box, reveal if needed, and perform search"""
        log("Checking for search box...", "INFO", "🔍")
        search_input = None
        location_input = None
        
        try:
            # First try to find the search input directly
            try:
                search_input = self.wait.until(EC.presence_of_element_located((
                    By.CSS_SELECTOR, 
                    "input[aria-label='Job title, skill, company, keyword']"
                )))
                location_input = self.wait.until(EC.presence_of_element_located((
                    By.CSS_SELECTOR, 
                    "input[aria-label='Location Field']"
                )))
                log("Search box and location box found directly", "SUCCESS", "✅")
            except Exception:
                log("Search box or location box not immediately visible", "WARNING", "⚠️")
                try:
                    # Try direct navigation to jobs page
                    log("Navigating to jobs page...", "INFO")
                    self.driver.get("https://www.dice.com/jobs")
                    time.sleep(3)
                    
                    # Wait for search input with exact selector
                    log("Waiting for search box to appear...", "INFO")
                    search_input = self.wait.until(EC.presence_of_element_located((
                        By.CSS_SELECTOR, 
                        "input#typeaheadInput[data-cy='typeahead-input']"
                    )))
                    log("Search box found after navigation", "SUCCESS", "✅")

                    log("Waiting for location box to appear...", "INFO")
                    location_input = self.wait.until(EC.presence_of_element_located((
                        By.CSS_SELECTOR, 
                        "input#google-location-search"
                    )))
                    log("Location box found after navigation", "SUCCESS", "✅")
                    
                except Exception:
                    # If direct navigation fails, try shadow DOM approach
                    log("Trying shadow DOM navigation...", "INFO")
                    self.driver.execute_script("""
                        const header = document.querySelector('dhi-seds-nav-header');
                        const shadowRoot1 = header.shadowRoot;
                        const technologist = shadowRoot1.querySelector('dhi-seds-nav-header-technologist');
                        const shadowRoot2 = technologist.shadowRoot;
                        const display = shadowRoot2.querySelector('dhi-seds-nav-header-display');
                        const shadowRoot3 = display.shadowRoot;
                        const searchLink = shadowRoot3.querySelector('a[href*="/jobs"]');
                        if (searchLink) {
                            searchLink.click();
                            return true;
                        }
                        return false;
                    """)
                    
                    log("Clicked Search Jobs link, waiting for page load...", "INFO")
                    time.sleep(5)
                    
                    search_input = self.wait.until(EC.presence_of_element_located((
                        By.CSS_SELECTOR, 
                        "input#typeaheadInput[data-cy='typeahead-input']"
                    )))
                    location_input = self.wait.until(EC.presence_of_element_located((
                        By.CSS_SELECTOR, 
                        "input#google-location-search"
                    )))
            
            if search_input and location_input:
                # Perform the search
                log(f"Entering search keyword: {keyword}", "INFO")
                search_input.clear()
                time.sleep(1)
                
                # Type the keyword character by character
                for char in keyword:
                    search_input.send_keys(char)
                    time.sleep(0.01)

                # if location and not location.strip().lower() == 'remote':
                #     print(f"Entering location: {location}")
                #     location_input.clear()
                #     time.sleep(1)
                    
                #     # Type the location character by location
                #     for char in location:
                #         location_input.send_keys(char)
                #         time.sleep(0.01)

                time.sleep(1)
                search_input.send_keys(Keys.RETURN)
                time.sleep(4)
                
                # Wait for results to load
                try:
                    self.wait.until(EC.presence_of_element_located((
                        By.CSS_SELECTOR, 
                        "a[data-testid='job-search-job-card-link']"
                    )))
                except Exception as e:
                    # Additional wait if needed
                    log(str(e), "ERROR", "❌")
                    raise Exception("Not found any job post for the search filter.")
                    time.sleep(3)
                
                log("Search initiated successfully", "SUCCESS", "✅")
                return True
            else:
                log("Failed to find search input", "ERROR", "❌")
                return False
            
        except Exception as e:
            log(f"Error during search: {str(e)}", "ERROR", "❌")
            return False

    def apply_filters(self):
        """Apply filters based on user preferences"""
        try:
            log(f"Applying filters: {self.filters}", "INFO")  # Debug: Show filter contents
            filters_applied = False

            # all_filters_button = self.wait.until(EC.element_to_be_clickable((
            #     By.XPATH, "//button[@jf-ext-button-ct='all filters']"
            # )))
            # self.driver.execute_script("arguments[0].click();", all_filters_button)
            # print("All filter setting modal is shown")
            # time.sleep(2)
            
            # Apply Posted Date filter only if selected
            posted_date = self.filters.get('posted_date', 'NO_PREFERENCE')
            if posted_date:
                log("Applying Posted Date filter...", "INFO")
                try:
                    # Try to find the radio input with a more flexible XPath
                    posted_date_button = self.wait.until(EC.presence_of_element_located((
                        By.XPATH, f"//input[@type='radio' and @name='postedDateOption' and @value='{posted_date}']"
                    )))
                    # Use JavaScript to click the element
                    self.driver.execute_script("arguments[0].click();", posted_date_button)
                    time.sleep(4)
                    filters_applied = True
                    log("Posted Date filter applied successfully", "SUCCESS", "✅")
                except Exception as e:
                    log(f"Error applying Posted Date filter: {str(e)}", "ERROR", "❌")
                    # Try alternative approach if the first one fails
                    try:
                        posted_date_button = self.wait.until(EC.presence_of_element_located((
                            By.CSS_SELECTOR, f"input[type='radio'][name='postedDateOption'][value='{posted_date}']"
                        )))
                        self.driver.execute_script("arguments[0].click();", posted_date_button)
                        time.sleep(4)
                        filters_applied = True
                        log("Posted Date filter applied successfully using alternative selector", "SUCCESS", "✅")
                    except Exception as e2:
                        log(f"Error applying Posted Date filter with alternative selector: {str(e2)}", "ERROR", "❌")
            else:
                log("Posted Date filter not selected, skipping...", "INFO")

            # Apply Third Party filter only if selected
            if self.filters.get('third_party', False):
                log("Applying Third Party filter...", "INFO")
                try:
                    third_party_button = self.wait.until(EC.element_to_be_clickable((
                        By.XPATH, "//button[@role='checkbox' and @aria-label='Filter Search Results by Third Party']"
                    )))
                    self.driver.execute_script("arguments[0].click();", third_party_button)
                    time.sleep(4)
                    filters_applied = True
                    log("Third Party filter applied successfully", "SUCCESS", "✅")
                except Exception as e:
                    log(f"Error applying Third Party filter: {str(e)}", "ERROR", "❌")
            else:
                log("Third Party filter not selected, skipping...", "INFO")

            # Apply Remote filter only if keyword is `Remote`
            if self.filters.get('remote', True):
                log("Applying Work Setting filter as `Remote`...", "INFO")
                try:
                    remote_button = self.wait.until(EC.presence_of_element_located((
                        By.XPATH, "//input[@type='checkbox' and @name='workPlaceTypeOptions.remote']"
                    )))
                    self.driver.execute_script("arguments[0].click();", remote_button)
                    time.sleep(4)
                    filters_applied = True
                    log("Remote filter applied successfully", "SUCCESS", "✅")
                except Exception as e:
                    log(f"Error applying Remote filter: {str(e)}", "ERROR", "❌")
                    # Try alternative approach if the first one fails
                    try:
                        remote_button = self.wait.until(EC.presence_of_element_located((
                            By.CSS_SELECTOR, "input[type='checkbox'][name='workPlaceTypeOptions.remote']"
                        )))
                        self.driver.execute_script("arguments[0].click();", remote_button)
                        time.sleep(4)
                        filters_applied = True
                        log("Remote filter applied successfully using alternative selector", "SUCCESS", "✅")
                    except Exception as e2:
                        log(f"Error applying Remote filter with alternative selector: {str(e2)}", "ERROR", "❌")
            else:
                log("Remote filter not selected, skipping...", "INFO")

            
            

            if not self.filters:
                log("No filters selected, continuing without filters", "INFO")
                return True
            return filters_applied or self.filters
            
        except Exception as e:
            log(f"Error applying filters: {str(e)}", "ERROR", "❌")
            return False