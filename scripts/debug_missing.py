import json
import argparse
import pdfplumber
import os
import re
import calendar
from datetime import datetime, timedelta

def squash(x):
    if not isinstance(x, str): return ""
    return re.sub(r"\s+", "", x).strip()

def analyze_missing(input_pdf, extracted_json, master_path):
    with open(master_path, "r", encoding="utf-8") as f:
        master_data = json.load(f)

    with open(extracted_json, "r", encoding="utf-8") as f:
        extracted_data = json.load(f)

    # 抽出されたデータをセットに変換 (id + date)
    extracted_set = set(f"{e['id']}_{e['date']}" for e in extracted_data)

    print("--- Missing Entries Check ---")
    
    # Extract year/month from PDF filename (YYYY_MM.pdf)
    match = re.search(r"(\d{4})_(\d{2})", os.path.basename(input_pdf))
    if not match:
        print("Warning: Could not extract year/month from filename. Defaulting to 2026/05.")
        year, month = 2026, 5
    else:
        year, month = int(match.group(1)), int(match.group(2))

    with pdfplumber.open(input_pdf) as pdf:
        for page in pdf.pages:
            table = page.extract_table()
            if not table: continue
            
            for row in table:
                if len(row) < 5: continue
                
                name_text = squash(str(row[2] or ""))
                
                matched_cafeteria = None
                for cafeteria in master_data["cafeterias"]:
                    if squash(cafeteria["name"]) in name_text or name_text in squash(cafeteria["name"]):
                        matched_cafeteria = cafeteria
                        break
                
                if matched_cafeteria:
                    schedule_icons = row[4:]
                    
                    for idx, icon in enumerate(schedule_icons):
                        if "○" in str(icon):
                            date_str = f"{year}-{month:02d}-{idx+1:02d}"
                            key = f"{matched_cafeteria['id']}_{date_str}"
                            
                            if key not in extracted_set:
                                print(f"MISSING: Shop={matched_cafeteria['name']}, Date={date_str}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("pdf", help="Path to input PDF")
    parser.add_argument("json", help="Path to extracted JSON")
    parser.add_argument("--master", default="scripts/facilities.json", help="Path to facilities.json")
    args = parser.parse_args()
    analyze_missing(args.pdf, args.json, args.master)
