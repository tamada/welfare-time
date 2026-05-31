import os
import argparse
import requests
import json
from bs4 import BeautifulSoup
import pdfplumber
import re
import unicodedata
from datetime import datetime, timedelta, timezone
from pathlib import Path

# Define timezones
JST = timezone(timedelta(hours=9), "JST")

def load_metadata(metadata_file):
    if os.path.exists(metadata_file):
        with open(metadata_file, "r") as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                return {}
    return {}

def save_metadata(metadata, metadata_file):
    with open(metadata_file, "w") as f:
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
    
    return datetime.now(JST).strftime("%m")

def main():
    parser = argparse.ArgumentParser(description="Fetch cafeteria schedule PDFs")
    parser.add_argument("-u", "--url", default="https://www.kyoto-su.ac.jp/campus/welfare/", help="Base URL")
    parser.add_argument("-o", "--output", required=True, help="Output directory")
    parser.add_argument("-H", "--html", help="Local HTML file to parse instead of fetching from URL")
    parser.add_argument("--save-html", help="Save the fetched/read HTML to this file")
    args = parser.parse_args()

    daily_dir = args.output
    metadata_file = os.path.join(daily_dir, ".metadata.json")

    html_content = ""
    base_url = args.url
    if args.html:
        with open(args.html, "r") as f:
            html_content = f.read()
    else:
        response = requests.get(args.url)
        html_content = response.text

    if args.save_html:
        with open(args.save_html, "w") as f:
            f.write(html_content)

    soup = BeautifulSoup(html_content, "html.parser")
    
    pdf_links = []
    for a in soup.find_all("a", href=True):
        href = a["href"].strip()
        if href.lower().endswith(".pdf"):
            pdf_links.append(requests.compat.urljoin(base_url, href))
            
    if not pdf_links:
        print("No PDF links found")
        return

    os.makedirs(daily_dir, exist_ok=True)
    metadata = load_metadata(metadata_file)
    
    for pdf_url in pdf_links:
        head = requests.head(pdf_url)
        last_modified = head.headers.get("Last-Modified")
        etag = head.headers.get("ETag")
        
        res = requests.get(pdf_url)
        temp_path = os.path.join(daily_dir, "temp.pdf")
        with open(temp_path, "wb") as f:
            f.write(res.content)
            
        month = get_month_from_pdf(temp_path)
        now_jst = datetime.now(JST)
        year = now_jst.year
        curr_month = now_jst.month
        target_month = int(month)
        if (target_month == 1 or target_month == 2) and curr_month == 12:
            year += 1
            
        final_filename = f"{year}_{month}.pdf"
        final_path = os.path.join(daily_dir, final_filename)
        
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
            "fetched_at": datetime.now(JST).isoformat()
        }
        print(f"Saved: {final_path}")
        
    save_metadata(metadata, metadata_file)

if __name__ == "__main__":
    main()
