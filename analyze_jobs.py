import json
import google.generativeai as genai
from datetime import datetime
import os

def analyze_with_gemini(batch_file: str, api_key: str) -> list:
    """Analyze a batch of job postings using Gemini API."""
    try:
        # Load the batch of jobs with proper UTF-8 encoding
        with open(batch_file, 'r', encoding='utf-8') as f:
            jobs = json.load(f)
        
        # Clean the job data while preserving special characters
        cleaned_jobs = []
        for job in jobs:
            # Create a new clean job object
            clean_job = {}
            for key, value in job.items():
                if isinstance(value, str):
                    # Only remove control characters while preserving special chars
                    clean_value = ''.join(char for char in value if ord(char) >= 32)
                    clean_job[key] = clean_value
                else:
                    clean_job[key] = value
            cleaned_jobs.append(clean_job)
        
        # Configure Gemini
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-2.0-flash')
        
        # More direct prompt that focuses on schema and valid JSON
        standardization_prompt = """
        Reformat these job listings into the following schema. Return ONLY valid JSON with no explanations:

        [
          {
            "job_id": "unique identifier or empty string",
            "title": "job title",
            "company": "company name",
            "location": "city/location",
            "posted_date": "2025-04-04", 
            "application_deadline": "YYYY-MM-DD or null",
            "job_url": "full URL",
            "work_mode": "On-site/Remote/Hybrid",
            "compensation": {
              "salary_range": "",
              "benefits_package": ""
            },
            "company_info": {
              "size": "",
              "industry": "",
              "years_active": "",
              "business_scale": ""
            },
            "employment_type": "",
            "required_qualifications": [],
            "preferred_qualifications": [],
            "responsibilities": [],
            "benefits": [],
            "department_size": "",
            "key_skills": [],
            "languages": [],
            "application_method": ""
          }
        ]
        
        IMPORTANT STANDARDIZATION RULES:
        
        1. For "location", only use ONE of these standardized region names (match to the closest region):
        Gorenjska, Goriška, Jugovzhodna Slovenija, Koroška, Notranjsko-kraška, Obalno-kraška, Osrednjeslovenska, 
        Podravska, Pomurska, Savinjska, Spodnjeposavska, Zasavska, Tujina, Remote
        
        2. For "company_info.industry", only use ONE of these standardized industry categories:
        Administracija
        Arhitektura, Gradbeništvo, Geodezija
        Bančništvo, Finance
        Elektrotehnika, Elektronika, Telekomunikacije
        Farmacija, Naravoslovje
        Gostinstvo, Turizem
        Informatika, Programiranje
        Kadrovanje
        Agronomija, Gozdarstvo, Ribištvo, Veterina
        Komerciala, Trženje
        Prehrambena industrija, Živilstvo
        Proizvodnja, Steklarstvo
        Lesarstvo
        Računovodstvo, Revizija
        Socialno in prostovoljno delo
        Strojištvo, Metalurgija, Rudarstvo
        Poučevanje, Prevajanje, Kultura, Šport
        Tehnične storitve, Mehanika
        Kreativa, Design
        Management, Poslovno svetovanje, Organizacija
        Marketing, Oglaševanje, PR
        Novinarstvo, Mediji, Založništvo
        Osebne storitve, Varovanje
        Pravo, Družboslovje
        Transport, Nabava, Logistika
        Trgovina
        Zavarovalništvo, Nepremičnine
        Zdravstvo, Nega
        Znanost, Tehnologija, Raziskave in razvoj
        Drugo
        
        RETURN ONLY THE JSON ARRAY. No markdown formatting.
        """
        
        # Break into smaller chunks if needed - process 5 jobs at a time to avoid context issues
        max_jobs_per_request = 5
        all_analyzed_jobs = []
        
        for i in range(0, len(cleaned_jobs), max_jobs_per_request):
            chunk = cleaned_jobs[i:i+max_jobs_per_request]
            # Convert chunk to plain text to avoid JSON complexity
            jobs_text = "\n\nJOB LISTINGS TO PROCESS:\n\n"
            
            for j, job in enumerate(chunk):
                jobs_text += f"JOB {j+1}:\n"
                for key, value in job.items():
                    jobs_text += f"{key}: {value}\n"
                jobs_text += "\n---\n\n"
            
            full_prompt = standardization_prompt + jobs_text
            
            # First attempt with safety parameters
            response = model.generate_content(full_prompt, generation_config={
                "temperature": 0.1,  # More deterministic
                "top_p": 0.8,
                "top_k": 40
            })
            
            response_text = response.text
            # Remove any markdown formatting
            if "```json" in response_text:
                response_text = response_text.split("```json")[1].split("```")[0].strip()
            elif "```" in response_text:
                response_text = response_text.split("```")[1].split("```")[0].strip()
            
            try:
                chunk_jobs = json.loads(response_text)
                all_analyzed_jobs.extend(chunk_jobs)
                print(f"Successfully processed {len(chunk_jobs)} jobs from {batch_file}")
            except json.JSONDecodeError as e:
                print(f"Error with chunk, trying one-by-one processing for jobs {i} to {i+len(chunk)-1}")
                
                # Process each job individually as a last resort
                for job in chunk:
                    try:
                        single_job_prompt = standardization_prompt + "\n\nJOB TO PROCESS:\n\n" + "\n".join([f"{k}: {v}" for k, v in job.items()])
                        single_response = model.generate_content(single_job_prompt)
                        single_text = single_response.text
                        
                        if "```json" in single_text:
                            single_text = single_text.split("```json")[1].split("```")[0].strip()
                        elif "```" in single_text:
                            single_text = single_text.split("```")[1].split("```")[0].strip()
                        
                        single_job_result = json.loads(single_text)
                        # If it's an array with one job, take the first element
                        if isinstance(single_job_result, list) and len(single_job_result) > 0:
                            all_analyzed_jobs.append(single_job_result[0])
                        else:
                            all_analyzed_jobs.append(single_job_result)
                    except Exception as e:
                        print(f"Failed to process individual job: {str(e)}")
        
        return all_analyzed_jobs
        
    except Exception as e:
        print(f"Error analyzing batch {batch_file}: {e}")
        return []

def main():
    api_key = os.getenv('GEMINI_API_KEY')
    if not api_key:
        print("Error: GEMINI_API_KEY environment variable not set")
        return
    
    today = datetime.now().strftime('%Y%m%d')
    all_analyzed_jobs = []
    batch_number = 1
    
    # Process each batch file
    while True:
        batch_file = f"jobs_raw_{today}_batch{batch_number}.json"
        if not os.path.exists(batch_file):
            break
            
        print(f"\nProcessing batch {batch_number}")
        analyzed_jobs = analyze_with_gemini(batch_file, api_key)
        if analyzed_jobs:
            all_analyzed_jobs.extend(analyzed_jobs)
        batch_number += 1
    
    # Save all analyzed jobs to a single file
    if all_analyzed_jobs:
        output_file = f"jobs_analyzed_{today}.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(all_analyzed_jobs, f, ensure_ascii=False, indent=2)
        print(f"\nAll analyzed jobs saved to: {output_file}")
        print(f"Total jobs analyzed: {len(all_analyzed_jobs)}")

if __name__ == "__main__":
    main() 