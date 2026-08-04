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

def slugify(text):
    return re.sub(r"[^\w\s-]", "", text).strip().lower().replace(" ", "-")

def get_id_from_url(url, fallback_name):
    if url:
        match = re.search(r"/([^/]+)$", url.strip("/"))
        if match:
            return match.group(1)
    return slugify(fallback_name)

def generator(cafeteria_dir, kitchen_cars_path, master_path, output_dir, kitchen_cars_archive, base_url):
    # Use JST for all time-based logic and timestamps
    now_jst = datetime.now(JST)
    today_str = now_jst.strftime("%Y-%m-%d")
    last_updated = now_jst.isoformat()
    base_url = base_url.rstrip("/")
    
    # 1. Load Master Data
    master_raw = load_json(master_path)
    if not master_raw:
        master_raw = {"facilities": [], "kitchen_cars": []}
        
    cafeteria_master_map = {}
    facilities = master_raw.get("facilities", []) + master_raw.get("cafeterias", [])
    for c in facilities:
        key = (squash_name(c["name"]), squash_field(c["location"]))
        cafeteria_master_map[key] = c
        
    kitchen_car_master_map = {}
    kc_list = master_raw.get("kitchen_cars", []) + [f for f in facilities if f.get("category") == "キッチンカー"]
    for k in kc_list:
        key = squash_name(k["name"])
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
    
    # Entries before today are frozen: the source site drops past data quickly,
    # so the archive is the only record of what actually happened.
    # Entries from today on are replaced by the scraped data, so that cancellations
    # and time changes are reflected. Today's entries become frozen tomorrow.
    frozen_past = [d for d in past_archive if d["date"] < today_str]
    # A scrape may still contain past entries (e.g. recovering after skipped runs);
    # archive them too instead of dropping them. Archived entries take precedence.
    frozen_past += [d for d in all_scraped_kitchen_cars if d["date"] < today_str]
    if all_scraped_kitchen_cars:
        upcoming = [d for d in all_scraped_kitchen_cars if d["date"] >= today_str]
    else:
        # An empty scrape most likely means a fetch failure; keep the archive as is.
        upcoming = [d for d in past_archive if d["date"] >= today_str]

    past_archive = []
    seen_past = set()
    for d in frozen_past + upcoming:
        key = (d["id"], d["date"])
        if key not in seen_past:
            past_archive.append(d)
            seen_past.add(key)
    save_json(past_archive, kitchen_cars_archive)

    kitchen_car_schedules = past_archive

    # 3. Initialize Schedule Map
    schedule_map = {}
    
    def get_or_create_date(date_str):
        if date_str not in schedule_map:
            schedule_map[date_str] = {
                "date": date_str,
                "timezone": "JST",
                "facilities": [],
                "sources": []
            }
        return schedule_map[date_str]

    # Ensure a minimum window around today (7 days ago to 32 days ahead)
    # This ensures static shops appear for the current period even if no other data exists.
    start_init = now_jst - timedelta(days=7)
    for i in range(40):
        get_or_create_date((start_init + timedelta(days=i)).strftime("%Y-%m-%d"))

    for p in Path(cafeteria_dir).glob("*.json"):
        # Match {YYYY_MM}.json to daily/{YYYY_MM}.pdf
        source_filename = p.name.replace(".json", ".pdf")
        
        entries = load_json(str(p))
        if isinstance(entries, list):
            for s in entries:
                day_data = get_or_create_date(s["date"])
                
                # Add source to day as an absolute path for the frontend
                source_entry = {"name": source_filename, "url": f"{base_url}/daily/{source_filename}"}
                if source_entry not in day_data["sources"]:
                    day_data["sources"].append(source_entry)

                norm_name = squash_name(s["name"])
                norm_loc = squash_field(s["location"])
                m_info = cafeteria_master_map.get((norm_name, norm_loc))
                
                if not m_info:
                    print(f"!!! MAJOR ERROR: Shop not found in master data: Name='{norm_name}', Location='{norm_loc}' (Source: {source_filename}, Date: {s['date']})")
                    # Provide hints for potential matches
                    hints = [m["id"] for k, m in cafeteria_master_map.items() if norm_name in k[0] or k[0] in norm_name]
                    if hints:
                        print(f"    Hint: Found similar names in master data: {', '.join(set(hints))}")
                    shop_id = slugify(f"MISSING-{norm_name}-{norm_loc}")
                else:
                    shop_id = m_info["id"]

                day_data["facilities"].append({
                    "id": shop_id,
                    "name": s["name"],
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
        norm_name = squash_name(s["name"])
        m_info = kitchen_car_master_map.get(norm_name)
        target_url = s.get("url", "") or (m_info.get("url", "") if m_info else "")

        # For kitchen cars, missing from master is NOT an error.
        # Priority: Master ID > URL Hash > Slugified Name
        if m_info and "id" in m_info:
            shop_id = m_info["id"]
        elif target_url:
            shop_id = get_id_from_url(target_url, s["name"])
        else:
            shop_id = slugify(norm_name)
        
        day_data["facilities"].append({
            "id": shop_id,
            "name": s["name"],
            "url": target_url,
            "image_url": m_info.get("image_url", "") if m_info else "",
            "headline": s.get("headline", "") or (m_info.get("headline", "") if m_info else ""),
            "location": s.get("location") or "大学内指定場所",
            "google_map": "",
            "category": "キッチンカー",
            "start_time": s.get("start_time", "00:00"),
            "end_time": s.get("end_time", "00:00"),
            "business_hours": s.get("business_hours", ""),
            "note": ""
        })

    # Fill gaps between the first and last dates to ensure continuity
    if schedule_map:
        all_dates = sorted(schedule_map.keys())
        first_dt = datetime.strptime(all_dates[0], "%Y-%m-%d")
        last_dt = datetime.strptime(all_dates[-1], "%Y-%m-%d")
        curr_dt = first_dt
        while curr_dt <= last_dt:
            get_or_create_date(curr_dt.strftime("%Y-%m-%d"))
            curr_dt += timedelta(days=1)

    # 5. Inject Static Schedules (e.g. ATMs)
    for date_str, day_data in schedule_map.items():
        dt = datetime.strptime(date_str, "%Y-%m-%d")
        weekday = dt.weekday() # 0=Mon, 5=Sat, 6=Sun

        for m_shop in facilities:
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

                    day_data["facilities"].append({
                        "id": m_shop["id"],
                        "name": m_shop["name"],
                        "url": m_shop.get("url", ""),
                        "location": m_shop["location"],
                        "category": m_shop.get("category", "サービス"),
                        "headline": m_shop.get("headline", ""),
                        "google_map": "",
                        "image_url": "",
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
    all_dates = sorted(schedule_map.keys())
    max_date_str = all_dates[-1] if all_dates else today_str
    max_dt = datetime.strptime(max_date_str, "%Y-%m-%d").replace(tzinfo=JST)
    
    delta_days = (max_dt - current_monday).days
    total_weeks = (delta_days // 7) + 1 if delta_days >= 0 else 1

    for w in range(total_weeks):
        week_start = current_monday + timedelta(weeks=w)
        daily_schedules = [schedule_map.get((week_start + timedelta(days=i)).strftime("%Y-%m-%d"), {"date": (week_start + timedelta(days=i)).strftime("%Y-%m-%d"), "facilities": [], "sources": []}) for i in range(7)]
        week_data = {
            "week_index": w,
            "start_date": week_start.strftime("%Y-%m-%d"),
            "end_date": (week_start + timedelta(days=6)).strftime("%Y-%m-%d"),
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
        for c in data["facilities"]:
            sid = c["id"]
            if sid not in all_shops:
                all_shops[sid] = {**{k: v for k, v in c.items() if k not in ["start_time", "end_time", "business_hours", "note", "date"]}, "schedules": []}
            all_shops[sid]["schedules"].append({"date": date_str, "location": c["location"], "start_time": c["start_time"], "end_time": c["end_time"], "note": c["note"]})

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
            global_sources.append({"name": filename, "url": f"{base_url}/daily/{filename}"})

    save_json({
        "last_updated": last_updated,
        "timezone": "JST",
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
    parser.add_argument("--base-url", required=True)
    args = parser.parse_args()
    generator(args.cafeteria_dir, args.kitchen_cars, args.master, args.output_dir, args.kitchen_cars_archive, args.base_url)
