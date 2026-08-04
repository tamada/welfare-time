import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from generator import merge_kitchen_car_archive

TODAY = "2026-08-04"

def entry(shop_id, date, business_hours="11:00〜17:00"):
    return {
        "id": shop_id,
        "name": f"{shop_id}の店",
        "location": "",
        "date": date,
        "start_time": business_hours.split("〜")[0],
        "end_time": business_hours.split("〜")[1],
        "business_hours": business_hours,
        "headline": "",
        "url": f"https://schedule.mellow.jp/ss_web/shops/{shop_id}",
    }

def keys(entries):
    return {(e["id"], e["date"]) for e in entries}

def check(failures, condition, message):
    if not condition:
        failures.append(message)

def test_merge_kitchen_car_archive():
    """アーカイブの不変条件を検証する。

    data/kitchen_cars_past.json は、その日に何が出店していたかの唯一の記録で
    あり、失うと復元できない。
    """
    failures = []

    # 1. 過去のエントリは凍結される。スクレイプに含まれなくても消えない
    archive = [entry("a", "2026-07-29"), entry("b", "2026-07-30")]
    merged = merge_kitchen_car_archive(archive, [entry("c", "2026-08-10")], TODAY)
    check(failures, ("a", "2026-07-29") in keys(merged), "Past entry 'a' must survive a scrape that omits it")
    check(failures, ("b", "2026-07-30") in keys(merged), "Past entry 'b' must survive a scrape that omits it")

    # 2. 当日以降はスクレイプ結果が正。出店の取りやめが反映される
    archive = [entry("past", "2026-07-30"), entry("a", "2026-08-05"), entry("b", "2026-08-05")]
    merged = merge_kitchen_car_archive(archive, [entry("a", "2026-08-05", "11:00〜15:00")], TODAY)
    check(failures, ("b", "2026-08-05") not in keys(merged), "Cancelled upcoming entry 'b' must be dropped")
    check(failures, ("a", "2026-08-05") in keys(merged), "Upcoming entry 'a' must remain")
    check(failures, ("past", "2026-07-30") in keys(merged), "Past entry must survive an upcoming cancellation")
    updated = [e for e in merged if e["id"] == "a"][0]
    check(failures, updated["business_hours"] == "11:00〜15:00",
          f"Upcoming entry must take the scraped hours, but got {updated['business_hours']!r}")

    # 3. スクレイプが0件ならアーカイブに手を加えない（フェッチ失敗の可能性）
    archive = [entry("past", "2026-07-30"), entry("future", "2026-08-05")]
    merged = merge_kitchen_car_archive(archive, [], TODAY)
    check(failures, keys(merged) == keys(archive),
          "An empty scrape must leave the archive untouched, it most likely means a fetch failure")

    # 4. 当日のエントリはスクレイプから取り込まれる（翌日には凍結される）
    merged = merge_kitchen_car_archive([], [entry("today", TODAY)], TODAY)
    check(failures, ("today", TODAY) in keys(merged), "Today's entry must be archived on the day itself")
    frozen = merge_kitchen_car_archive(merged, [], "2026-08-05")
    check(failures, ("today", TODAY) in keys(frozen), "Yesterday's entry must be frozen the next day")

    # 5. スクレイプに過去日が含まれる場合も取りこぼさない（実行が飛んだ日の回復）
    merged = merge_kitchen_car_archive([], [entry("recovered", "2026-08-01")], TODAY)
    check(failures, ("recovered", "2026-08-01") in keys(merged),
          "A past entry present in the scrape must be archived instead of dropped")

    # 6. 重複は (id, date) で排除され、アーカイブ側が優先される
    archive = [entry("dup", "2026-07-30", "11:00〜17:00")]
    scraped = [entry("dup", "2026-07-30", "09:00〜10:00")]
    merged = merge_kitchen_car_archive(archive, scraped, TODAY)
    check(failures, len(merged) == 1, f"Duplicated (id, date) must collapse into one, but got {len(merged)}")
    if merged:
        check(failures, merged[0]["business_hours"] == "11:00〜17:00",
              "The archived entry must win over a conflicting past entry from the scrape")

    # 7. 同じ日の別店舗は別エントリとして残る
    merged = merge_kitchen_car_archive([], [entry("x", TODAY), entry("y", TODAY)], TODAY)
    check(failures, len(merged) == 2, f"Different shops on the same day must be kept, but got {len(merged)}")

    if failures:
        raise AssertionError("\n  - " + "\n  - ".join(failures))

    print("Regression test passed: kitchen car archive invariants.")

if __name__ == "__main__":
    try:
        test_merge_kitchen_car_archive()
    except Exception as e:
        print(f"Test failed: {e}")
        exit(1)
