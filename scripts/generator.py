import json
import os
import argparse
from datetime import datetime
from pathlib import Path

def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def save_json(data, path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def generator(cafeteria_dir, kitchen_cars_path, output_dir):
    today = datetime.now().strftime("%Y-%m-%d")
    
    # 1. Load cafeteria data
    cafeteria_data = []
    cafeteria_path = Path(cafeteria_dir)
    if not cafeteria_path.exists():
        raise FileNotFoundError(f"Cafeteria directory not found: {cafeteria_dir}")
        
    for p in cafeteria_path.glob("parsed_*.json"):
        cafeteria_data.extend(load_json(p))
    
    # 2. Load and split kitchen car data
    if not os.path.exists(kitchen_cars_path):
        raise FileNotFoundError(f"Kitchen car data not found: {kitchen_cars_path}")
        
    all_kitchen_cars = load_json(kitchen_cars_path)
    past_kitchen_cars = [d for d in all_kitchen_cars if d["date"] < today]
    future_kitchen_cars = [d for d in all_kitchen_cars if d["date"] >= today]
    
    # 3. Update/Merge past kitchen car data
    past_archive_path = "data/kitchen_cars_past.json"
    if os.path.exists(past_archive_path):
        past_archive = load_json(past_archive_path)
    else:
        past_archive = []
    
    # Simple merge by id and date
    seen = {(d["id"], d["date"]) for d in past_archive}
    for d in past_kitchen_cars:
        if (d["id"], d["date"]) not in seen:
            past_archive.append(d)
            seen.add((d["id"], d["date"]))
    
    save_json(past_archive, past_archive_path)
    print(f"Archived past kitchen car data to {past_archive_path}")
    
    # 4. Merge cafeteria and future kitchen car data for API
    combined_future = cafeteria_data + future_kitchen_cars
    save_json(combined_future, os.path.join(output_dir, "api/schedule/future.json"))
    print(f"Generated API data in {output_dir}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--cafeteria-dir", required=True, help="Dir with parsed cafeteria JSONs")
    parser.add_argument("--kitchen-cars", required=True, help="Path to kitchen car JSON")
    parser.add_argument("-o", "--output-dir", required=True, help="Output directory")
    args = parser.parse_args()
    
    generator(args.cafeteria_dir, args.kitchen_cars, args.output_dir)
