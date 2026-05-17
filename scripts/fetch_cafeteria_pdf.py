import os
import argparse
import requests
import json
from bs4 import BeautifulSoup
import pdfplumber
import re
from datetime import datetime
from pathlib import Path
from email.utils import parsedate_to_datetime

METADATA_FILE = "daily/.metadata.json"

def load_metadata():
    if os.path.exists(METADATA_FILE):
        with open(METADATA_FILE, "r") as f:
            return json.load(f)
    return {}

def save_metadata(metadata):
    with open(METADATA_FILE, "w") as f:
        json.dump(metadata, f, indent=2)

def get_month_from_pdf(pdf_path):
    with pdfplumber.open(pdf_path) as pdf:
        text = ""
        for page in pdf.pages:
            text += page.extract_text() or ""
    
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
    parser = argparse.ArgumentParser(description="Fetch all cafeteria schedule PDFs with persistent metadata")
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

    os.makedirs("daily", exist_ok=True)
    metadata = load_metadata()
    
    for pdf_url in pdf_links:
        # HEADリクエストで更新情報を確認
        head = requests.head(pdf_url)
        last_modified = head.headers.get("Last-Modified")
        etag = head.headers.get("ETag")
        
        # 仮ダウンロードして年月判別
        res = requests.get(pdf_url)
        temp_path = "daily/temp.pdf"
        with open(temp_path, "wb") as f:
            f.write(res.content)
            
        month = get_month_from_pdf(temp_path)
        year = datetime.now().year
        
        curr_month = datetime.now().month
        target_month = int(month)
        if (target_month == 1 or target_month == 2) and curr_month == 12:
            year += 1
            
        final_path = os.path.join("daily", f"{year}_{month}.pdf")
        
        # メタデータ比較（ファイルが存在し、かつメタデータが一致する場合スキップ）
        if os.path.exists(final_path):
            stored_info = metadata.get(final_path)
            if stored_info and last_modified == stored_info.get("last-modified"):
                print(f"Skipping (not modified): {final_path}")
                os.remove(temp_path)
                continue
        
        os.rename(temp_path, final_path)
        metadata[final_path] = {"last-modified": last_modified, "etag": etag}
        print(f"Saved: {final_path}")
        
    save_metadata(metadata)

if __name__ == "__main__":
    main()
