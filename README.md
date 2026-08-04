# Welfare TIME

現代の大学生活のための、福利厚生の時間と情報ナビ（Welfare Time & Information for Modern Education）です。

京都産業大学の食堂・コンビニ・ショップ・ATM、および日替わりで出店するキッチンカーの営業情報を自動収集し、ウェブサイトと JSON API として公開しています。情報がPDFや外部サイトに散らばっているため、これらを統合して一箇所で確認できるようにすることを目的としています。

- サイト: <https://tamadalab.github.io/welfare-time/>
- APIリファレンス: <https://tamadalab.github.io/welfare-time/help/api/>

## データソース

2つの情報源から取得し、正規化して静的な JSON API として配信します。

1. **学食スケジュール**: 大学サイトが公開するPDFのメニュー表から抽出します。
2. **キッチンカー**: [SHOP STOP](https://schedule.mellow.jp/ss_web/markets/KqTl8N) のページをスクレイピングします。

## データパイプライン

すべて `make` から実行します。

| 段階 | コマンド | 処理 | 出力先 |
| --- | --- | --- | --- |
| Fetch | `make fetch_pdf` | 大学サイトからPDFを取得 | `data/pdfs/` |
| Fetch | `make fetch_kitchencar` | Playwright でJS描画後のHTMLを取得 | `data/kitchencars/raw.html` |
| Parse | `make parse_pdf` | PDFを解析 | `data/cafeterias/*.json` |
| Scrape | `make parse_kitchencar` | HTMLを解析 | `data/kitchencars/scraped.json` |
| Generate | `make generate` | 統合してAPIを生成 | `static/api/` |
| Build | `make build_html` | Tailwind CSS と Hugo でサイトを生成 | `public/` |

`static/api/` に生成されたファイルを Hugo が `public/` へコピーし、`public/` を gh-pages ブランチとして公開しています。

## 毎朝の自動更新

[GitHub Actions](.github/workflows/daily_update.yml) が毎日 JST 7時（UTC 22時）に上記のパイプラインを実行し、生成物を gh-pages ブランチへ push します。実行の混雑により、実際の更新時刻は日によって前後します。

キッチンカーの過去データは `data/kitchen_cars_past.json` に蓄積し、更新のたびに main ブランチへコミットします。情報源は過去の出店情報をすぐ削除するため、このファイルが「その日に何が出店していたか」の唯一の記録になります。

蓄積には次の不変条件があります。

- 過去（`date < today`）のエントリは凍結し、削除も変更もしない
- 当日以降はスクレイプ結果を正とし、出店の取りやめや時間変更を反映する
- スクレイプ結果が0件のときはフェッチ失敗の可能性があるため、アーカイブに手を加えない

なお夏期休暇中はキッチンカーの出店自体がないため、0件が正常な状態です。

## 開発環境

以下が必要です。バージョンは [ワークフロー](.github/workflows/daily_update.yml) で使用しているものです。

- Python 3.11
- Hugo 0.119.0（extended）— サイト生成に加え、`make generate` がベースURLの取得に使います
- Node 26 — Tailwind CSS のビルドに使います

### セットアップ

```bash
pip install -r requirements.txt
playwright install chromium
npm ci
```

`playwright install chromium` は `make fetch_kitchencar` に必要です。

### ローカルでの確認

```bash
make generate
make serve
```

`make serve` は Hugo の開発サーバーを起動します（<http://localhost:1313/welfare-time/>）。

### テスト

```bash
make test
```

食堂PDFのパーサとキッチンカーのスクレイパーの回帰テストを実行します。`make` の `PYTHON` 変数が指すインタプリタで動くため、依存関係を入れた環境を指定してください。

```bash
make test PYTHON=/path/to/venv/bin/python
```

### その他のコマンド

`make help` で一覧を表示します。`make stale_api` は、gh-pages で配信されているが現在は生成されなくなったAPIファイルを検出します。

## ディレクトリ構成

| パス | 内容 |
| --- | --- |
| `scripts/` | データ収集・変換・生成用のPythonスクリプトとテスト |
| `scripts/facilities.json` | 施設のマスターデータ（正式ID・URL・カテゴリなど） |
| `content/` | Hugo のコンテンツ（ヘルプ、APIリファレンス） |
| `layouts/` | Hugo のテンプレート |
| `assets/` | Tailwind CSS のソース |
| `static/` | 静的ファイル。`static/api/` は生成物のため追跡対象外 |
| `data/` | 取得したPDFとキッチンカーのアーカイブ |
| `testdata/` | テスト用のPDFとHTMLフィクスチャ |
| `.github/workflows/` | 毎朝のデータ更新ワークフロー |

`public/` は Hugo の出力先かつ gh-pages のワークツリーで、リポジトリには含まれません。

## 公開API

すべてGETリクエストで取得できます。詳細は [APIリファレンス](https://tamadalab.github.io/welfare-time/help/api/) を参照してください。

| エンドポイント | 内容 |
| --- | --- |
| `/api/schedule/today` | 当日の営業情報。`tomorrow`, `yesterday` も利用可能 |
| `/api/schedule/YYYY-MM-DD` | 指定日の営業情報 |
| `/api/shops` | 全店舗のマスター情報と営業スケジュール履歴 |
| `/api/shops/{shop-id}` | 指定店舗の営業日時の一覧 |
| `/api/status` | データセット全体の更新状況と範囲 |

## リンク集

- [プロジェクト詳細ドキュメント (GEMINI.md)](GEMINI.md): 命名規則やデータ正規化の方針。
- [利用規約・ライセンス](LICENSE): プロジェクトのライセンス情報。
