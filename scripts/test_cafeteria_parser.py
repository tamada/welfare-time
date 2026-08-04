import json
import subprocess
import os
import argparse

def test_cafeteria_parser(input_pdf, output_json):
    # スクリプトの実行
    subprocess.run(["python3", "scripts/parse_cafeteria_pdf.py", input_pdf, "-o", output_json], check=True)
    
    with open(output_json, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    # 1. 件数確認
    expected_count = 348
    if len(data) != expected_count:
        raise AssertionError(f"Expected {expected_count} entries, but got {len(data)}")
    
    # 2. 特定データの確認 (CAFE KSUKSUのパンのみ)
    ksuksu_notes = [d for d in data if d["name"] == "CAFE KSUKSU" and d["note"] == "パンのみ"]
    if len(ksuksu_notes) < 2:
        raise AssertionError("CAFE KSUKSU should have entries with 'パンのみ' note")

    print("Regression test passed: 348 entries and correct note extraction.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--pdf", default="testdata/2026_05.pdf", help="Path to input PDF")
    parser.add_argument("--output", default="tmp/test_result.json", help="Path to output JSON")
    args = parser.parse_args()

    # Ensure output directory exists
    os.makedirs(os.path.dirname(args.output), exist_ok=True)

    try:
        test_cafeteria_parser(args.pdf, args.output)
    except Exception as e:
        print(f"Test failed: {e}")
        exit(1)
