import argparse
from bs4 import BeautifulSoup
import re

def debug_kitchen_cars(input_path):
    with open(input_path, "r", encoding="utf-8") as f:
        soup = BeautifulSoup(f, "html.parser")

    # 全てのテキストを検索して店舗情報っぽいものを探す
    # キッチンカーのスケジュールページによくあるキーワードで検索
    print("--- Searching for potential shop entries ---")
    # ページ内のリンクやdivから、出店者名や出店場所らしきものを探す
    # Mellowのページ構造を推測するための探索
    for element in soup.find_all(True): # 全タグを走査
        text = element.get_text(strip=True)
        if not text: continue
        
        # 店舗名らしきキーワードが含まれるか（例えば「屋」「キッチン」「カー」など）
        if "キッチン" in text or "屋" in text or "カレー" in text or "ランチ" in text:
            print(f"Found match: {text[:50]}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("input", help="Path to kitchen cars HTML file")
    args = parser.parse_args()
    debug_kitchen_cars(args.input)
