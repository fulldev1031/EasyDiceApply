from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import os, time, json

from .handlers.shadow_dom_handler import ShadowDOMHandler
from .handlers.job_handler import JobHandler
from .handlers.search_filter_handler import SearchAndFilter

class DiceAutomation:
    def __init__(self, driver, wait, username, password, keyword, location, max_applications, filters=None, status_callback=None, processed_jobs_file_path="logs/processed_job_summary_list.json"):
        self.driver = driver
        self.wait = wait
        self.username = username
        self.password = password
        self.search_keyword = keyword
        self.search_location = location
        self.max_applications = max_applications
        self.filters = filters if filters is not None else {}
        self.status_callback = status_callback
        self.processed_jobs_file_path = processed_jobs_file_path
        self.automation_status = {
            "status": "initializing",
            "message": "",
            "total_jobs": 0,
            "jobs_processed": 0,
            "applications_submitted": 0,
            "already_applied": 0,
            "job_skipped": 0,
            "current_page": 0,
            "current_job": 0,
            "max_applications": max_applications
        }

    def update_status(self, message, status="running"):
        """Update automation status and notify UI"""
        self.automation_status["message"] = message
        self.automation_status["status"] = status
        if self.status_callback:
            self.status_callback(self.automation_status)
        print(message)

    def login(self):
        """Handle login process with improved verification."""
        try:
            self.update_status("Navigating to Dice login page...")
            self.driver.get("https://www.dice.com/dashboard/login")

            # Step 1: Wait for email input and enter username
            print("Waiting for email input field...")
            email_input = WebDriverWait(self.driver, 15).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "input[placeholder='Please enter your email']"))
            )
            email_input.clear()
            email_input.send_keys(self.username)
            email_input.send_keys(Keys.RETURN)
            print("Username entered successfully.")

            # Step 2: Wait for password input and enter password
            print("Waiting for password input field...")
            password_input = WebDriverWait(self.driver, 15).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "input[type='password']"))
            )
            password_input.clear()
            password_input.send_keys(self.password)
            password_input.send_keys(Keys.RETURN)
            print("Password entered successfully.")

            # Step 3: Confirm successful login by checking for a unique dashboard element
            print("Checking for dashboard element to confirm successful login...")
            try:
                dashboard_element = WebDriverWait(self.driver, 15).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "a[href*='/profile']"))
                )
                if dashboard_element:
                    self.update_status("Login successful", "success")
                    print("Login confirmed successful.")
                    return True
            except Exception as e:
                print(f"Failed to find dashboard element: {e}")
                # Try alternative verification method
                try:
                    profile_menu = WebDriverWait(self.driver, 5).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, ".profile-menu"))
                    )
                    if profile_menu:
                        self.update_status("Login successful", "success")
                        print("Login confirmed via profile menu.")
                        return True
                except:
                    pass
                
                return False

        except Exception as e:
            print(f"Login failed with error: {e}")
            self.update_status(f"Login failed: {str(e)}", "error")

            # Additional check for specific login error message
            try:
                error_element = self.driver.find_element(By.CSS_SELECTOR, "div.error-message")
                if error_element:
                    self.update_status("Invalid credentials provided.", "error")
                    print("Invalid credentials detected.")
            except:
                print("No specific error message found.")

            return False

    def get_job_listings(self):
        """Get all job listings from the current page"""
        try:
            # Wait for at least one job listing to be present
            self.wait.until(EC.presence_of_element_located(
                (By.CSS_SELECTOR, "a[data-cy='card-title-link'].card-title-link")
            ))
            time.sleep(2)  # Additional wait for all listings to load
            
            # Find all job listings
            listings = self.driver.find_elements(By.XPATH, "//a[@data-cy='card-title-link']")
            self.update_status(f"Found {len(listings)} Dice job listings in current page.")
            return listings
        except Exception as e:
            self.update_status(f"Error finding job listings: {str(e)}", "error")
            return []
    
    def safe_get_text(self, parent, selector, default=""):
        try:
            element = parent.find_element(By.CSS_SELECTOR, selector)
            return element.text
        except:
            return default

    def find_job_summary_in_list(self, job_summary, job_list):
        for index, job in enumerate(job_list):
            if (
                job.get("card_title") == job_summary.get("card_title") and
                job.get("company_name") == job_summary.get("company_name") and
                job.get("location") == job_summary.get("location") and
                job.get("employment_type") == job_summary.get("employment_type") and
                job.get("card_summary") == job_summary.get("card_summary")
            ):
                return index
        return -1
    
    def get_job_aready_processed_list(self):
        file_path = self.processed_jobs_file_path
        os.makedirs(os.path.dirname(file_path), exist_ok=True)

        if os.path.exists(file_path):
            with open(file_path, "r") as file:
                try:
                    processed_job_summary_list = json.load(file)
                except json.JSONDecodeError:
                    processed_job_summary_list = []
        else:
            processed_job_summary_list = []
        return processed_job_summary_list
    
    def update_processed_job(self, processed_job_summary_list, job_summary=None, update=True):
        if job_summary is None:
            with open(self.processed_jobs_file_path, "w") as file:
                json.dump(processed_job_summary_list, file, indent=4)
            return False

        found_index = self.find_job_summary_in_list(job_summary, processed_job_summary_list)

        if found_index == -1:
            processed_job_summary_list.append(job_summary)
            action = "added"
        else:
            processed_job_summary_list[found_index] = job_summary
            action = "updated"
        if update:
            with open(self.processed_jobs_file_path, "w") as file:
                json.dump(processed_job_summary_list, file, indent=4)

        print(f"Job summary {action} successfully.")
        return action == "updated"


    def run(self):
        """Main method to run the automation"""
        try:
            self.update_status("Starting automation...")

            # Initialize handlers
            search_filter = SearchAndFilter(self.driver, self.wait, filters=self.filters)
            shadow_dom_handler = ShadowDOMHandler(self.driver, self.wait)
            job_handler = JobHandler(self.driver, self.wait, shadow_dom_handler, self.status_callback)

            # Perform search with the keyword
            if not search_filter.perform_search(self.search_keyword, self.search_location):
                raise Exception("Search failed")
            print("Search completed successfully.")

            # Apply filters if specified
            if not search_filter.apply_filters():
                raise Exception("Filter application failed")
            print("Filters applied successfully.")
            
            total_count_elem = self.driver.find_element(By.ID, "totalJobCount")
            if total_count_elem:
                total_job_count = total_count_elem.text
                self.automation_status["total_jobs"] = total_job_count
                self.update_status(f"A total of {total_job_count} jobs have been searched.")

            applications_submitted = 0
            jobs_processed = 0
            already_applied = 0
            job_skipped = 0
            page = 0

            while True:
                page += 1
                self.automation_status["current_page"] = page
                self.update_status(f"Trying to apply with page {page}...")

                job_index = 0
                current_url = self.driver.current_url
                
                job_listings = self.get_job_listings()

                while applications_submitted < self.max_applications and jobs_processed < 500:
                    try:
                        if not job_listings or job_index >= len(job_listings):
                            self.update_status(f"All jobs of Page {page} are processed", "completed")
                            break

                        self.automation_status["current_job"] = job_index + 1

                        print('///' + '-' * 100)
                        self.update_status(f"Processing job {job_index + 1} of {len(job_listings)} in Page {page}")
                        print('-' * 100 + '///')
                        

                        listing = job_listings[job_index]
                        self.driver.execute_script("arguments[0].scrollIntoView(true);", listing)
                        time.sleep(1)
                        
                        job_search_card = listing.find_element(By.XPATH, "./ancestor::*[@data-cy='search-card']")

                        is_already_applied = False

                        # Check for card is already applied by badge
                        if job_search_card and job_search_card.find_elements(By.XPATH, ".//div[contains(@class, 'ribbon-status-applied')]"):
                            is_already_applied = True

                        # Get Job summary
                        job_summary = {}

                        job_summary["card_title"] = listing.text  # Assuming 'listing' is already defined
                        job_summary["company_name"] = self.safe_get_text(job_search_card, '[data-cy="search-result-company-name"]')
                        job_summary["location"] = self.safe_get_text(job_search_card, '[data-cy="search-result-location"]')
                        job_summary["employment_type"] = self.safe_get_text(job_search_card, '[data-cy="search-result-employment-type"]')
                        job_summary["card_summary"] = self.safe_get_text(job_search_card, '[data-cy="card-summary"]')
                        
                        processed_job_list = self.get_job_aready_processed_list()
                        # Check for card is already processed
                        if self.update_processed_job(processed_job_list, job_summary, update=False):
                            is_already_applied = True
                        
                        if not is_already_applied:
                            # Click the job listing
                            self.driver.execute_script("arguments[0].click();", listing)
                            new_tab = self.driver.window_handles[-1]
                            self.driver.switch_to.window(new_tab)
                            detail_url = self.driver.current_url
                            apply_result = job_handler.apply_to_job(filters=self.filters)
                            job_summary['apply_status'] = True
                            job_summary['job_url'] = detail_url
                            if apply_result == 1:
                                applications_submitted += 1
                                self.automation_status["applications_submitted"] = applications_submitted
                                progress_percent = int((applications_submitted / self.max_applications) * 100)
                                self.update_status(f"Successfully applied to job {applications_submitted} of {self.max_applications} ({progress_percent}%)")
                            elif apply_result == 0:
                                already_applied += 1
                                self.update_status("Job already applied. Skipping...")
                            else:
                                job_skipped += 1
                                job_summary['apply_status'] = False
                                self.update_status("Job Post is not Dice Easy Apply. Skipping...")
                            
                            processed_job_list = self.get_job_aready_processed_list()
                            self.update_processed_job(processed_job_list, job_summary)

                        else:
                            already_applied += 1
                            self.update_status("Job already applied. Skipping...")

                        jobs_processed += 1
                        self.automation_status["jobs_processed"] = jobs_processed
                        self.automation_status["already_applied"] = already_applied
                        self.automation_status["job_skipped"] = job_skipped
                        job_index += 1
                        time.sleep(1)
                        
                    except Exception as e:
                        self.update_status(f"Error processing job: {str(e)}", "error")
                        jobs_processed += 1
                        job_index += 1
                        continue
                try:
                    pagination_next = self.driver.find_element(By.XPATH, "//li[contains(@class, 'pagination-next') and not(contains(@class, 'disabled'))]")
                    if pagination_next:
                        pagination_next.click()
                        time.sleep(1)
                        self.update_status(f"Moving to next page(Page {page+1})")
                        WebDriverWait(self.driver, 15).until(EC.url_changes(current_url))
                        time.sleep(2)

                    else:
                        self.update_status("No more jobs available to process.", "completed")
                        break
                except:
                    self.update_status("No more jobs available to process.", "completed")
                    break


            # Update final status
            if applications_submitted > 0:
                self.update_status(
                    f"Completed! Applied to {applications_submitted} out of {self.max_applications} target jobs",
                    "completed"
                )
            else:
                self.update_status("Completed - No applications submitted", "completed_no_applications")

            return {
                "success": True,
                "applications_submitted": applications_submitted,
                "jobs_processed": jobs_processed,
                "already_applied": already_applied,
                "status": self.automation_status
            }

        except Exception as e:
            self.update_status(f"An error occurred: {str(e)}", "error")
            return {
                "success": False,
                "error": str(e),
                "status": self.automation_status
            }
