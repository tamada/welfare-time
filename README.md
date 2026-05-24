# W-TIME

現代の大学生活のための、福利厚生の時間と情報ナビ（Welfare Time & Information for Modern Education）です。

大学の食堂やキッチンカーのスケジュール情報を自動収集し、APIとして公開・ホスティングするプロジェクトです。
PDFやWebサイトなど情報が散らばっているため、これらを統合して提供することを目的としています。
このプロジェクトは、以下の2つの主要なデータソースから情報を取得し、正規化して静的なJSON APIとして配信します。

1. **学食スケジュール**: PDF形式のメニュー表から情報を抽出する、
2. **キッチンカー**: Webサイトからスケジュール情報をスクレイピングする。

## リンク集

- [プロジェクト詳細ドキュメント (GEMINI.md)](GEMINI.md): 命名規則、データパイプライン、ワークフロールールなどの詳細。
- [APIリファレンス](help/api.html): 公開されているAPIエンドポイントの仕様。
- [フロントエンド表示](public/index.html): 収集されたデータのブラウザ上での表示。
- [利用規約・ライセンス](LICENSE): プロジェクトのライセンス情報。

## データパイプライン

データは以下の手順で処理されます：

1. **Fetch**: PDFやHTMLなどの生データを取得 (`scripts/fetch_*.py`)
2. **Parse/Scrape**: 生データを解析し、正規化されたJSONに変換 (`scripts/parse_*.py`, `scripts/scrape_*.py`)
3. **Generate**: 解析済みデータを統合し、`public/api/` 配下にエンドポイントファイルを生成 (`scripts/generator.py`)

詳細は [GEMINI.md の Data Pipeline セクション](GEMINI.md#data-pipeline) を参照してください。

## 開発・セットアップ

Python 3.x 環境が必要です。

### 依存関係のインストール

```bash
pip install -r requirements.txt
```

### スクリプトの実行

主要なスクリプトの使い方は各ファイルのヘルプを確認してください。

```bash
python scripts/generator.py --help
```

## ディレクトリ構成

- `scripts/`: データ収集・変換用Pythonスクリプト
- `public/`: ホスティングされる静的ファイル（APIエンドポイントを含む）
- `data/`, `testdata/`: 過去のデータやテスト用データ
- `help/`: 利用者向けのヘルプ・ドキュメント
