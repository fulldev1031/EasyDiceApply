from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import os, time, json
from datetime import datetime

from .handlers.shadow_dom_handler import ShadowDOMHandler
from .handlers.job_handler import JobHandler
from .handlers.search_filter_handler import SearchAndFilter

def log(msg, level="INFO", symbol=""):
    ts = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    prefix = f"[{ts}] [{level}]"
    if symbol:
        print(f"{prefix} {symbol} {msg}")
    else:
        print(f"{prefix} {msg}")

def print_job_status(job_idx, total_jobs, page, job, status, error=None):
    log(f"\n=== Processing Job {job_idx} of {total_jobs} (Page {page}) ===")
    log(f"  • Job Title   : {job.get('card_title')}")
    log(f"  • Company     : {job.get('company_name')}")
    log(f"  • Location    : {job.get('location')}")
    log(f"  • Published   : {job.get('publish_date')}")
    if job.get('applied_date'):
        log(f"  • Applied Date: {job.get('applied_date')}")
    log(f"  • Status      : {status}")
    if error:
        log(f"  ❌ ERROR: {error}")

def print_page_summary(page, jobs_on_page, applied, already_applied, skipped, errors):
    log("\n----------------------------------------")
    log(f"Page {page} Summary:")
    log(f"  - Total Jobs      : {jobs_on_page}")
    log(f"  - Applied         : {applied} ✅")
    log(f"  - Already Applied : {already_applied} ⏩")
    log(f"  - Skipped         : {skipped} ➖")
    log(f"  - Errors          : {errors} ❌")
    log("========================================\n")

def print_final_summary(total_jobs, total_applied, total_already_applied, total_skipped, total_errors):
    log("\n************ FINAL SUMMARY ************")
    log(f"Total Jobs Processed : {total_jobs}")
    log(f"Total Applied        : {total_applied} ✅")
    log(f"Total Already Applied: {total_already_applied} ⏩")
    log(f"Total Skipped        : {total_skipped} ➖")
    log(f"Total Errors         : {total_errors} ❌")
    log("***************************************\n")

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

    def login(self):
        """Handle login process with improved verification."""
        try:
            self.update_status("Navigating to Dice login page...")
            self.driver.get("https://www.dice.com/dashboard/login")

            # Step 1: Wait for email input and enter username
            log("Waiting for email input field...", "INFO", "⏳")
            email_input = WebDriverWait(self.driver, 15).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "input[placeholder='Please enter your email']"))
            )
            email_input.clear()
            email_input.send_keys(self.username)
            email_input.send_keys(Keys.RETURN)
            log("Username entered successfully.", "SUCCESS", "✅")

            # Step 2: Wait for password input and enter password
            log("Waiting for password input field...", "INFO", "⏳")
            password_input = WebDriverWait(self.driver, 15).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "input[type='password']"))
            )
            password_input.clear()
            password_input.send_keys(self.password)
            password_input.send_keys(Keys.RETURN)
            log("Password entered successfully.", "SUCCESS", "✅")

            # Step 3: Confirm successful login by checking for a unique dashboard element
            log("Checking for dashboard element to confirm successful login...")
            for attempt in range(2):  # Retry twice
                try:
                    current_url = self.driver.current_url
                    if current_url != "https://www.dice.com/home-feed":
                        try:
                            WebDriverWait(self.driver, 10).until(
                                EC.url_to_be("https://www.dice.com/home-feed")
                            )
                        except Exception:
                            log("URL did not redirect automatically, forcing redirect to home feed.", "WARNING", "⚠️ ")
                            self.driver.get("https://www.dice.com/home-feed")
                        
                        time.sleep(5)
                    
                    dashboard_element = WebDriverWait(self.driver, 15).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, "a[href*='/profile']"))
                    )
                    if dashboard_element:
                        self.update_status("Login successful", "success")
                        log("Login confirmed successful.")
                        return True
                except Exception as e:
                    log(f"Failed to find dashboard element: {e}", "ERROR", "❌")
                    if attempt < 1:  # If this is not the last attempt
                        self.driver.refresh()  # Refresh the page
                        log("Page refreshed, retrying...")
                    else:
                        # Try alternative verification method
                        try:
                            profile_menu = WebDriverWait(self.driver, 5).until(
                                EC.presence_of_element_located((By.CSS_SELECTOR, ".profile-menu"))
                            )
                            if profile_menu:
                                self.update_status("Login successful", "success")
                                log("Login confirmed via profile menu.")
                                return True
                        except:
                            pass
                        return False

        except Exception as e:
            log(f"Login failed with error: {e}", "ERROR", "❌")
            self.update_status(f"Login failed: {str(e)}", "error")

            # Additional check for specific login error message
            try:
                error_element = self.driver.find_element(By.CSS_SELECTOR, "div.error-message")
                if error_element:
                    self.update_status("Invalid credentials provided.", "error")
                    log("Invalid credentials detected.")
            except:
                log("No specific error message found.")

            return False

    def get_job_listings(self):
        """Get all job listings from the current page"""
        try:
            # Wait for at least one job listing to be present
            self.wait.until(EC.presence_of_element_located(
                (By.CSS_SELECTOR, "a[data-testid='job-search-job-card-link']")
            ))
            time.sleep(2)  # Additional wait for all listings to load
            
            # Find all job listings
            listings = self.driver.find_elements(By.CSS_SELECTOR, "a[data-testid='job-search-job-card-link']")
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

        log(f"Job summary {action} successfully.")
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

            # Apply filters if specified
            if not search_filter.apply_filters():
                raise Exception("Filter application failed")
            time.sleep(2)
            
            job_search_results_container = self.driver.find_element(By.CSS_SELECTOR, '[data-testid="job-search-results-container"]')
            first_p_element = job_search_results_container.find_element(By.TAG_NAME, "p")
            if first_p_element:
                total_job_count = first_p_element.text.split()[0]  # Extract only the number of total results
                self.automation_status["total_jobs"] = total_job_count
                self.update_status(f"A total of {total_job_count} jobs have been searched.")

            applications_submitted = 0
            jobs_processed = 0
            already_applied = 0
            job_skipped = 0
            job_errors = 0
            page = 0
            jobs_per_page = 20

            while True:
                page += 1
                self.automation_status["current_page"] = page
                self.update_status(f"Trying to apply with page {page}...")

                job_index = 0
                current_url = self.driver.current_url
                
                job_listings = self.get_job_listings()
                total_jobs_on_page = len(job_listings)
                page_applied = 0
                page_already_applied = 0
                page_skipped = 0
                page_errors = 0

                while applications_submitted < self.max_applications and jobs_processed < 500:
                    try:
                        if not job_listings or job_index >= len(job_listings):
                            self.update_status(f"All jobs of Page {page} are processed", "completed")
                            break

                        self.automation_status["current_job"] = job_index + 1

                        listing = job_listings[job_index]
                        self.driver.execute_script("arguments[0].scrollIntoView(true);", listing)
                        time.sleep(1)
                        
                        job_search_card = listing.find_element(By.XPATH, '..')

                        is_already_applied = False

                        # Check for card is already applied by badge
                        if job_search_card and job_search_card.find_elements(By.XPATH, ".//span[contains(text(), 'Applied')]"):
                            is_already_applied = True

                        # Get Job summary
                        job_summary = {}
                        job_summary["card_title"] = self.safe_get_text(job_search_card, 'div.content > div:first-child > div:first-child > a')
                        job_summary["company_name"] = self.safe_get_text(job_search_card, 'div.header > span:first-child > a:last-child > p')
                        job_summary["location"] = self.safe_get_text(job_search_card, 'div.content > span:nth-child(2) > div:first-child > div:first-child > div:first-child > p')
                        job_summary["employment_type"] = self.safe_get_text(job_search_card, 'div.content p#employmentType-label')
                        job_summary["card_summary"] = self.safe_get_text(job_search_card, 'div.content > span:nth-child(3) > div > p')
                        job_summary["publish_date"] = ""

                        processed_job_list = self.get_job_aready_processed_list()
                        # Check for card is already processed
                        if self.update_processed_job(processed_job_list, job_summary, update=False):
                            is_already_applied = True

                        status = ""
                        error_msg = None
                        if not is_already_applied:
                            # Click the job listing
                            self.driver.execute_script("arguments[0].click();", listing)
                            new_tab = self.driver.window_handles[-1]
                            self.driver.switch_to.window(new_tab)
                            detail_url = self.driver.current_url
                            apply_result = job_handler.apply_to_job(filters=self.filters, job_summary=job_summary)
                            job_summary['apply_status'] = True
                            job_summary['job_url'] = detail_url
                            if apply_result == 1:
                                applications_submitted += 1
                                page_applied += 1
                                self.automation_status["applications_submitted"] = applications_submitted
                                progress_percent = int((applications_submitted / self.max_applications) * 100)
                                self.update_status(f"Successfully applied to job {applications_submitted} of {self.max_applications} ({progress_percent}%)")
                                status = "Applied ✅"
                            elif apply_result == 0:
                                already_applied += 1
                                page_already_applied += 1
                                self.update_status("Job already applied. Skipping...")
                                status = "Already Applied ⏩"
                            else:
                                job_skipped += 1
                                page_skipped += 1
                                job_summary['apply_status'] = False
                                self.update_status("Job Post is not Dice Easy Apply. Skipping...")
                                status = "Skipped ➖"
                            processed_job_list = self.get_job_aready_processed_list()
                            self.update_processed_job(processed_job_list, job_summary)
                        else:
                            already_applied += 1
                            page_already_applied += 1
                            self.update_status("Job already applied. Skipping...")
                            status = "Already Applied ⏩"

                        jobs_processed += 1
                        self.automation_status["jobs_processed"] = jobs_processed
                        self.automation_status["already_applied"] = already_applied
                        self.automation_status["job_skipped"] = job_skipped
                        job_index += 1
                        time.sleep(1)
                        print_job_status(job_index, total_jobs_on_page, page, job_summary, status)
                    except Exception as e:
                        job_errors += 1
                        page_errors += 1
                        self.update_status(f"Error processing job: {str(e)}", "error")
                        jobs_processed += 1
                        job_index += 1
                        print_job_status(job_index, total_jobs_on_page, page, job_summary if 'job_summary' in locals() else {}, "Error ❌", error=str(e))
                        continue
                print_page_summary(page, total_jobs_on_page, page_applied, page_already_applied, page_skipped, page_errors)
                try:
                    pagination_next = self.driver.find_element(By.XPATH, "//span[@aria-label='Next' and not(contains(@class, 'disabled'))]")
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
            print_final_summary(jobs_processed, applications_submitted, already_applied, job_skipped, job_errors)
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
