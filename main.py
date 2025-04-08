import os
from datetime import datetime
import time
from scraper import main as scraper_main
from analyze_jobs import main as analyze_main
from upload_to_supabase import upload_to_supabase
import json

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
    today = datetime.now().strftime('%Y%m%d')
    analyzed_file = f"jobs_analyzed_{today}.json"
    
    try:
        # Step 1: Run the scraper (now returns number of batches created)
        print("\n=== Starting scraper ===")
        num_batches = scraper_main()
        if num_batches == 0:
            print("No job batches were created. Exiting.")
            return 0
        print("Scraping completed successfully")
        
        # Step 2: Run the analyzer (processes all batches)
        print("\n=== Starting analysis ===")
        api_key = os.getenv('GEMINI_API_KEY')
        if not api_key:
            raise Exception("GEMINI_API_KEY environment variable not set")
        
        analyze_main()  # This will handle batch processing internally
        
        if not os.path.exists(analyzed_file):
            raise Exception(f"Analysis failed to create {analyzed_file}")
            
        # Verify that the analyzed file contains valid JSON
        try:
            with open(analyzed_file, 'r', encoding='utf-8') as f:
                analyzed_jobs = json.load(f)
            if not analyzed_jobs or not isinstance(analyzed_jobs, list):
                raise Exception("Analyzed jobs file contains invalid or empty data")
            print(f"Analysis completed successfully with {len(analyzed_jobs)} jobs")
        except json.JSONDecodeError:
            raise Exception("Analyzed jobs file contains invalid JSON")
        
        # Step 3: Upload to Supabase
        print("\n=== Starting Supabase upload ===")
        upload_to_supabase(analyzed_file)
        print("Upload completed successfully")
        
        # Step 4: Cleanup all files
        print("\n=== Cleaning up files ===")
        cleanup_files(today, num_batches)
        print("Cleanup completed")
        
        print("\n=== All tasks completed successfully ===")
        
    except Exception as e:
        print(f"\nError in workflow: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main()) 