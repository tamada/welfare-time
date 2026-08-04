import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from generator import merge_kitchen_car_archive, add_cafeteria_schedules

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

def test_unresolved_shops(tmp_dir):
    """マスターに引き当てられない店舗が、集計されつつ公開もされることを検証する。

    データ更新を止めないため、引き当て失敗は例外にせず報告に留める。
    """
    import json
    failures = []

    os.makedirs(tmp_dir, exist_ok=True)
    entries = [
        {"name": "登録済みの店", "location": "1F", "date": "2026-06-01",
         "start_time": "11:00", "end_time": "14:00", "business_hours": "11:00～14:00", "note": ""},
        {"name": "未登録の店", "location": "2F", "date": "2026-06-01",
         "start_time": "11:00", "end_time": "14:00", "business_hours": "11:00～14:00", "note": ""},
        {"name": "未登録の店", "location": "2F", "date": "2026-06-02",
         "start_time": "11:00", "end_time": "14:00", "business_hours": "11:00～14:00", "note": ""},
    ]
    path = os.path.join(tmp_dir, "2026_06.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(entries, f, ensure_ascii=False)

    master_map = {("登録済みの店", "1F"): {"id": "known", "name": "登録済みの店", "location": "1F"}}
    schedule_map = {}
    unresolved = add_cafeteria_schedules(schedule_map, tmp_dir, master_map, "https://example.com")

    check(failures, list(unresolved) == [("未登録の店", "2F")],
          f"Only the unknown shop must be reported, but got {list(unresolved)}")
    if unresolved:
        record = unresolved[("未登録の店", "2F")]
        check(failures, sorted(record["dates"]) == ["2026-06-01", "2026-06-02"],
              f"Every date must be collected, but got {record['dates']}")
        check(failures, record["sources"] == {"2026_06.pdf"},
              f"The source file must be recorded, but got {record['sources']}")

    # 引き当てできなくてもその日のデータは失われない
    day = schedule_map.get("2026-06-01", {})
    ids = [f["id"] for f in day.get("facilities", [])]
    check(failures, "known" in ids, f"The resolved shop must keep its master id, but got {ids}")
    check(failures, any(i.startswith("missing-") for i in ids),
          f"The unresolved shop must still be published with a generated id, but got {ids}")

    if failures:
        raise AssertionError("\n  - " + "\n  - ".join(failures))

    print("Regression test passed: unresolved shops are reported without dropping data.")

if __name__ == "__main__":
    try:
        test_merge_kitchen_car_archive()
        test_unresolved_shops(os.path.join("tmp", "test_generator_cafeterias"))
    except Exception as e:
        print(f"Test failed: {e}")
        exit(1)
