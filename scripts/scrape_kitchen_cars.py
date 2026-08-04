import json
import re
import argparse
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

def scrape_kitchen_cars(input_path, output_path):
    with open(input_path, "r", encoding="utf-8") as f:
        soup = BeautifulSoup(f, "html.parser")

    results = []
    
    # ページ内の各出店情報を特定する要素を取得
    items = soup.find_all("a", class_="a-link text-body text-decoration-none d-block")

    for item in items:
        # 日付: badgeクラス
        date_el = item.find("span", class_="badge")
        date_text = date_el.get_text(strip=True) if date_el else ""
        date_match = re.search(r"(\d{4})/(\d{2})/(\d{2})", date_text)
        if not date_match: continue
        
        # 店舗名: card-title
        name_el = item.find("div", class_="card-title")
        name = name_el.get_text(strip=True) if name_el else "不明"
        
        # テキスト要素リスト
        text_elements = item.find_all("div", class_="card-text")
        
        # メニュー: 1番目の card-text
        menu = text_elements[0].get_text(strip=True) if len(text_elements) > 0 else ""
        
        # 時間: 2番目の card-text
        time_text = text_elements[1].get_text(strip=True) if len(text_elements) > 1 else "00:00~00:00"
        
        # URL (href 属性)
        url = item.get("href", "")
        if url and not url.startswith("http"):
            url = "https://schedule.mellow.jp" + url
        
        time_match = re.search(r"(\d{1,2}:\d{2})\s*[〜~～]\s*(\d{1,2}:\d{2})", time_text)
        start, end = time_match.groups() if time_match else ("00:00", "00:00")
        shop_name = squash_name(name)

        results.append({
            "id": get_id_from_url(url, shop_name),
            "name": shop_name,
            "location": "",
            "date": f"{date_match.group(1)}-{date_match.group(2)}-{date_match.group(3)}",
            "start_time": squash_field(start),
            "end_time": squash_field(end),
            "business_hours": squash_field(time_text),
            "headline": squash_name(menu),
            "url": url
        })

    # 重複排除
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
    parser = argparse.ArgumentParser(description="Scrape kitchen car schedule HTML")
    parser.add_argument("input", help="Input HTML path")
    parser.add_argument("output", help="Output JSON path")
    args = parser.parse_args()
    
    scrape_kitchen_cars(args.input, args.output)
