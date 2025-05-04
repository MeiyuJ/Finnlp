import requests
from bs4 import BeautifulSoup
import os
import re
from datetime import datetime
import json
import csv

BASE_URL = "https://www.federalreserve.gov"
SPEECH_URL_TEMPLATE = BASE_URL + "/newsevents/speech/{}-speeches.htm"
YEARS = ["2018", "2019", "2024", "2025"]
OUTPUT_DIR = "./data/fed_speeches"
CSV_METADATA_FILE = os.path.join(OUTPUT_DIR, "speech_metadata.csv")
JSON_METADATA_FILE = os.path.join(OUTPUT_DIR, "speech_metadata.json")

os.makedirs(OUTPUT_DIR, exist_ok=True)

with open(CSV_METADATA_FILE, "w", newline="", encoding="utf-8") as f:
    writer = csv.writer(f)
    writer.writerow(["Year", "Date", "Title", "Speaker", "Location", "URL", "Filepath", "Word Count"])

all_metadata = []

def fetch_soup(url):
    res = requests.get(url)
    res.raise_for_status()
    return BeautifulSoup(res.text, "html.parser")

def extract_speech_links(year):
    url = SPEECH_URL_TEMPLATE.format(year)
    soup = fetch_soup(url)
    speeches = []
    for link in soup.find_all("a", href=True):
        href = link["href"]
        if "/newsevents/speech/" in href and href.endswith(".htm"):
            full_url = BASE_URL + href if href.startswith("/") else href
            speeches.append({
                "year": year,
                "url": full_url,
                "title": link.get_text(strip=True) or "Untitled"
            })
    return speeches

def extract_speech_content(speech):
    url = speech["url"]
    res = requests.get(url)
    res.raise_for_status()
    soup = BeautifulSoup(res.text, "html.parser")

    title = speech["title"]
    year = speech["year"]
    date_match = re.search(r'(\d{8})', url)
    date = None
    if date_match:
        try:
            date = datetime.strptime(date_match.group(1), '%Y%m%d').strftime('%Y-%m-%d')
        except:
            pass

    speaker = None
    for p in soup.find_all("p"):
        text = p.get_text(strip=True)
        if re.search(r'^(Governor|Chair|Vice Chair|President)', text):
            speaker = text
            break

    location = None
    for p in soup.find_all("p"):
        if "at" in p.get_text(strip=True).lower():
            location = p.get_text(strip=True)
            break

    # Grab all paragraphs
    paragraphs = [p.get_text(separator=" ", strip=True) for p in soup.find_all("p")]

    # Narrow down to relevant section
    start_keywords = [
        "Resources for Consumers"
    ]
    end_keywords = [
        "1. ",
        "Board of Governorsof theFederal Reserve System",
        "Board of Governors of the Federal Reserve System"
    ]

    # Find the range of interest
    start_idx, end_idx = 0, len(paragraphs)
    for i, para in enumerate(paragraphs):
        if any(k in para for k in start_keywords):
            start_idx = i+1
            break
    for i, para in enumerate(paragraphs[start_idx:], start=start_idx):
        if any(k in para for k in end_keywords):
            end_idx = i
            break

    filtered_paragraphs = paragraphs[start_idx:end_idx]
    text = "\n\n".join(filtered_paragraphs)

    # text = "\n\n".join(p.get_text(strip=True) for p in paragraphs)
    word_count = len(text.split())

    safe_title = re.sub(r'[^\w\-]', '_', title[:30])
    date_part = date.replace("-", "") if date else "unknown"
    filename = f"{date_part}_{safe_title}.txt"
    year_dir = os.path.join(OUTPUT_DIR, year)
    os.makedirs(year_dir, exist_ok=True)
    filepath = os.path.join(year_dir, filename)

    with open(filepath, "w", encoding="utf-8") as f:
        # f.write(f"Title: {title}\nDate: {date}\nSpeaker: {speaker}\nLocation: {location}\nURL: {url}\nWord Count: {word_count}\n\n")
        f.write(text)

    with open(CSV_METADATA_FILE, "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([year, date, title, speaker, location, url, filepath, word_count])

    return {
        "year": year,
        "date": date,
        "title": title,
        "speaker": speaker,
        "location": location,
        "url": url,
        "filepath": filepath,
        "word_count": word_count
    }

def run():
    for year in YEARS:
        speeches = extract_speech_links(year)
        for speech in speeches:
            metadata = extract_speech_content(speech)
            all_metadata.append(metadata)

    with open(JSON_METADATA_FILE, "w", encoding="utf-8") as f:
        json.dump(all_metadata, f, indent=2)

if __name__ == "__main__":
    run()

