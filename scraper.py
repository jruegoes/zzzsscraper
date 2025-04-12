import requests
from bs4 import BeautifulSoup
import json
from datetime import datetime
import os
from typing import List, Dict
import time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import re
import sys
import selenium
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

class ESSJobScraper:
    def __init__(self):
        # Use the complete URL with search parameters
        self.base_url = "https://www.ess.gov.si/iskalci-zaposlitve/iskanje-zaposlitve/iskanje-dela/#/?drzava=SI&datObj=TODAY&iskalniTekst=&iskalnaLokacija="
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }

    def get_page_content(self, url: str) -> str:
        """Get the HTML content of a page."""
        try:
            response = requests.get(url, headers=self.headers)
            response.encoding = 'utf-8'  # Explicitly set UTF-8 encoding
            return response.text
        except Exception as e:
            print(f"Error fetching page content: {e}")
            return ""

    def parse_job_listings(self, html_content: str) -> List[str]:
        """Parse job listings from the HTML content and log job titles."""
        # The current approach won't work because the content is loaded dynamically
        soup = BeautifulSoup(html_content, 'html.parser')
        job_titles = []

        # Debug: Print the entire HTML content to check if job cards are presentwill help you see if the content is loaded correctly

        # Find all job cards
        job_cards = soup.find_all('a', class_='list-group-item list-group-item-action set-pointer ng-star-inserted')

        if not job_cards:
            print("No job cards found. Please check the HTML structure.")
        else:
            print(f"Found {len(job_cards)} job cards.")  # Debugging statement
            for card in job_cards:
                print(card)  # Print each job card to verify its structure

        for card in job_cards:
            try:
                # Extract job title
                title = card.find('h5', class_='list-item-title').get_text(strip=True)
                job_titles.append(title)
                print(f"Job Title: {title}")  # Log the job title
            except Exception as e:
                print(f"Error parsing job card: {e}")
                continue

        return job_titles

    def scrape_jobs(self, limit: int = 60):
        """Main method to scrape jobs from the ESS website."""
        html_content = self.get_page_content(self.base_url)
        if not html_content:
            print("Failed to retrieve HTML content.")
            return []

        job_titles = self.parse_job_listings(html_content)

        # Limit the number of jobs to the specified limit
        if len(job_titles) > limit:
            job_titles = job_titles[:limit]
            print(f"Limiting results to the first {limit} jobs.")

        return job_titles

    def scrape_jobs_with_selenium(self, limit=None):
        """
        Use Selenium to scrape jobs from the ESS website.
        If limit is None, all available jobs will be scraped.
        """
        # Basic Chrome options
        chrome_options = Options()
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        
        # Initialize the driver
        driver = webdriver.Chrome(options=chrome_options)
        driver.set_page_load_timeout(300)  # 5 minutes timeout
        
        try:
            # Navigate to the URL
            print(f"Loading URL: {self.base_url}")
            driver.get(self.base_url)
            
            # Wait for job listings to load
            WebDriverWait(driver, 30).until(
                EC.presence_of_element_located((By.CLASS_NAME, "list-group-item"))
            )
            
            # Get total jobs count
            total_jobs_element = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, ".card-header-title.number-text strong"))
            )
            total_jobs = int(total_jobs_element.text.strip())
            print(f"Total jobs available: {total_jobs}")
            
            # Adjust max jobs to scrape based on limit
            max_jobs_to_scrape = total_jobs if limit is None else min(limit, total_jobs)
            print(f"Will scrape up to {max_jobs_to_scrape} jobs")
            
            # Keep clicking "Show more" button until all needed jobs are loaded
            max_attempts = 100  # Increased max attempts for full scraping
            attempts = 0
            
            while attempts < max_attempts:
                # Force wait for page to fully load before checking job count
                time.sleep(2)
                
                # Count current jobs
                job_elements = driver.find_elements(By.CSS_SELECTOR, ".list-group-item")
                jobs_loaded = len(job_elements)
                print(f"Currently loaded: {jobs_loaded} jobs")
                
                # Check if we've loaded enough jobs
                if jobs_loaded >= max_jobs_to_scrape:
                    print(f"Loaded {jobs_loaded} jobs, which meets our limit of {max_jobs_to_scrape}")
                    break
                    
                # Check if button exists before trying to click
                show_more_buttons = driver.find_elements(By.CSS_SELECTOR, "button.show-more-btn")
                if not show_more_buttons:
                    print("No more 'Show more' button found")
                    break
                    
                try:
                    # Use JavaScript to scroll to the button and click it
                    button = show_more_buttons[0]
                    driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", button)
                    time.sleep(1)  # Give time for scrolling
                    driver.execute_script("arguments[0].click();", button)
                    
                    print(f"Clicked 'Show more' button, attempt {attempts+1}")
                    attempts += 1
                    
                    # Wait between clicks to ensure content loads
                    time.sleep(3)
                    
                except Exception as e:
                    print(f"Error clicking 'Show more' button: {str(e)}")
                    break
            
            # Process only the limited number of job listings
            job_cards = driver.find_elements(By.CSS_SELECTOR, ".list-group-item")
            job_cards = job_cards[:max_jobs_to_scrape]  # Limit the job cards to process
            
            # Create a list to store complete job data
            job_data = []
            
            # Process limited jobs
            print(f"Starting to process {len(job_cards)} jobs in detail...")
            
            for index in range(len(job_cards)):
                # Initialize job_detail outside the try block
                job_detail = {"title": "Unknown", "company": "Unknown", "job_id": "", "job_url": ""}
                success = False
                
                try:
                    print(f"\n--- Processing job {index+1}/{len(job_cards)} ---")
                    
                    # Retrieve job cards again in case the DOM has been refreshed
                    job_cards = driver.find_elements(By.CSS_SELECTOR, ".list-group-item")
                    
                    # Get the current job card
                    job_card = job_cards[index]
                    
                    # Extract job ID from the card's ID attribute
                    try:
                        job_card_id = job_card.get_attribute("id")
                        if job_card_id and job_card_id.startswith("vacancy-"):
                            # Try to find the job ID embedded in the DOM
                            # This is a first attempt to get the job ID
                            print(f"Job card ID: {job_card_id}")
                        else:
                            job_card_id = None
                    except Exception as e:
                        print(f"Warning: Could not get job card ID: {str(e)}")
                        job_card_id = None
                    
                    # Extract job URL/href before clicking
                    try:
                        # Get the href attribute which contains the direct link to the job
                        job_url = job_card.get_attribute("href")
                        if job_url:
                            job_detail["job_url"] = job_url
                            print(f"Job URL: {job_url}")
                        else:
                            # If href is not available, try to get the current URL with fragment identifier
                            job_card_id = job_card.get_attribute("id")
                            if job_card_id:
                                # Construct URL with fragment identifier
                                base_url = driver.current_url.split('#')[0]
                                job_detail["job_url"] = f"{base_url}#{job_card_id}"
                                print(f"Constructed Job URL: {job_detail['job_url']}")
                            else:
                                # As a fallback, get the ID from the data attribute that contains the job reference
                                job_ref = job_card.get_attribute("data-reference") or job_card.get_attribute("data-id")
                                if job_ref:
                                    job_detail["job_url"] = f"{self.base_url}&selectedVacancyId={job_ref}"
                                    print(f"Reference-based URL: {job_detail['job_url']}")
                                else:
                                    job_detail["job_url"] = ""
                                    print("No job URL could be extracted")
                    except Exception as e:
                        print(f"Warning: Could not get job URL: {str(e)}")
                        job_detail["job_url"] = ""
                    
                    # Extract the basic job title before clicking
                    try:
                        job_title_element = job_card.find_element(By.CSS_SELECTOR, "h5.list-item-title")
                        job_title = job_title_element.text.strip()
                        job_detail["title"] = job_title
                        print(f"Title: {job_title}")
                    except Exception as e:
                        print(f"Warning: Could not get job title: {str(e)}")
                    
                    # Extract company info before clicking
                    try:
                        company_element = job_card.find_element(By.CSS_SELECTOR, "p.list-item-text")
                        company_info = company_element.text.strip()
                        job_detail["company"] = company_info
                        print(f"Company: {company_info}")
                    except Exception as e:
                        print(f"Warning: Could not get company info: {str(e)}")
                    
                    # Store the current URL before clicking (this will help construct the direct link later)
                    current_url_before_click = driver.current_url
                    
                    # Click on the job card to open the modal
                    print("Clicking job card to open modal...")
                    try:
                        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", job_card)
                        time.sleep(1)
                        driver.execute_script("arguments[0].click();", job_card)
                    except Exception as e:
                        print(f"Error clicking job card: {str(e)}")
                        raise
                    
                    # Wait for the modal to load
                    try:
                        WebDriverWait(driver, 10).until(
                            EC.presence_of_element_located((By.CSS_SELECTOR, ".pdm-container"))
                        )
                        print("Modal loaded successfully")
                        
                        # Wait a moment to ensure the URL in the browser is fully updated
                        time.sleep(2)
                        
                        # Get the current URL after modal is loaded - this is exactly what we want
                        modal_url = driver.current_url
                        
                        # Simply save the exact URL from the browser when modal is open
                        job_detail["job_url"] = modal_url
                        print(f"Saved job URL from modal: {modal_url}")
                        
                        # IMPORTANT: Don't override this URL anywhere else in the code!
                        
                        # Extract job ID if needed
                        if "/#/pdm/" in modal_url:
                            try:
                                job_id = modal_url.split("/#/pdm/")[1].strip()
                                job_detail["job_id"] = job_id
                                print(f"Extracted job ID: {job_id}")
                            except Exception as e:
                                print(f"Warning: Could not extract job ID from URL: {str(e)}")
                    except Exception as e:
                        print(f"Error waiting for modal: {str(e)}")
                        raise
                    
                    # Extract title and company directly from the modal instead of the card
                    try:
                        # Title extraction from modal using the info-title class
                        title_div = driver.find_element(By.CSS_SELECTOR, ".info-title.vacancies-name-detail")
                        if title_div:
                            title_text = title_div.text.strip()
                            # Title format is usually "JOB TITLE | LOCATION"
                            if "|" in title_text:
                                title = title_text.split("|")[0].strip()
                                job_detail["title"] = title
                                print(f"Title from modal: {title}")
                            else:
                                job_detail["title"] = title_text
                                print(f"Title from modal (no separator): {title_text}")
                        
                        # Company extraction from modal using the vacancies-organization class
                        company_div = driver.find_element(By.CSS_SELECTOR, ".vacancies-organization")
                        if company_div:
                            company_text = company_div.text.strip()
                            job_detail["company"] = company_text
                            print(f"Company from modal: {company_text}")
                    except Exception as e:
                        print(f"Warning: Could not extract title/company from modal: {str(e)}")
                        # Fallback to card extraction if modal extraction fails
                        # ... existing code for fallback extraction ...
                    
                    # Wait a moment for content to fully load
                    time.sleep(3)
                    
                    # Extract detailed information from the modal
                    print("Extracting details from modal...")
                    
                    # Process job description
                    try:
                        desc_section = driver.find_elements(By.CSS_SELECTOR, ".section-opis .text-justify")
                        if desc_section:
                            job_detail["description"] = desc_section[0].text.strip()
                            print(f"Description: {job_detail['description'][:50]}..." if len(job_detail['description']) > 50 else f"Description: {job_detail['description']}")
                        else:
                            job_detail["description"] = ""
                            print("No description found")
                    except Exception as e:
                        print(f"Warning: Could not get description: {str(e)}")
                        job_detail["description"] = ""
                    
                    # Process job requirements
                    try:
                        req_section = driver.find_elements(By.CSS_SELECTOR, ".section-Pricakujemo")
                        if req_section:
                            requirements = []
                            req_items = req_section[0].find_elements(By.CSS_SELECTOR, ".body-text")
                            for item in req_items:
                                requirements.append(item.text.strip())
                            job_detail["requirements"] = requirements
                            print(f"Requirements: {requirements[:2]}..." if len(requirements) > 2 else f"Requirements: {requirements}")
                        else:
                            job_detail["requirements"] = []
                            print("No requirements found")
                    except Exception as e:
                        print(f"Warning: Could not get requirements: {str(e)}")
                        job_detail["requirements"] = []
                    
                    # Process job benefits
                    try:
                        benefits_section = driver.find_elements(By.CSS_SELECTOR, ".section-nudimo")
                        if benefits_section:
                            benefits = []
                            benefit_items = benefits_section[0].find_elements(By.CSS_SELECTOR, ".body-text")
                            for item in benefit_items:
                                benefits.append(item.text.strip())
                            job_detail["benefits"] = benefits
                            print(f"Benefits: {benefits[:2]}..." if len(benefits) > 2 else f"Benefits: {benefits}")
                        else:
                            job_detail["benefits"] = []
                            print("No benefits found")
                    except Exception as e:
                        print(f"Warning: Could not get benefits: {str(e)}")
                        job_detail["benefits"] = []
                    
                    # Process application method
                    try:
                        app_section = driver.find_elements(By.CSS_SELECTOR, ".section-nacin-prijave")
                        if app_section:
                            job_detail["application_method"] = app_section[0].text.replace("Način prijave", "").strip()
                            print(f"Application method: {job_detail['application_method']}")
                        else:
                            job_detail["application_method"] = ""
                            print("No application method found")
                    except Exception as e:
                        print(f"Warning: Could not get application method: {str(e)}")
                        job_detail["application_method"] = ""
                    
                    # Process contact info
                    try:
                        contact_section = driver.find_elements(By.CSS_SELECTOR, ".section-kontakt")
                        if contact_section:
                            job_detail["contact_info"] = contact_section[0].text.replace("Kontakt za kandidata", "").strip()
                            print(f"Contact info: {job_detail['contact_info'][:50]}..." if len(job_detail['contact_info']) > 50 else f"Contact info: {job_detail['contact_info']}")
                        else:
                            job_detail["contact_info"] = ""
                            print("No contact info found")
                    except Exception as e:
                        print(f"Warning: Could not get contact info: {str(e)}")
                        job_detail["contact_info"] = ""
                    
                    # Process location - updated to handle location extraction more reliably
                    try:
                        location_div = driver.find_elements(By.CSS_SELECTOR, ".info-title.vacancies-name-detail")
                        if location_div:
                            location_text = location_div[0].text.strip()
                            if "|" in location_text:
                                location = location_text.split("|")[1].strip()
                                # Clean up location by removing the map marker icon text if present
                                if "map-marker-alt" in location:
                                    location = location.replace("map-marker-alt", "").strip()
                                job_detail["location"] = location
                                print(f"Location: {location}")
                            else:
                                job_detail["location"] = ""
                                print("No location found in title")
                        else:
                            job_detail["location"] = ""
                            print("No location div found")
                    except Exception as e:
                        print(f"Warning: Could not get location: {str(e)}")
                        job_detail["location"] = ""
                    
                    # Mark as successful if we got this far
                    success = True
                    
                    # Click back to list
                    print("Clicking back to list...")
                    try:
                        back_buttons = driver.find_elements(By.CSS_SELECTOR, "a.mobile-link")
                        if back_buttons:
                            driver.execute_script("arguments[0].click();", back_buttons[0])
                            print("Clicked back button")
                        else:
                            print("Back button not found, trying alternate method")
                            # Try alternate method - close button
                            close_buttons = driver.find_elements(By.CSS_SELECTOR, "div[aria-label='Close']")
                            if close_buttons:
                                driver.execute_script("arguments[0].click();", close_buttons[0])
                                print("Clicked close button")
                            else:
                                print("Close button not found, trying browser back")
                                driver.back()
                                print("Used browser back button")
                    except Exception as e:
                        print(f"Warning: Could not click back to list: {str(e)}")
                        # If we can't click back, try refreshing the page
                        driver.refresh()
                        print("Refreshed page instead")
                    
                    # Wait for the list to reload
                    try:
                        WebDriverWait(driver, 10).until(
                            EC.presence_of_element_located((By.CSS_SELECTOR, ".list-group-item"))
                        )
                        print("List reloaded successfully")
                    except Exception as e:
                        print(f"Warning: Wait for list reload failed: {str(e)}")
                        # If we can't wait for the list, try refreshing the page
                        driver.refresh()
                        WebDriverWait(driver, 10).until(
                            EC.presence_of_element_located((By.CSS_SELECTOR, ".list-group-item"))
                        )
                        print("Refreshed page and list reloaded")
                    
                    # Wait a moment to ensure we're back to the list
                    time.sleep(2)
                    
                except Exception as e:
                    print(f"Error processing job {index+1}: {str(e)}")
                    
                    # If we encountered an error, try to get back to the listing page
                    try:
                        driver.get(self.base_url)
                        print("Recovered by reloading base URL")
                        WebDriverWait(driver, 10).until(
                            EC.presence_of_element_located((By.CLASS_NAME, "list-group-item"))
                        )
                        time.sleep(3)
                    except Exception as recovery_error:
                        print(f"Failed to recover: {str(recovery_error)}")
                
                finally:
                    # Add the job detail to our collection regardless of success
                    # This ensures we capture whatever data we managed to get
                    if job_detail and job_detail["title"] != "Unknown":
                        job_data.append(job_detail)
                        print(f"Added job data for {job_detail['title']}")
                        if success:
                            print("Job processed successfully")
                        else:
                            print("Job added with partial data")
            
            print(f"\nCompleted processing {len(job_data)} jobs")
            if job_data:
                print(f"First job title: {job_data[0]['title']}")
                print(f"Last job title: {job_data[-1]['title']}")
            
            return job_data
            
        except Exception as e:
            print(f"Fatal error in Selenium scraping: {e}")
            import traceback
            traceback.print_exc()
            return []
        finally:
            try:
                driver.quit()
            except:
                pass

def main():
    try:
        print("=== Starting scraper with improved error handling ===")
        print("Python version:", sys.version)
        print("Selenium version:", selenium.__version__)
        
        # Check internet connectivity first
        try:
            requests.get("https://www.google.com", timeout=5)
            print("Internet connection test: SUCCESS")
        except Exception as e:
            print(f"Internet connection test: FAILED - {str(e)}")
        
        scraper = ESSJobScraper()
        
        # Use Selenium to get ALL detailed job data (no limit)
        print("\nStarting job scraping with no limit (scraping all available jobs)")
        
        # Add retry mechanism for the entire scraping process
        max_retries = 3
        for retry in range(max_retries):
            try:
                detailed_job_data = scraper.scrape_jobs_with_selenium(limit=None)
                
                if detailed_job_data and len(detailed_job_data) > 0:
                    today = datetime.now().strftime('%Y%m%d')
                    batch_file = f"detailed_jobs_{today}.json"
                    with open(batch_file, 'w', encoding='utf-8') as f:
                        json.dump(detailed_job_data, f, ensure_ascii=False, indent=2)
                    print(f"Saved {len(detailed_job_data)} detailed job listings to {batch_file}")
                    break
                else:
                    print(f"No job data returned from attempt {retry+1}/{max_retries}")
                    if retry < max_retries - 1:
                        print("Waiting 60 seconds before next attempt...")
                        time.sleep(60)
            except Exception as e:
                print(f"Error during scraping attempt {retry+1}/{max_retries}: {e}")
                if retry < max_retries - 1:
                    print("Waiting 60 seconds before next attempt...")
                    time.sleep(60)
        else:
            print("All retry attempts failed. No job data could be collected.")
            return 1
        
        return 0
        
    except Exception as e:
        print(f"Fatal error in main function: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main()) 