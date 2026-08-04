import json
import subprocess
import os
import sys
import argparse

def run_scraper(input_html, output_json):
    # テストを起動したインタプリタで実行する。python3 を直に指定すると、
    # 仮想環境から実行したときに bs4 が見つからず落ちる。
    subprocess.run([sys.executable, "scripts/scrape_kitchen_cars.py", input_html, output_json], check=True)
    with open(output_json, "r", encoding="utf-8") as f:
        return json.load(f)

def check(failures, condition, message):
    if not condition:
        failures.append(message)

def test_kitchen_car_scraper(sample_html, empty_html, output_json):
    failures = []
    data = run_scraper(sample_html, output_json)
    by_id = {d["id"]: d for d in data}

    # 1. 件数確認（重複1件と日付なし1件が除かれ、出店情報以外のリンクは拾われない）
    expected_count = 5
    check(failures, len(data) == expected_count,
          f"Expected {expected_count} entries, but got {len(data)}")

    # 2. id はURL末尾の店舗ID、name は店名（旧仕様では id に店名が入っていた）
    melon = by_id.get("dqSe1b")
    check(failures, melon is not None, "Entry with id 'dqSe1b' should exist")
    if melon:
        check(failures, melon["name"] == "メロンパンみのり",
              f"Expected name 'メロンパンみのり', but got {melon['name']!r}")
        check(failures, melon["url"] == "https://schedule.mellow.jp/ss_web/shops/dqSe1b",
              f"Relative href should be prefixed with the mellow domain, but got {melon['url']!r}")
        check(failures, melon["date"] == "2026-10-01",
              f"Expected date '2026-10-01', but got {melon['date']!r}")
        check(failures, (melon["start_time"], melon["end_time"]) == ("11:00", "17:00"),
              f"Expected 11:00-17:00, but got {melon['start_time']}-{melon['end_time']}")
        check(failures, melon["headline"] == "メロンパン",
              f"Expected headline 'メロンパン', but got {melon['headline']!r}")

    # 3. 絶対URLは二重にドメインが付かない。半角チルダも営業時間として解釈される
    kissa = by_id.get("5gSVjO")
    check(failures, kissa is not None, "Entry with id '5gSVjO' should exist")
    if kissa:
        check(failures, kissa["url"] == "https://schedule.mellow.jp/ss_web/shops/5gSVjO",
              f"Absolute href should be kept as is, but got {kissa['url']!r}")
        check(failures, (kissa["start_time"], kissa["end_time"]) == ("11:00", "16:00"),
              f"Expected 11:00-16:00 from '11:00 ~ 16:00', but got {kissa['start_time']}-{kissa['end_time']}")

    # 4. 全角英数・全角空白・半角括弧が正規化される
    normalized = by_id.get("q8S8od")
    check(failures, normalized is not None, "Entry with id 'q8S8od' should exist")
    if normalized:
        check(failures, normalized["name"] == "TEST カフェ（京都）",
              f"Expected normalized name 'TEST カフェ（京都）', but got {normalized['name']!r}")

    # 5. URLがない出店は店名のスラッグにフォールバックし、互いに別店舗として残る
    no_url = [d for d in data if not d["url"]]
    check(failures, len(no_url) == 2,
          f"Expected 2 entries without url, but got {len(no_url)}")
    check(failures, len({d["id"] for d in no_url}) == 2,
          "Entries without url must keep distinct ids, otherwise different shops collapse into one")
    check(failures, all(d["id"] for d in no_url),
          "Entries without url must not have an empty id")

    # 6. 日付のない出店はスキップされる
    check(failures, "XXXXXX" not in by_id, "Entry without a date badge should be skipped")

    # 7. 出店が0件でもエラーにならず空配列を返す（夏期休暇中の実ページがこの状態）
    empty = run_scraper(empty_html, output_json)
    check(failures, empty == [], f"Expected an empty list for a page with no entries, but got {empty!r}")

    if failures:
        raise AssertionError("\n  - " + "\n  - ".join(failures))

    print(f"Regression test passed: {expected_count} entries, id/name split, dedup and fallbacks.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--html", default="testdata/kitchen_cars_sample.html", help="Path to input HTML")
    parser.add_argument("--empty-html", default="testdata/kitchen_cars_empty.html", help="Path to HTML without entries")
    parser.add_argument("--output", default="tmp/test_kitchen_cars.json", help="Path to output JSON")
    args = parser.parse_args()

    # Ensure output directory exists
    os.makedirs(os.path.dirname(args.output), exist_ok=True)

    try:
        test_kitchen_car_scraper(args.html, args.empty_html, args.output)
    except Exception as e:
        print(f"Test failed: {e}")
        exit(1)
