from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
import time

class SearchAndFilter:
    def __init__(self, driver, wait, filters=None):
        self.driver = driver
        self.wait = wait
        # Initialize filters with user preferences or empty dict
        self.filters = filters if filters is not None else {}

    def perform_search(self, keyword, location):
        """Check for search box, reveal if needed, and perform search"""
        print("Checking for search box...")
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
                print("Search box and location box found directly")
            except Exception:
                print("Search box or location box not immediately visible")
                try:
                    # Try direct navigation to jobs page
                    print("Navigating to jobs page...")
                    self.driver.get("https://www.dice.com/jobs")
                    time.sleep(3)
                    
                    # Wait for search input with exact selector
                    print("Waiting for search box to appear...")
                    search_input = self.wait.until(EC.presence_of_element_located((
                        By.CSS_SELECTOR, 
                        "input#typeaheadInput[data-cy='typeahead-input']"
                    )))
                    print("Search box found after navigation")

                    print("Waiting for location box to appear...")
                    location_input = self.wait.until(EC.presence_of_element_located((
                        By.CSS_SELECTOR, 
                        "input#google-location-search"
                    )))
                    print("Location box found after navigation")
                    
                except Exception:
                    # If direct navigation fails, try shadow DOM approach
                    print("Trying shadow DOM navigation...")
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
                    
                    print("Clicked Search Jobs link, waiting for page load...")
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
                print(f"Entering search keyword: {keyword}")
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
                    print(str(e))
                    raise Exception("Not found any job post for the search filter.")
                    time.sleep(3)
                
                print("Search initiated successfully")
                return True
            else:
                print("Failed to find search input")
                return False
            
        except Exception as e:
            print(f"Error during search: {str(e)}")
            return False

    def apply_filters(self):
        """Apply filters based on user preferences"""
        try:
            print(f"Applying filters: {self.filters}")  # Debug: Show filter contents
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
                print("Applying Posted Date filter...")
                try:
                    # Try to find the radio input with a more flexible XPath
                    posted_date_button = self.wait.until(EC.presence_of_element_located((
                        By.XPATH, f"//input[@type='radio' and @name='postedDateOption' and @value='{posted_date}']"
                    )))
                    # Use JavaScript to click the element
                    self.driver.execute_script("arguments[0].click();", posted_date_button)
                    time.sleep(4)
                    filters_applied = True
                    print("Posted Date filter applied successfully")
                except Exception as e:
                    print(f"Error applying Posted Date filter: {str(e)}")
                    # Try alternative approach if the first one fails
                    try:
                        posted_date_button = self.wait.until(EC.presence_of_element_located((
                            By.CSS_SELECTOR, f"input[type='radio'][name='postedDateOption'][value='{posted_date}']"
                        )))
                        self.driver.execute_script("arguments[0].click();", posted_date_button)
                        time.sleep(4)
                        filters_applied = True
                        print("Posted Date filter applied successfully using alternative selector")
                    except Exception as e2:
                        print(f"Error applying Posted Date filter with alternative selector: {str(e2)}")
            else:
                print("Posted Date filter not selected, skipping...")

            # Apply Third Party filter only if selected
            if self.filters.get('third_party', False):
                print("Applying Third Party filter...")
                try:
                    third_party_button = self.wait.until(EC.element_to_be_clickable((
                        By.XPATH, "//button[@role='checkbox' and @aria-label='Filter Search Results by Third Party']"
                    )))
                    self.driver.execute_script("arguments[0].click();", third_party_button)
                    time.sleep(4)
                    filters_applied = True
                    print("Third Party filter applied successfully")
                except Exception as e:
                    print(f"Error applying Third Party filter: {str(e)}")
            else:
                print("Third Party filter not selected, skipping...")

            # Apply Remote filter only if keyword is `Remote`
            if self.filters.get('remote', True):
                print("Applying Work Setting filter as `Remote`...")
                try:
                    remote_button = self.wait.until(EC.presence_of_element_located((
                        By.XPATH, "//input[@type='checkbox' and @name='workPlaceTypeOptions.remote']"
                    )))
                    self.driver.execute_script("arguments[0].click();", remote_button)
                    time.sleep(4)
                    filters_applied = True
                    print("Remote filter applied successfully")
                except Exception as e:
                    print(f"Error applying Remote filter: {str(e)}")
                    # Try alternative approach if the first one fails
                    try:
                        remote_button = self.wait.until(EC.presence_of_element_located((
                            By.CSS_SELECTOR, "input[type='checkbox'][name='workPlaceTypeOptions.remote']"
                        )))
                        self.driver.execute_script("arguments[0].click();", remote_button)
                        time.sleep(4)
                        filters_applied = True
                        print("Remote filter applied successfully using alternative selector")
                    except Exception as e2:
                        print(f"Error applying Remote filter with alternative selector: {str(e2)}")
            else:
                print("Remote filter not selected, skipping...")

            
            

            if not self.filters:
                print("No filters selected, continuing without filters")
                return True
            return filters_applied or self.filters
            
        except Exception as e:
            print(f"Error applying filters: {str(e)}")
            return False