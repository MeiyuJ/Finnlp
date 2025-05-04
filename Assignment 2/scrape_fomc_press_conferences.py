import os
import re
import requests
from bs4 import BeautifulSoup
from pathlib import Path
from PyPDF2 import PdfReader

BASE_URL = "https://www.federalreserve.gov"
CALENDAR_URL = f"{BASE_URL}/monetarypolicy/fomccalendars.htm"
PDF_DOWNLOAD_DIR = "./data/press_conferences/pdf"
TEXT_OUTPUT_DIR = "./data/press_conferences/text"
TARGET_YEARS = {'2018', '2019', '2024', '2025'}

Path(PDF_DOWNLOAD_DIR).mkdir(parents=True, exist_ok=True)
Path(TEXT_OUTPUT_DIR).mkdir(parents=True, exist_ok=True)

def fetch_soup(url):
    res = requests.get(url)
    res.raise_for_status()
    return BeautifulSoup(res.text, "html.parser")

def extract_pressconf_links_from_calendar(soup):
    links = []
    for a in soup.find_all("a", href=True):
        href = a["href"]
        if re.match(r"^/monetarypolicy/fomcpresconf\d{8}\.htm$", href):
            full_url = BASE_URL + href
            date_str = re.search(r'\d{8}', href).group(0)
            year = date_str[:4]
            if year in TARGET_YEARS:
                links.append((year, full_url, date_str))
    return links

def extract_pdf_from_pressconf_page(url, date_str):
    try:
        soup = fetch_soup(url)
        for a in soup.find_all("a", href=True):
            href = a['href']
            if f"FOMCpresconf{date_str}.pdf" in href or f"fomcpresconf{date_str}.pdf" in href:
                if not href.startswith("http"):
                    href = BASE_URL + href
                return href
    except Exception as e:
        print(f"Failed to parse PDF link from {url}: {e}")
    return None

def download_pdf(pdf_url, save_path):
    try:
        res = requests.get(pdf_url)
        res.raise_for_status()
        with open(save_path, "wb") as f:
            f.write(res.content)
        print(f"Downloaded PDF: {save_path}")
        return True
    except Exception as e:
        print(f"Failed to download PDF: {pdf_url}, error: {e}")
        return False

def extract_text_from_pdf(pdf_path):
    try:
        with open(pdf_path, "rb") as f:
            reader = PdfReader(f)
            text = "\n\n".join(page.extract_text() for page in reader.pages if page.extract_text())
            return text
    except Exception as e:
        print(f"Failed to extract text from {pdf_path}: {e}")
        return ""

def clean_press_conference_text(raw_text):
    # Step 1: Remove page headers and footers
    text = re.sub(r'(?i)Page \d+ of \d+', '', raw_text)
    """
    Removes FOMC press conference headers like:
    'January 31, 2024\nChair Powell’s Press Conference\nFINAL'
    """
    # This regex matches a date, optional whitespace, name/title line, and 'FINAL'
    pattern = r"^(January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},\s+\d{4}\s*\n.*?(Chair(man)? Powell.*|Chair Powell.*)\nFINAL\n?"
    text = re.sub(pattern, '', text, flags=re.IGNORECASE | re.MULTILINE)
    text = re.sub(r'^\s*FOMC.*?\n+', '', text, flags=re.MULTILINE)  # some PDF footers
    text = re.sub(r'\n{3,}', '\n\n', text)  # collapse 3+ linebreaks

    # Step 2: Remove line breaks that are not real paragraph breaks
    # Rule: merge lines if there's only one \n between them
    lines = text.splitlines()
    cleaned_lines = []
    buffer = []

    for line in lines:
        line = line.strip()
        if not line:
            if buffer:
                cleaned_lines.append(" ".join(buffer))
                buffer = []
            cleaned_lines.append("")  # Paragraph break
        else:
            buffer.append(line)

    if buffer:
        cleaned_lines.append(" ".join(buffer))

    # Step 3: Collapse multiple empty lines into one
    cleaned_text = "\n\n".join([line for line in cleaned_lines if line.strip() != ""])

    # Optional: remove footnote indicators like "1 Chairman Powell intended..."
    cleaned_text = re.sub(r'\s*\d+\s+Chairman Powell.*?$', '', cleaned_text, flags=re.MULTILINE)

    return cleaned_text

def process_press_conference(year, link, date_str):
    pdf_url = extract_pdf_from_pressconf_page(link, date_str)
    if not pdf_url:
        print(f"No PDF link found for {link}")
        return

    pdf_filename = f"press_{date_str}.pdf"
    txt_filename = f"press_{date_str}.txt"
    pdf_path = os.path.join(PDF_DOWNLOAD_DIR, pdf_filename)
    txt_path = os.path.join(TEXT_OUTPUT_DIR, txt_filename)

    if download_pdf(pdf_url, pdf_path):
        text = extract_text_from_pdf(pdf_path)
        cleaned_text = clean_press_conference_text(text)
        with open(txt_path, "w", encoding="utf-8") as f:
            f.write(cleaned_text)
        print(f"Saved text: {txt_path}")

def scrape_press_conferences():
    # Step 1: Recent years
    soup = fetch_soup(CALENDAR_URL)
    links = extract_pressconf_links_from_calendar(soup)

    # Step 2: Historical years
    for y in ['2018', '2019']:
        hist_url = f"{BASE_URL}/monetarypolicy/fomchistorical{y}.htm"
        hist_soup = fetch_soup(hist_url)
        links += extract_pressconf_links_from_calendar(hist_soup)

    print(f"Found {len(links)} press conference links.")

    # Step 3: Process each press conf
    for year, link, date_str in links:
        process_press_conference(year, link, date_str)

if __name__ == "__main__":
    scrape_press_conferences()
