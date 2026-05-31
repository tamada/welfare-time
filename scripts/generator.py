import json
import os
import argparse
import re
import unicodedata
from datetime import datetime, timedelta, timezone
from pathlib import Path

# Define timezones
JST = timezone(timedelta(hours=9), "JST")

def load_json(path):
    if not os.path.exists(path):
        return {}
    with open(path, "r", encoding="utf-8") as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return {}

def save_json(data, path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def slugify(text):
    return re.sub(r"[^\w\s-]", "", text).strip().lower().replace(" ", "-")

def get_id_from_url(url, fallback_name):
    if url:
        match = re.search(r"/([^/]+)$", url.strip("/"))
        if match:
            return match.group(1)
    return slugify(fallback_name)

def generator(cafeteria_dir, kitchen_cars_path, master_path, output_dir, kitchen_cars_archive):
    # Use JST for date-based logic
    now_jst = datetime.now(JST)
    today_str = now_jst.strftime("%Y-%m-%d")
    
    # Use UTC with Z for the timestamp
    last_updated = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    
    # 1. Load Master Data
    master_raw = load_json(master_path)
    if not master_raw:
        master_raw = {"cafeterias": [], "kitchen_cars": []}
        
    cafeteria_master_map = {}
    for c in master_raw.get("cafeterias", []):
        key = (c["name"], c["location"])
        cafeteria_master_map[key] = c
        
    kitchen_car_master_map = {}
    for k in master_raw.get("kitchen_cars", []):
        key = k["name"]
        kitchen_car_master_map[key] = k

    # Load metadata for PDF URLs from the new public/daily location
    metadata = load_json(os.path.join(output_dir, "daily/.metadata.json"))
    
    # 2. Load and Archive Kitchen Car Data
    all_scraped_kitchen_cars = load_json(kitchen_cars_path)
    if isinstance(all_scraped_kitchen_cars, dict):
        all_scraped_kitchen_cars = []
    
    past_archive = load_json(kitchen_cars_archive)
    if isinstance(past_archive, dict):
        past_archive = []
    
    seen_past = {(d["id"], d["date"]) for d in past_archive}
    for d in all_scraped_kitchen_cars:
        if d["date"] < today_str and (d["id"], d["date"]) not in seen_past:
            past_archive.append(d)
            seen_past.add((d["id"], d["date"]))
    save_json(past_archive, kitchen_cars_archive)
    
    kitchen_car_schedules = past_archive + [d for d in all_scraped_kitchen_cars if d["date"] >= today_str]
    unique_kc = []
    seen_kc = set()
    for d in kitchen_car_schedules:
        key = (d["id"], d["date"])
        if key not in seen_kc:
            unique_kc.append(d)
            seen_kc.add(key)
    kitchen_car_schedules = unique_kc

    # 3. Initialize Schedule Map with a range of dates
    schedule_map = {}
    
    # Initialize from 7 days ago to 30 days ahead to ensure static shops appear
    start_init = now_jst - timedelta(days=7)
    for i in range(40):
        d_str = (start_init + timedelta(days=i)).strftime("%Y-%m-%d")
        schedule_map[d_str] = {
            "date": d_str, 
            "last_updated": last_updated, 
            "timezone": "JST",
            "cafeterias": [], 
            "kitchen_cars": [],
            "sources": []
        }
    
    def get_or_create_date(date_str):
        if date_str not in schedule_map:
            schedule_map[date_str] = {
                "date": date_str, 
                "last_updated": last_updated, 
                "timezone": "JST",
                "cafeterias": [], 
                "kitchen_cars": [],
                "sources": []
            }
        return schedule_map[date_str]

    for p in Path(cafeteria_dir).glob("*.json"):
        # Match {YYYY_MM}.json to daily/{YYYY_MM}.pdf
        source_filename = p.name.replace(".json", ".pdf")
        
        entries = load_json(str(p))
        if isinstance(entries, list):
            for s in entries:
                day_data = get_or_create_date(s["date"])
                
                # Add source to day as a relative path for the frontend
                source_entry = {"name": source_filename, "url": f"daily/{source_filename}"}
                if source_entry not in day_data["sources"]:
                    day_data["sources"].append(source_entry)

                m_info = cafeteria_master_map.get((s["id"], s["location"]))
                shop_id = m_info["id"] if m_info else slugify(f"{s['id']}-{s['location']}")
                
                day_data["cafeterias"].append({
                    "id": shop_id,
                    "name": s["id"],
                    "location": s["location"],
                    "category": m_info.get("category", "食堂") if m_info else "食堂",
                    "url": m_info.get("url", "") if m_info else "",
                    "google_map": m_info.get("google_map", "") if m_info else "",
                    "image_url": m_info.get("image_url", "") if m_info else "",
                    "headline": m_info.get("headline", "") if m_info else "",
                    "start_time": s["start_time"],
                    "end_time": s["end_time"],
                    "business_hours": s["business_hours"],
                    "note": s["note"]
                })

    # 4. Merge Kitchen Cars
    for s in kitchen_car_schedules:
        day_data = get_or_create_date(s["date"])
        m_info = kitchen_car_master_map.get(s["id"])
        target_url = s.get("url", "") or (m_info.get("url", "") if m_info else "")
        shop_id = m_info["id"] if m_info and "id" in m_info else get_id_from_url(target_url, s["id"])
        
        day_data["kitchen_cars"].append({
            "id": shop_id,
            "name": s["id"],
            "url": target_url,
            "image_url": m_info.get("image_url", "") if m_info else "",
            "headline": s.get("headline", "") or (m_info.get("headline", "") if m_info else ""),
            "location": s.get("location") or "大学内指定場所",
            "category": "キッチンカー",
            "start_time": s.get("start_time", "00:00"),
            "end_time": s.get("end_time", "00:00"),
            "business_hours": s.get("business_hours", ""),
            "note": ""
        })

    # 5. Inject Static Schedules (e.g. ATMs)
    for date_str, day_data in schedule_map.items():
        dt = datetime.strptime(date_str, "%Y-%m-%d")
        weekday = dt.weekday() # 0=Mon, 5=Sat, 6=Sun

        for m_shop in master_raw.get("cafeterias", []):
            if "static-hours" in m_shop:
                hours_str = ""
                if weekday < 5: # Mon-Fri
                    hours_str = m_shop["static-hours"].get("ordinary", "")
                elif weekday == 5: # Sat
                    hours_str = m_shop["static-hours"].get("saturday", "")

                if hours_str and hours_str != "closed":
                    start_time, end_time = "00:00", "00:00"
                    if "-" in hours_str:
                        start_time, end_time = hours_str.split("-")

                    day_data["cafeterias"].append({
                        "id": m_shop["id"],
                        "name": m_shop["name"],
                        "url": m_shop.get("url", ""),
                        "location": m_shop["location"],
                        "category": m_shop.get("category", "サービス"),
                        "headline": m_shop.get("headline", ""),
                        "start_time": start_time,
                        "end_time": end_time,
                        "business_hours": hours_str,
                        "note": ""
                    })

    # 6. Generate Daily API Files
    api_schedule_dir = os.path.join(output_dir, "api/schedule")
    for date_str, data in schedule_map.items():
        save_json(data, os.path.join(api_schedule_dir, f"{date_str}"))
    
    shortcuts = {
        "today": today_str,
        "yesterday": (now_jst - timedelta(days=1)).strftime("%Y-%m-%d"),
        "tomorrow": (now_jst + timedelta(days=1)).strftime("%Y-%m-%d")
    }
    for label, d_str in shortcuts.items():
        if d_str in schedule_map:
            save_json(schedule_map[d_str], os.path.join(api_schedule_dir, f"{label}"))

    # 6. Weekly API
    current_monday = now_jst - timedelta(days=now_jst.weekday())
    for w in range(3):
        week_start = current_monday + timedelta(weeks=w)
        daily_schedules = [schedule_map.get((week_start + timedelta(days=i)).strftime("%Y-%m-%d"), {"date": (week_start + timedelta(days=i)).strftime("%Y-%m-%d"), "cafeterias": [], "kitchen_cars": [], "sources": []}) for i in range(7)]
        week_data = {
            "week_index": w,
            "start_date": week_start.strftime("%Y-%m-%d"),
            "end_date": (week_start + timedelta(days=6)).strftime("%Y-%m-%d"),
            "last_updated": last_updated,
            "timezone": "JST",
            "daily_schedules": daily_schedules
        }
        # Save as weeks/0, weeks/1, etc.
        os.makedirs(os.path.join(api_schedule_dir, "weeks"), exist_ok=True)
        save_json(week_data, os.path.join(api_schedule_dir, f"weeks/{w}"))
        if w == 0: save_json(week_data, os.path.join(api_schedule_dir, "week"))

    # 7. Shops API
    all_shops = {}
    for date_str, data in sorted(schedule_map.items()):
        for c in data["cafeterias"]:
            sid = c["id"]
            if sid not in all_shops:
                all_shops[sid] = {**{k: v for k, v in c.items() if k not in ["start_time", "end_time", "business_hours", "note", "date"]}, "schedules": []}
            all_shops[sid]["schedules"].append({"date": date_str, "location": c["location"], "start_time": c["start_time"], "end_time": c["end_time"], "note": c["note"]})
        for k in data["kitchen_cars"]:
            sid = k["id"]
            if sid not in all_shops:
                all_shops[sid] = {**{k2: v for k2, v in k.items() if k2 not in ["start_time", "end_time", "business_hours", "note", "date"]}, "schedules": []}
            all_shops[sid]["schedules"].append({"date": date_str, "location": k["location"], "start_time": k["start_time"], "end_time": k["end_time"], "note": k["note"]})

    api_shops_dir = os.path.join(output_dir, "api/shops")
    shops_index = {"shops": []}
    for sid, sdata in all_shops.items():
        save_json(sdata, os.path.join(api_shops_dir, f"{sid}"))
        shops_index["shops"].append({k: v for k, v in sdata.items() if k != "schedules"})
    save_json(shops_index, os.path.join(api_shops_dir, "index.json"))

    # 8. Status API
    dates = sorted(schedule_map.keys())
    global_sources = []
    if isinstance(metadata, dict):
        for filename, info in metadata.items():
            global_sources.append({"name": filename, "url": f"daily/{filename}"})

    save_json({
        "last_updated": last_updated,
        "timezone": "UTC",
        "data_range": {"start": dates[0] if dates else "", "end": dates[-1] if dates else ""},
        "shop_count": len(all_shops),
        "sources": global_sources
    }, os.path.join(output_dir, "api/status"))

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--cafeteria-dir", required=True)
    parser.add_argument("--kitchen-cars", required=True)
    parser.add_argument("--kitchen-cars-archive", required=True)
    parser.add_argument("--master", required=True)
    parser.add_argument("-o", "--output-dir", required=True)
    args = parser.parse_args()
    generator(args.cafeteria_dir, args.kitchen_cars, args.master, args.output_dir, args.kitchen_cars_archive)
