import os
import argparse
import requests
import json
from bs4 import BeautifulSoup
import pdfplumber
import re
import unicodedata
from datetime import datetime
from pathlib import Path

# Updated storage location to be inside data for source storage
DAILY_DIR = "data/daily"
METADATA_FILE = os.path.join(DAILY_DIR, ".metadata.json")

def load_metadata():
    if os.path.exists(METADATA_FILE):
        with open(METADATA_FILE, "r") as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                return {}
    return {}

def save_metadata(metadata):
    with open(METADATA_FILE, "w") as f:
        json.dump(metadata, f, indent=2)

def get_month_from_pdf(pdf_path):
    with pdfplumber.open(pdf_path) as pdf:
        text = ""
        for page in pdf.pages:
            text += page.extract_text() or ""
    
    text = unicodedata.normalize("NFKC", text)
    match = re.search(r"(\d{1,2})月", text)
    if match:
        return match.group(1).zfill(2)
    
    name = os.path.basename(pdf_path).lower()
    months = ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"]
    for i, m in enumerate(months):
        if m in name:
            return str(i + 1).zfill(2)
    
    return datetime.now().strftime("%m")

def main():
    parser = argparse.ArgumentParser(description="Fetch cafeteria schedule PDFs")
    parser.add_argument("-u", "--url", default="https://www.kyoto-su.ac.jp/campus/welfare/", help="Base URL")
    args = parser.parse_args()

    response = requests.get(args.url)
    soup = BeautifulSoup(response.text, "html.parser")
    
    pdf_links = []
    for a in soup.find_all("a", href=True):
        if a["href"].lower().endswith(".pdf"):
            pdf_links.append(requests.compat.urljoin(args.url, a["href"]))
            
    if not pdf_links:
        print("No PDF links found")
        return

    os.makedirs(DAILY_DIR, exist_ok=True)
    metadata = load_metadata()
    
    for pdf_url in pdf_links:
        head = requests.head(pdf_url)
        last_modified = head.headers.get("Last-Modified")
        etag = head.headers.get("ETag")
        
        res = requests.get(pdf_url)
        temp_path = os.path.join(DAILY_DIR, "temp.pdf")
        with open(temp_path, "wb") as f:
            f.write(res.content)
            
        month = get_month_from_pdf(temp_path)
        year = datetime.now().year
        curr_month = datetime.now().month
        target_month = int(month)
        if (target_month == 1 or target_month == 2) and curr_month == 12:
            year += 1
            
        final_filename = f"{year}_{month}.pdf"
        final_path = os.path.join(DAILY_DIR, final_filename)
        
        if os.path.exists(final_path):
            stored_info = metadata.get(final_filename)
            if stored_info and last_modified == stored_info.get("last-modified"):
                print(f"Skipping (not modified): {final_path}")
                os.remove(temp_path)
                metadata[final_filename]["url"] = pdf_url
                continue
        
        os.rename(temp_path, final_path)
        metadata[final_filename] = {
            "last-modified": last_modified,
            "etag": etag,
            "url": pdf_url,
            "fetched_at": datetime.now().isoformat()
        }
        print(f"Saved: {final_path}")
        
    save_metadata(metadata)

if __name__ == "__main__":
    main()
