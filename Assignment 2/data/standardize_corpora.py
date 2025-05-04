import os
import re
import json
import csv
from pathlib import Path
from datetime import datetime

def read_text(filepath):
    with open(filepath, "r", encoding="utf-8") as f:
        return f.read()

def parse_date_from_filename(filename):
    match = re.search(r'\d{8}', filename)
    if match:
        try:
            return datetime.strptime(match.group(), "%Y%m%d").date().isoformat()
        except:
            return None
    return None

def standardize_minutes(root_dir):
    entries = []
    for file in Path(root_dir).glob("*.txt"):
        text = read_text(file)
        date = parse_date_from_filename(file.name)
        entries.append({
            "source_type": "minutes",
            "date": date,
            "filename": file.name,
            "filepath": str(file),
            "title": None,
            "speaker": None,
            "location": None,
            "word_count": len(text.split()),
            "text":text
        })
    return entries

def standardize_press_confs(root_dir):
    entries = []
    for file in Path(root_dir).glob("*.txt"):
        text = read_text(file)
        date = parse_date_from_filename(file.name)
        entries.append({
            "source_type": "press_conference",
            "date": date,
            "filename": file.name,
            "filepath": str(file),
            "title": None,
            "speaker": None,
            "location": None,
            "word_count": len(text.split()),
            "text":text
        })
    return entries

def standardize_speeches(speech_dir, metadata_file):
    with open(metadata_file, "r", encoding="utf-8") as f:
        metadata = json.load(f)

    entries = []
    for item in metadata:
        file_path = item.get("filepath")
        if file_path and os.path.exists(file_path):
            text = read_text(file_path)
            entries.append({
                "source_type": "speech",
                "date": item.get("date"),
                "filename": os.path.basename(file_path),
                "filepath": file_path,
                "title": item.get("title"),
                "speaker": item.get("speaker"),
                "location": item.get("location"),
                "word_count": item.get("word_count", len(text.split())),
                "text":text
            })
    return entries

def write_output(entries, name):
    outdir = "standardized"
    os.makedirs(outdir, exist_ok=True)

    csv_path = os.path.join(outdir, f"{name}.csv")
    json_path = os.path.join(outdir, f"{name}.json")

    keys = ["source_type", "date", "filename", "filepath", "title", "speaker", "location", "word_count", "text"]

    with open(csv_path, "w", newline='', encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=keys)
        writer.writeheader()
        for entry in entries:
            writer.writerow(entry)

    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(entries, f, indent=2)

if __name__ == "__main__":
    minutes = standardize_minutes("data/fomc_minutes")
    press_confs = standardize_press_confs("data/press_conferences/text")
    speeches = standardize_speeches("data/fed_speeches", "data/fed_speeches/speech_metadata.json")

    write_output(minutes, "unified_minutes")
    write_output(press_confs, "unified_press_conferences")
    write_output(speeches, "unified_speeches")
