import requests
from bs4 import BeautifulSoup
import json
from datetime import datetime
import os
from typing import List, Dict
import time

class MojeDeloScraper:
    def __init__(self):
        self.base_url = "https://www.mojedelo.com/prosta-delovna-mesta/vsa-podrocja"
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

    def get_job_details(self, job_url: str) -> Dict:
        """Fetch and parse detailed job information from the job's page."""
        html_content = self.get_page_content(job_url)
        if not html_content:
            return {}
        
        soup = BeautifulSoup(html_content, 'html.parser')
        details = {}
        
        try:
            # Get all text content from the job details section
            job_details = soup.find('div', class_='job-description')
            if job_details:
                # Get all text content from the job description
                description_text = []
                for element in job_details.find_all(['p', 'div', 'h2', 'h3', 'h4', 'ul', 'li']):
                    text = element.get_text(strip=True)
                    if text:
                        description_text.append(text)
                details['full_description'] = '\n'.join(description_text)
            
            # Get company info
            company_info = soup.find('div', class_='w-col-4')
            if company_info:
                company_name = company_info.find('strong')
                if company_name:
                    details['company_full_name'] = company_name.get_text(strip=True)
                
                company_address = company_info.find('span', class_='address')
                if company_address:
                    details['company_address'] = company_address.get_text(strip=True)
                
                company_website = company_info.find('a', target='_blank')
                if company_website:
                    details['company_website'] = company_website.get('href', '')
            
            # Get company size and industry
            company_size = soup.find('div', string='Število zaposlenih:')
            if company_size:
                details['company_size'] = company_size.find_next('div').get_text(strip=True)
            
            industry = soup.find('div', string='Dejavnost:')
            if industry:
                details['industry'] = industry.find_next('div').get_text(strip=True)
            
            # Get job type and contract type
            job_type = soup.find('div', string='Tip zaposlitve:')
            if job_type:
                details['job_type'] = job_type.find_next('div').get_text(strip=True)
            
            contract_type = soup.find('div', string='Tip pogodbe:')
            if contract_type:
                details['contract_type'] = contract_type.find_next('div').get_text(strip=True)
            
            # Get education level and experience
            education = soup.find('div', string='Izobrazba:')
            if education:
                details['education_level'] = education.find_next('div').get_text(strip=True)
            
            experience = soup.find('div', string='Izkušnje:')
            if experience:
                details['experience'] = experience.find_next('div').get_text(strip=True)
            
            # Get salary info if available
            salary = soup.find('div', string='Plačilo:')
            if salary:
                details['salary'] = salary.find_next('div').get_text(strip=True)
            
        except Exception as e:
            print(f"Error parsing job details: {e}")
        
        return details

    def parse_job_cards(self, html_content: str) -> List[Dict]:
        """Parse job cards from the HTML content."""
        soup = BeautifulSoup(html_content, 'html.parser')
        jobs = []
        
        # Find all job cards (both regular and premium)
        job_cards = soup.find_all(['a', 'div'], class_=['w-inline-block job-ad deluxe w-clearfix', 'w-inline-block job-ad top w-clearfix'])
        
        for card in job_cards:
            try:
                # Get the job URL
                if card.name == 'a':
                    job_url = card.get('href', '')
                else:
                    job_url = card.find('a', class_='details overlayOnHover1').get('href', '')
                
                if not job_url.startswith('http'):
                    job_url = f"https://www.mojedelo.com{job_url}"
                
                # Find the posted date
                date_div = card.find('div', class_='boxItemGroup').find('div', class_='detail')
                posted_date = date_div.text.strip() if date_div else ""
                
                # Only process jobs posted today
                if posted_date.lower() == "danes":
                    # Get job title
                    title = card.find('h2', class_='title').text.strip()
                    
                    # Get company name
                    company_div = card.find('div', class_='boxName').find('div', class_='detail')
                    company = company_div.text.strip() if company_div else ""
                    
                    # Get location
                    location_div = card.find_all('div', class_='boxItemGroup')[2].find('div', class_='detail')
                    location = location_div.text.strip() if location_div else ""
                    
                    # Get job description preview
                    description_preview = card.find('p', class_='premiumDescription')
                    description_preview = description_preview.text.strip() if description_preview else ""
                    
                    # Get detailed job information
                    print(f"Fetching details for: {title}")
                    details = self.get_job_details(job_url)
                    
                    # Add a small delay to be respectful to the server
                    time.sleep(1)
                    
                    job_data = {
                        'title': title,
                        'company': company,
                        'location': location,
                        'posted_date': posted_date,
                        'description_preview': description_preview,
                        'job_url': job_url,
                        'scraped_at': datetime.now().isoformat(),
                        **details  # Add all the detailed information
                    }
                    
                    jobs.append(job_data)
            except Exception as e:
                print(f"Error parsing job card: {e}")
                continue
                
        return jobs

    def scrape_todays_jobs(self, page: int) -> List[Dict]:
        """
        Scrape jobs from a specific page.
        This method is not used - remove it.
        """
        # Delete this entire method - it's not used

def main():
    scraper = MojeDeloScraper()
    all_jobs = []
    batch_size = 4  # pages per batch
    batch_number = 1
    current_page = 1
    today = datetime.now().strftime('%Y%m%d')
    max_pages = 22  # Maximum number of pages to scrape

    try:
        while current_page <= max_pages:
            # Calculate end page for this batch (don't exceed max_pages)
            end_page = min(current_page + batch_size - 1, max_pages)
            
            print(f"\nProcessing pages {current_page} to {end_page}")
            batch_jobs = []
            
            # Flag to track if we found any "danes" jobs in this batch
            found_today_jobs = False
            
            # Scrape a batch of pages
            for page_num in range(current_page, end_page + 1):
                print(f"Scraping page {page_num}...")
                url = f"{scraper.base_url}?p={page_num}" if page_num > 1 else scraper.base_url
                html_content = scraper.get_page_content(url)
                
                if not html_content:
                    raise StopIteration
                    
                jobs_on_page = scraper.parse_job_cards(html_content)
                if jobs_on_page:  # If we found any jobs on this page
                    found_today_jobs = True  # We found "danes" jobs (parse_job_cards only returns "danes" jobs)
                    batch_jobs.extend(jobs_on_page)
                time.sleep(1)  # Be nice to the server
            
            # If we didn't find any "danes" jobs in this batch, stop scraping
            if not found_today_jobs:
                print("No more jobs from today found, stopping scraper")
                break
            
            # Save batch to separate file if we have jobs
            if batch_jobs:
                batch_file = f"jobs_raw_{today}_batch{batch_number}.json"
                with open(batch_file, 'w', encoding='utf-8') as f:
                    json.dump(batch_jobs, f, ensure_ascii=False, indent=2)
                print(f"Saved batch {batch_number} with {len(batch_jobs)} jobs to {batch_file}")
                
                all_jobs.extend(batch_jobs)
                batch_number += 1
                current_page = end_page + 1  # Move to the next batch
            
            # Exit the loop if we've reached max_pages
            if current_page > max_pages:
                print(f"Reached maximum page limit ({max_pages})")
                break
            
    except StopIteration:
        pass
    except Exception as e:
        print(f"Error during scraping: {e}")
    
    print(f"\nTotal jobs found: {len(all_jobs)}")
    print(f"Total batches created: {batch_number - 1}")
    return batch_number - 1  # Return number of batches created

if __name__ == "__main__":
    main() 