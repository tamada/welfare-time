import json
import re
from bs4 import BeautifulSoup
import unicodedata

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
    # 時間の tilde を全角 ～ に統一
    x = x.replace("~", "～")
    return x

def scrape_kitchen_cars(input_path, output_path):
    with open(input_path, "r", encoding="utf-8") as f:
        soup = BeautifulSoup(f, "html.parser")

    results = []
    
    items = soup.find_all("a", class_="a-link text-body text-decoration-none d-block")

    for item in items:
        date_el = item.find("span", class_="badge")
        date_text = date_el.get_text(strip=True) if date_el else ""
        date_match = re.search(r"(\d{4})/(\d{2})/(\d{2})", date_text)
        if not date_match: continue
        
        name_el = item.find("div", class_="card-title")
        name = name_el.get_text(strip=True) if name_el else "不明"
        
        text_elements = item.find_all("div", class_="card-text")
        menu = text_elements[0].get_text(strip=True) if len(text_elements) > 0 else ""
        time_text = text_elements[1].get_text(strip=True) if len(text_elements) > 1 else "00:00~00:00"
        
        url = "https://schedule.mellow.jp" + item.get("href", "")
        
        time_match = re.search(r"(\d{1,2}:\d{2})\s*[〜~～]\s*(\d{1,2}:\d{2})", time_text)
        start, end = time_match.groups() if time_match else ("00:00", "00:00")

        results.append({
            "id": squash_name(name),
            "location": "",
            "date": f"{date_match.group(1)}-{date_match.group(2)}-{date_match.group(3)}",
            "start_time": squash_field(start),
            "end_time": squash_field(end),
            "business_hours": squash_field(f"{start}～{end}"),
            "note": squash_name(menu)
        })

    unique_results = []
    seen = set()
    for res in results:
        key = (res["id"], res["date"])
        if key not in seen:
            unique_results.append(res)
            seen.add(key)

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(unique_results, f, indent=2, ensure_ascii=False)
    print(f"Parsed {len(unique_results)} entries. Saved to {output_path}")

if __name__ == "__main__":
    scrape_kitchen_cars("tmp/kitchen_cars_raw.html", "tmp/scraped_kitchen_cars.json")