import requests
from bs4 import BeautifulSoup
import os
import re
from datetime import datetime

BASE_URL = "https://www.federalreserve.gov"
CALENDAR_URL = f"{BASE_URL}/monetarypolicy/fomccalendars.htm"
TARGET_YEARS = {'2018', '2019', '2024', '2025'}
OUTPUT_DIR = "./data/fomc_minutes"

os.makedirs(OUTPUT_DIR, exist_ok=True)

def fetch_calendar_page():
    response = requests.get(CALENDAR_URL)
    response.raise_for_status()
    return BeautifulSoup(response.text, "html.parser")

def extract_meeting_links_flexible(soup):
    links = []
    for a in soup.find_all("a", href=True):
        href = a["href"]
        if re.match(r"^/monetarypolicy/fomcminutes\d{8}\.htm$", href):
            date_str = re.search(r'(\d{8})', href).group(1)
            year = date_str[:4]
            if year in TARGET_YEARS:
                full_url = BASE_URL + href
                links.append((year, full_url))
    return links

def clean_minutes_text(raw_html):
    soup = BeautifulSoup(raw_html, "html.parser")
    
    # Grab all paragraphs
    paragraphs = [p.get_text(separator=" ", strip=True) for p in soup.find_all("p")]
    
    # Join them back into a single string with paragraph breaks
    full_text = "\n\n".join(paragraphs)

    # Narrow down to relevant section
    start_keywords = [
        "Developments in Financial Markets and Open Market Operations",
        "Staff Review of the Economic Situation"
    ]
    end_keywords = [
        "Voting for this action", 
        "Committee Policy Actions", 
        "Directive", 
        "Statement"
    ]

    # Find the range of interest
    start_idx, end_idx = 0, len(paragraphs)
    for i, para in enumerate(paragraphs):
        if any(k in para for k in start_keywords):
            start_idx = i
            break
    for i, para in enumerate(paragraphs[start_idx:], start=start_idx):
        if any(k in para for k in end_keywords):
            end_idx = i
            break

    filtered_paragraphs = paragraphs[start_idx:end_idx]
    cleaned_text = "\n\n".join(filtered_paragraphs)

    return cleaned_text

def scrape_historical_minutes(year):
    assert 2015 <= int(year) <= 2019, "Historical scraper supports years before 2020 only"
    url = f"https://www.federalreserve.gov/monetarypolicy/fomchistorical{year}.htm"
    
    try:
        res = requests.get(url)
        res.raise_for_status()
        soup = BeautifulSoup(res.text, "html.parser")
        
        links = []
        for a in soup.find_all("a", href=True):
            href = a["href"]
            if re.match(r"^/monetarypolicy/fomcminutes\d{8}\.htm$", href):
                full_url = BASE_URL + href
                date_str = full_url.split("/")[-1].replace(".htm", "")
                links.append((year, full_url, date_str))
        
        print(f"Found {len(links)} links for {year}.")
        
        for y, link, date_str in links:
            try:
                res = requests.get(link)
                res.raise_for_status()
                cleaned_text = clean_minutes_text(res.text)
                
                filename = f"{OUTPUT_DIR}/minutes_{y}_{date_str}.txt"
                with open(filename, "w", encoding="utf-8") as f:
                    f.write(cleaned_text)
                print(f"Saved: {filename}")
            except Exception as e:
                print(f"Failed to fetch {link}: {e}")
    
    except Exception as e:
        print(f"Failed to load archive for {year}: {e}")

def scrape_minutes(year_url_pairs):
    for year, url in year_url_pairs:
        try:
            res = requests.get(url)
            res.raise_for_status()
            text = clean_minutes_text(res.text)
            
            # Save
            date_str = url.split("/")[-1].replace(".htm", "")
            filename = f"{OUTPUT_DIR}/minutes_{year}_{date_str}.txt"
            with open(filename, "w", encoding="utf-8") as f:
                f.write(text)
            print(f"Saved: {filename}")
        except Exception as e:
            print(f"Failed to scrape {url}: {e}")

if __name__ == "__main__":
    # For recent (2021–2025)
    soup = fetch_calendar_page()
    recent_links = extract_meeting_links_flexible(soup)
    print(f"Found {len(recent_links)} meeting minutes.")
    scrape_minutes(recent_links)

    # For historical (2018–2020)
    for y in ['2018', '2019']:
        scrape_historical_minutes(y)
