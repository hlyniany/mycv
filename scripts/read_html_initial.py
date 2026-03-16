"""
Extract CV data from HTML file and convert to JSONResume format.
Initial extraction - adds IT domain to all entries by default.
"""

from bs4 import BeautifulSoup
import json
import re
from datetime import datetime

def parse_date_range(date_str):
    """Parse date range like 'August 2023 - Present' into start/end dates."""
    if not date_str:
        return None, None
    
    date_str = date_str.strip()
    parts = [p.strip() for p in date_str.split('-')]
    
    month_map = {
        'january': '01', 'february': '02', 'march': '03', 'april': '04',
        'may': '05', 'june': '06', 'july': '07', 'august': '08',
        'september': '09', 'october': '10', 'november': '11', 'december': '12'
    }
    
    def parse_single_date(date_part):
        date_part = date_part.strip().lower()
        if 'present' in date_part:
            return None  # Present = no end date
        
        # Try "Month Year" format
        tokens = date_part.split()
        if len(tokens) >= 2:
            month = tokens[0].lower()
            year = tokens[1]
            if month in month_map:
                return f"{year}-{month_map[month]}"
        
        return date_part
    
    start_date = parse_single_date(parts[0]) if len(parts) > 0 else None
    end_date = parse_single_date(parts[1]) if len(parts) > 1 else None
    
    return start_date, end_date

def extract_cv_data(html_file):
    """Extract CV data from HTML file."""
    
    with open(html_file, 'r', encoding='utf-8') as f:
        soup = BeautifulSoup(f.read(), 'html.parser')
    
    cv_data = {
        "$schema": "https://raw.githubusercontent.com/jsonresume/resume-schema/v1.0.0/schema.json",
        "basics": {},
        "work": [],
        "education": [],
        "skills": [],
        "languages": [],
        "interests": [],
        "references": []
    }
    
    # Extract name and summary
    name_elem = soup.find('h1')
    if name_elem:
        cv_data['basics']['name'] = name_elem.get_text(strip=True)
    
    summary_elem = soup.find('p', style=lambda x: x and 'font-size: 18px' in x)
    if summary_elem:
        cv_data['basics']['summary'] = summary_elem.get_text(strip=True)
    
    # Extract contact info
    contact_box = soup.find('div', style=lambda x: x and 'background-color: #f0f0f0' in x)
    if contact_box:
        phone = contact_box.find('strong', string='Phone:')
        if phone:
            cv_data['basics']['phone'] = phone.find_next_sibling(string=True).strip()
        
        email_link = contact_box.find('a', href=lambda x: x and x.startswith('mailto:'))
        if email_link:
            cv_data['basics']['email'] = email_link.get_text(strip=True)
        
        linkedin_link = contact_box.find('a', href=lambda x: x and 'linkedin.com' in x)
        if linkedin_link:
            cv_data['basics']['url'] = linkedin_link.get('href')
        
        address = contact_box.find('strong', string='Address:')
        if address:
            location_text = address.find_next_sibling(string=True).strip()
            cv_data['basics']['location'] = {
                "city": location_text.split(',')[0].strip() if ',' in location_text else location_text,
                "countryCode": "NO"
            }
    
    # Extract experience
    experience_section = None
    for div in soup.find_all('div', style=lambda x: x and 'display: flex' in x):
        label = div.find('p', string=lambda x: x and 'EXPERIENCE' in x)
        if label:
            experience_section = div
            break
    
    if experience_section:
        content_div = experience_section.find('div', style=lambda x: x and 'flex: 1' in x and 'padding-left' in x)
        if content_div:
            for job_div in content_div.find_all('div', style=lambda x: x and 'margin-bottom: 20px' in x, recursive=False):
                h3 = job_div.find('h3')
                if not h3:
                    continue
                
                company = h3.get_text(strip=True)
                
                # Find date range (right side)
                date_p = job_div.find('p', style=lambda x: x and 'color: #666' in x)
                date_str = date_p.get_text(strip=True) if date_p else ""
                
                # Check if it looks like a date or a position
                # Dates typically have months or years with hyphens
                is_date = False
                if date_str and ('-' in date_str or any(month in date_str.lower() for month in ['january', 'february', 'march', 'april', 'may', 'june', 'july', 'august', 'september', 'october', 'november', 'december']) or any(year in date_str for year in ['2000', '2001', '2002', '2003', '2004', '2005', '2006', '2007', '2008', '2009', '2010', '2011', '2012', '2013', '2014', '2015', '2016', '2017', '2018', '2019', '2020', '2021', '2022', '2023', '2024', '2025'])):
                    is_date = True
                
                if is_date:
                    start_date, end_date = parse_date_range(date_str)
                    # Find position (below company name)
                    position_p = job_div.find('p', style=lambda x: x and 'font-style: italic' in x and 'color: #666' not in (x or ''))
                    position = position_p.get_text(strip=True) if position_p else ""
                else:
                    # The "date" field is actually the position (e.g., Armed Forces case)
                    position = date_str
                    start_date, end_date = None, None
                
                # Extract highlights (list items or paragraphs)
                highlights = []
                ul = job_div.find('ul')
                if ul:
                    highlights = [li.get_text(strip=True) for li in ul.find_all('li', recursive=False)]
                else:
                    # Check for paragraph descriptions
                    for p in job_div.find_all('p', recursive=False):
                        text = p.get_text(strip=True)
                        if text and p != date_p and p != position_p and len(text) > 20:
                            highlights.append(text)
                
                work_entry = {
                    "name": company,
                    "position": position,
                    "domains": ["it"]  # Default domain
                }
                
                if start_date:
                    work_entry["startDate"] = start_date
                
                if end_date:
                    work_entry["endDate"] = end_date
                
                if highlights:
                    work_entry["highlights"] = highlights
                
                cv_data['work'].append(work_entry)
    
    # Extract education
    education_section = None
    for div in soup.find_all('div', style=lambda x: x and 'display: flex' in x):
        label = div.find('p', string=lambda x: x and 'EDUCATION' in x)
        if label:
            education_section = div
            break
    
    if education_section:
        content_div = education_section.find('div', style=lambda x: x and 'flex: 1' in x and 'padding-left' in x)
        if content_div:
            # Find all direct child divs (both with and without margin-bottom style)
            for edu_div in content_div.find_all('div', recursive=False):
                h3 = edu_div.find('h3')
                if not h3:
                    continue
                
                institution = h3.get_text(strip=True)
                
                # Find study type and area
                study_p = edu_div.find('p', style=lambda x: x and 'font-style: italic' in x)
                study_text = study_p.get_text(strip=True) if study_p else ""
                
                # Parse "Master's degree, Applied Mathematics"
                study_type = ""
                area = ""
                if ',' in study_text:
                    parts = study_text.split(',', 1)
                    study_type = parts[0].strip()
                    area = parts[1].strip()
                else:
                    area = study_text
                
                # Find date range
                date_paragraphs = edu_div.find_all('p', string=lambda x: x and '-' in str(x) and any(month in str(x).lower() for month in ['january', 'february', 'march', 'april', 'may', 'june', 'july', 'august', 'september', 'october', 'november', 'december']))
                date_str = date_paragraphs[0].get_text(strip=True) if date_paragraphs else ""
                start_date, end_date = parse_date_range(date_str)
                
                edu_entry = {
                    "institution": institution,
                    "area": area,
                    "studyType": study_type,
                    "startDate": start_date,
                    "domains": ["it"]
                }
                
                if end_date:
                    edu_entry["endDate"] = end_date
                
                cv_data['education'].append(edu_entry)
    
    # Extract languages
    languages_section = None
    for div in soup.find_all('div', style=lambda x: x and 'display: flex' in x):
        label = div.find('p', string=lambda x: x and 'LANGUAGES' in x)
        if label:
            languages_section = div
            break
    
    if languages_section:
        content_div = languages_section.find('div', style=lambda x: x and 'flex: 1' in x and 'padding-left' in x)
        if content_div:
            text = content_div.get_text(strip=True)
            # Parse "English (Full professional proficiency), Norwegian (A2)"
            for lang_part in text.split(','):
                lang_part = lang_part.strip()
                match = re.match(r'(\w+)\s*\((.*?)\)', lang_part)
                if match:
                    language = match.group(1)
                    fluency = match.group(2)
                    cv_data['languages'].append({
                        "language": language,
                        "fluency": fluency
                    })
    
    # Extract hobbies/interests
    hobbies_section = None
    for div in soup.find_all('div', style=lambda x: x and 'display: flex' in x):
        label = div.find('p', string=lambda x: x and 'HOBBIES' in x)
        if label:
            hobbies_section = div
            break
    
    if hobbies_section:
        content_div = hobbies_section.find('div', style=lambda x: x and 'flex: 1' in x and 'padding-left' in x)
        if content_div:
            text = content_div.get_text(strip=True)
            # Parse "Snorkeling · Hiking · Cycling"
            hobbies = [h.strip() for h in text.split('·')]
            for hobby in hobbies:
                if hobby:
                    cv_data['interests'].append({"name": hobby})
    
    # Extract recommendations/references
    recommendations_section = None
    for div in soup.find_all('div', style=lambda x: x and 'display: flex' in x):
        label = div.find('p', string=lambda x: x and 'RECOMMEN' in x)
        if label:
            recommendations_section = div
            break
    
    if recommendations_section:
        content_div = recommendations_section.find('div', style=lambda x: x and 'flex: 1' in x and 'padding-left' in x)
        if content_div:
            for p in content_div.find_all('p'):
                text = p.get_text(strip=True)
                if text and not text.startswith('Norwegian') and not text.startswith('other'):
                    # Extract name and reference info
                    if ':' in text:
                        parts = text.split(':', 1)
                        name = parts[0].strip()
                        reference = parts[1].strip() if len(parts) > 1 else ""
                        cv_data['references'].append({
                            "name": name,
                            "reference": reference
                        })
    
    return cv_data

def main():
    html_file = 'docs/VitaliyHlynianyiZhuk2025.html'
    output_file = 'data/cv.resume.json'
    review_file = 'review/cv.resume.json'
    
    print(f"Extracting CV data from {html_file}...")
    cv_data = extract_cv_data(html_file)
    
    # Save to data folder
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(cv_data, f, indent=2, ensure_ascii=False)
    print(f"✓ Saved to {output_file}")
    
    # Save to review folder for manual inspection
    with open(review_file, 'w', encoding='utf-8') as f:
        json.dump(cv_data, f, indent=2, ensure_ascii=False)
    print(f"✓ Saved to {review_file} for review")
    
    # Print summary
    print(f"\n=== Extraction Summary ===")
    print(f"Name: {cv_data['basics'].get('name', 'N/A')}")
    print(f"Email: {cv_data['basics'].get('email', 'N/A')}")
    print(f"Work Experience: {len(cv_data['work'])} positions")
    print(f"Education: {len(cv_data['education'])} entries")
    print(f"Languages: {len(cv_data['languages'])} languages")
    print(f"Interests: {len(cv_data['interests'])} interests")
    print(f"References: {len(cv_data['references'])} references")
    print(f"\n✓ All entries tagged with 'it' domain by default")
    print(f"✓ Review and modify domains in: {review_file}")

if __name__ == '__main__':
    main()
