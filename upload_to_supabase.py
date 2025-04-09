import json
from datetime import datetime
import os
from supabase import create_client
from typing import Dict, Any
import random

def upload_to_supabase(analyzed_file: str) -> None:
    """Upload analyzed jobs to Supabase table."""
    try:
        # Load the analyzed jobs data with UTF-8 encoding
        with open(analyzed_file, 'r', encoding='utf-8') as f:
            try:
                jobs = json.load(f)
                if not isinstance(jobs, list):
                    jobs = []
            except json.JSONDecodeError:
                print("Error reading jobs file, starting with empty list")
                jobs = []
        
        # Configure Supabase client with proper encoding
        supabase_url = os.getenv('SUPABASE_URL')
        supabase_key = os.getenv('SUPABASE_KEY')
        
        if not supabase_url or not supabase_key:
            print("Error: SUPABASE_URL and SUPABASE_KEY environment variables must be set")
            return
            
        supabase = create_client(supabase_url, supabase_key)
        
        successful_uploads = 0
        total_jobs = len(jobs)
        
        # Upload each job to Supabase
        for index, job in enumerate(jobs):
            try:
                formatted_job = format_job_for_upload(job, index)
                
                # Insert into Supabase table
                result = supabase.table('jobs').insert(formatted_job).execute()
                successful_uploads += 1
                print(f"Uploaded job {index + 1}/{total_jobs}: {formatted_job['job_id']} - {formatted_job['title']}")
                
            except Exception as e:
                print(f"Failed to upload job {index + 1}/{total_jobs}: {str(e)}")
                continue
        
        print(f"\nUpload Summary:")
        print(f"Total jobs processed: {total_jobs}")
        print(f"Successfully uploaded: {successful_uploads}")
        print(f"Failed uploads: {total_jobs - successful_uploads}")
        
    except Exception as e:
        print(f"Error during upload process: {str(e)}")

def safe_strip(value: Any) -> str:
    """Safely convert any value to a stripped string while preserving special characters."""
    if value is None:
        return ""
    try:
        # Convert to string and strip whitespace while preserving special characters
        return str(value).strip()
    except:
        return ""

def format_job_for_upload(job: Dict[str, Any], index: int) -> Dict[str, Any]:
    """Format job data to match the Supabase table schema exactly."""
    
    def safe_list(value: Any) -> list:
        """Safely convert any value to a list while preserving special characters."""
        if isinstance(value, list):
            return [str(item) for item in value if item is not None]
        return []
    
    def safe_dict(value: Any) -> dict:
        """Safely convert any value to a dict."""
        if isinstance(value, dict):
            return value
        return {}
    
    # Create a unique ID based on date and sequence number
    today = datetime.now().strftime('%Y%m%d')
    unique_id = f"zavod_{today}_{index + 1}"  # e.g., zavod_20240404_1
    
    try:
        # Handle dates
        posted_date = job.get('posted_date', '')
        if not posted_date or not isinstance(posted_date, str):
            posted_date = today
            
        application_deadline = job.get('application_deadline')
        if not application_deadline or not isinstance(application_deadline, str):
            application_deadline = None
            
        # Format the job data with proper character encoding
        formatted_job = {
            'id': unique_id,  # Use the same unique_id here
            'title': safe_strip(job.get('title')) or 'Untitled Position',
            'company': safe_strip(job.get('company')) or 'Unknown Company',
            'location': safe_strip(job.get('location')) or 'Slovenia',
            'town_location': safe_strip(job.get('town_location')) or '',
            'posted_date': posted_date,
            'application_deadline': application_deadline,
            'job_url': safe_strip(job.get('job_url')) or '',
            'work_mode': safe_strip(job.get('work_mode')) or 'Not specified',
            'industry': safe_strip(job.get('industry')) or '',
            
            # JSONB fields with guaranteed structure
            'compensation': safe_dict(job.get('compensation')),
            'company_info': safe_dict(job.get('company_info')),
            
            # String fields with empty string fallbacks
            'employment_type': safe_strip(job.get('employment_type')),
            'department_size': safe_strip(job.get('department_size')),
            'application_method': safe_strip(job.get('application_method')),
            
            # Array fields with empty list fallbacks
            'required_qualifications': safe_list(job.get('required_qualifications')),
            'preferred_qualifications': safe_list(job.get('preferred_qualifications')),
            'responsibilities': safe_list(job.get('responsibilities')),
            'benefits': safe_list(job.get('benefits')),
            'key_skills': safe_list(job.get('key_skills')),
            'languages': safe_list(job.get('languages'))
        }
        
        return formatted_job
        
    except Exception as e:
        # If anything goes wrong, return a valid but empty job record
        print(f"Error formatting job {index + 1}, using fallback data: {str(e)}")
        return {
            'id': unique_id,  # Still use the unique_id even in error case
            'title': 'Error Processing Job',
            'company': 'Unknown Company',
            'location': 'Slovenia',
            'town_location': '',
            'posted_date': today,
            'application_deadline': None,
            'job_url': '',
            'work_mode': 'Not specified',
            'industry': '',
            'compensation': {},
            'company_info': {},
            'employment_type': '',
            'required_qualifications': [],
            'preferred_qualifications': [],
            'responsibilities': [],
            'benefits': [],
            'department_size': '',
            'key_skills': [],
            'languages': [],
            'application_method': ''
        }

def main():
    # Get the analyzed jobs file
    today = datetime.now().strftime('%Y%m%d')
    analyzed_file = f"jobs_analyzed_{today}.json"
    if not os.path.exists(analyzed_file):
        print(f"Error: Analyzed jobs file {analyzed_file} not found")
        return
    
    upload_to_supabase(analyzed_file)

if __name__ == "__main__":
    main() 