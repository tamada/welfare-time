import json
import subprocess
import os

def test_cafeteria_parser():
    input_pdf = "testdata/2026_05.pdf"
    output_json = "tmp/test_result.json"
    
    # スクリプトの実行
    subprocess.run(["python3", "scripts/parse_cafeteria_pdf.py", input_pdf, "-o", output_json], check=True)
    
    with open(output_json, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    # 1. 件数確認
    expected_count = 348
    if len(data) != expected_count:
        raise AssertionError(f"Expected {expected_count} entries, but got {len(data)}")
    
    # 2. 特定データの確認 (CAFE KSUKSUのパンのみ)
    ksuksu_notes = [d for d in data if d["id"] == "CAFE KSUKSU" and d["note"] == "パンのみ"]
    if len(ksuksu_notes) < 2:
        raise AssertionError("CAFE KSUKSU should have entries with 'パンのみ' note")

    print("Regression test passed: 348 entries and correct note extraction.")

if __name__ == "__main__":
    try:
        test_cafeteria_parser()
    except Exception as e:
        print(f"Test failed: {e}")
        exit(1)
