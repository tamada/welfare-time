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

def analyze_missing(input_path):
    master_path = "scripts/master.json"
    with open(master_path, "r", encoding="utf-8") as f:
        master_data = json.load(f)

    with open("tmp/final_cafeteria_data.json", "r", encoding="utf-8") as f:
        extracted_data = json.load(f)

    # 抽出されたデータをセットに変換 (id + date)
    extracted_set = set(f"{e['id']}_{e['date']}" for e in extracted_data)

    print("--- Missing Entries Check ---")
    with pdfplumber.open(input_path) as pdf:
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
                    # PDF上の該当日付を再計算
                    year, month = 2026, 5 # 固定
                    
                    for idx, icon in enumerate(schedule_icons):
                        if "○" in str(icon):
                            date_str = f"{year}-{month:02d}-{idx+1:02d}"
                            key = f"{matched_cafeteria['id']}_{date_str}"
                            
                            if key not in extracted_set:
                                print(f"MISSING: Shop={matched_cafeteria['name']}, Date={date_str}")

if __name__ == "__main__":
    analyze_missing("daily/2026_05.pdf")
