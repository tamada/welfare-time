import json
import argparse
import pdfplumber
import re
import calendar
import unicodedata
import os
from datetime import datetime
from pathlib import Path

def squash_name(x):
    if not isinstance(x, str): return ""
    x = unicodedata.normalize("NFKC", x)
    x = x.replace("(", "（").replace(")", "）")
    x = re.sub(r"\s+", " ", x).strip()
    return x

def squash_field(x):
    if not isinstance(x, str): return ""
    x = unicodedata.normalize("NFKC", x)
    x = re.sub(r"\s+", "", x)
    x = x.replace("(", "（").replace(")", "）")
    x = x.replace("~", "～")
    return x

def parse_pdf_to_json(input_path, output_path=None):
    # PDFの更新日時を確認
    if os.path.exists(input_path):
        pdf_mtime = os.path.getmtime(input_path)
    else:
        raise FileNotFoundError(f"Input file not found: {input_path}")
    
    # 既にJSONが存在し、かつPDFの方が古い場合はスキップ
    if output_path and os.path.exists(output_path) and os.path.getmtime(output_path) >= pdf_mtime:
        print(f"Skipping (not modified): {input_path}")
        return

    # ファイル名から年月を抽出
    match = re.search(r"(\d{4})_(\d{2})", Path(input_path).stem)
    if not match:
        raise ValueError(f"Could not extract year/month from filename: {input_path}")
    
    year = int(match.group(1))
    month = int(match.group(2))
    
    results = []
    _, last_day = calendar.monthrange(year, month)
    daysInMonth = [datetime(year, month, day) for day in range(1, last_day + 1)]

    with pdfplumber.open(input_path) as pdf:
        for page in pdf.pages:
            table = page.extract_table()
            if not table: continue
            
            for row in table:
                if len(row) < 5 or not row[0] or not str(row[0]).strip().isdigit():
                    continue
                
                row_cells = [squash_name(str(cell or "")) for cell in row]
                
                pdf_loc = squash_field(str(row_cells[1] or ""))
                pdf_name = squash_name(str(row_cells[2] or ""))
                pdf_hours = str(row_cells[3] or "")
                
                schedule_cells = row_cells[4:] 
                
                for idx, date_val in enumerate(daysInMonth):
                    if idx < len(schedule_cells):
                        cell_val = str(schedule_cells[idx] or "")
                        
                        if cell_val and cell_val != "×":
                            # Extract potential weekday-specific hours from pdf_hours
                            # Example: "平日 11:00~19:00 土 11:00~14:00" or "平日 8:00~19:00 水 8:00~18:00 土 8:00~17:00"
                            weekday_hours = pdf_hours.replace("：", ":")
                            
                            current_hours = ""
                            day_of_week = date_val.weekday() # 0=Mon, 2=Wed, 5=Sat
                            
                            if day_of_week == 5: # Saturday
                                sat_match = re.search(r"土\s*(\d{1,2}:\d{2})\s*[～~]\s*(\d{1,2}:\d{2})", weekday_hours)
                                if sat_match:
                                    current_hours = f"{sat_match.group(1)}~{sat_match.group(2)}"
                            elif day_of_week == 2: # Wednesday
                                wed_match = re.search(r"水\s*(\d{1,2}:\d{2})\s*[～~]\s*(\d{1,2}:\d{2})", weekday_hours)
                                if wed_match:
                                    current_hours = f"{wed_match.group(1)}~{wed_match.group(2)}"
                            
                            if not current_hours:
                                # Default to "平日" (Weekday) or the first available time range
                                weekday_match = re.search(r"(?:平日|月～金)\s*(\d{1,2}:\d{2})\s*[～~]\s*(\d{1,2}:\d{2})", weekday_hours)
                                if weekday_match:
                                    current_hours = f"{weekday_match.group(1)}~{weekday_match.group(2)}"
                                else:
                                    # Just find the first range if no "平日" label
                                    first_match = re.search(r"(\d{1,2}:\d{2})\s*[～~]\s*(\d{1,2}:\d{2})", weekday_hours)
                                    if first_match:
                                        current_hours = f"{first_match.group(1)}~{first_match.group(2)}"
                            
                            h_match = re.search(r"(\d{1,2}:\d{2})\s*[～~]\s*(\d{1,2}:\d{2})", current_hours)
                            default_start, default_end = h_match.groups() if h_match else ("00:00", "00:00")
                            
                            specific_match = re.search(r"(\d{1,2}[:：]\d{2})\s*[|]\s*(\d{1,2}[:：]\d{2})", cell_val.replace("：", ":"))
                            start, end = (specific_match.group(1), specific_match.group(2)) if specific_match else (default_start, default_end)
                            
                            note = cell_val.replace("○", "").replace(start, "").replace(end, "").replace("|", "").replace("\\n", " ").strip()
                            note = re.sub(r"\d{1,2}[:：]\d{2}", "", note).strip()
                            
                            results.append({
                                "id": pdf_name,
                                "location": pdf_loc,
                                "date": date_val.strftime("%Y-%m-%d"),
                                "start_time": squash_field(start),
                                "end_time": squash_field(end),
                                "business_hours": pdf_hours.replace("  ", " "),
                                "note": squash_field(note)
                            })

    json_output = json.dumps(results, indent=2, ensure_ascii=False)
    if output_path:
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(json_output)
        print(f"Parsed {len(results)} entries. Saved to {output_path}")
    else:
        print(json_output)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("input", help="Input PDF path")
    parser.add_argument("-o", "--output", help="Output JSON path (optional)")
    args = parser.parse_args()
    
    parse_pdf_to_json(args.input, args.output)
