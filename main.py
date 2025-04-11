import os
from datetime import datetime
import time
from scraper import main as scraper_main, ESSJobScraper
from analyze_jobs import main as analyze_main
from upload_to_supabase import upload_to_supabase
import json
import sys

def cleanup_files(today: str, num_batches: int):
    """Delete all temporary files."""
    files_to_delete = []
    
    # Add batch files
    for i in range(1, num_batches + 1):
        files_to_delete.append(f"jobs_raw_{today}_batch{i}.json")
    
    # Add analyzed file
    files_to_delete.append(f"jobs_analyzed_{today}.json")
    
    for file in files_to_delete:
        try:
            os.remove(file)
            print(f"Deleted: {file}")
        except Exception as e:
            print(f"Error deleting {file}: {e}")

def main():
    try:
        print("=== Starting scraper ===")
        scraper = ESSJobScraper()
        
        # Use Selenium to get ALL detailed job data (no limit)
        print("\nStarting job scraping with no limit (scraping all available jobs)")
        detailed_job_data = scraper.scrape_jobs_with_selenium(limit=None)
        
        if detailed_job_data and len(detailed_job_data) > 0:
            # Save to JSON file
            today = datetime.now().strftime('%Y%m%d')
            batch_file = f"detailed_jobs_{today}.json"
            with open(batch_file, 'w', encoding='utf-8') as f:
                json.dump(detailed_job_data, f, ensure_ascii=False, indent=2)
            print(f"Saved {len(detailed_job_data)} detailed job listings to {batch_file}")
            
            # Run the analyzer
            print("\n=== Starting analysis ===")
            analyze_main()
            
            # Upload to Supabase
            print("\n=== Starting Supabase upload ===")
            upload_to_supabase(f"jobs_analyzed_{today}.json")
            print("Upload completed successfully")
            
            return 0
        else:
            print("No job data found.")
            return 1
            
    except Exception as e:
        print(f"Error in main function: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main()) 