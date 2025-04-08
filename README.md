# MojeDelo.com Job Scraper

This project automatically scrapes job listings from MojeDelo.com that were posted today. It runs daily using GitHub Actions and saves the results to JSON files.

## Features

- Scrapes jobs posted today ("danes") from MojeDelo.com
- Checks up to 15 pages of listings
- Saves results in JSON format with date in filename
- Runs automatically every day at midnight via GitHub Actions
- Commits and pushes results to the repository

## Setup

1. Fork this repository
2. Enable GitHub Actions in your fork
3. Set up the following secrets in your repository settings:
   - GEMINI_API_KEY
   - SUPABASE_URL
   - SUPABASE_KEY
4. The scraper will run automatically every day at 18:00 UTC

## Manual Usage

To run the scraper manually:

```bash
pip install -r requirements.txt
python scraper.py
```

## Output

The scraper generates JSON files named `jobs_YYYYMMDD.json` containing:
- Job title
- Company name
- Posted date
- Scraped timestamp

## Requirements

- Python 3.9+
- requests
- beautifulsoup4
- python-dotenv
- schedule

## Note

The scraper respects the website's robots.txt and includes appropriate delays between requests. Please use responsibly and in accordance with the website's terms of service. # mojedelodailyscraper
