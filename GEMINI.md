# Project Documentation: Welfare TIME

京都産業大学の食堂・コンビニ・ショップ・ATM、およびキッチンカーの営業情報を自動収集し、Hugo で生成したサイトと静的な JSON API として公開するプロジェクトです。

利用者向けの概要とセットアップ手順は [README.md](README.md) を参照してください。この文書は、コードを変更する際に守るべき規約と不変条件をまとめたものです。

## Identifiers and Names

`id` と `name` は明確に区別します。**店名を `id` として使ってはいけません。**

| 対象 | `id` の由来 | `name` |
| :--- | :--- | :--- |
| 食堂・コンビニ・ショップ・ATM | マスター（`scripts/facilities.json`）の `id` | PDFに記載の店名 |
| キッチンカー | 情報源URLの末尾（例: `.../shops/dqSe1b` → `dqSe1b`） | ページに記載の店名 |

食堂のPDFには識別子が存在しません。取得できるのは店名と場所だけなので、`generator.py` が `(名前, 場所)` でマスターを引いて正式な `id` を解決します。マスターに存在しない店舗が現れた場合は `!!! MAJOR ERROR` を出力します。

キッチンカーはマスターに登録されていないことが正常です。URL末尾を `id` とし、URLが取得できない場合のみ店名のスラッグにフォールバックします。

重複排除のキーは `(id, date)` です。`id` に店名を入れると、店舗の改名で別店舗として扱われ、同名の別店舗が同一視されます。

## Data Normalization Conventions

正規化は `scripts/generator.py` と `scripts/scrape_kitchen_cars.py` の双方に同じ実装があります。片方だけ変更すると突き合わせが壊れます。

1. **`squash_name(x)`**: **Name** と **Note** に使用します。
   - NFKC 正規化（全角英数を半角に）。
   - 括弧を全角に変換: `(` → `（`, `)` → `）`。
   - 連続する空白を1つに畳み、前後を除去。
2. **`squash_field(x)`**: **Location**, **Time**, **Business Hours** に使用します。
   - NFKC 正規化。
   - 空白をすべて除去。
   - 括弧を全角に変換。
   - チルダ `~` を全角 `～` に変換。

## Data Pipeline

すべて `make` から実行します。単体のスクリプトを直接呼ぶ想定ではありません。

| Script | Input | Output |
| :--- | :--- | :--- |
| `scripts/fetch_cafeteria_pdf.py` | 大学サイト | `data/pdfs/YYYY_MM.pdf`, `data/pdfs/.metadata.json` |
| `scripts/parse_cafeteria_pdf.py` | `data/pdfs/YYYY_MM.pdf` | `data/cafeterias/YYYY_MM.json` |
| `scripts/fetch_kitchen_cars.py` | SHOP STOP のページ | `data/kitchencars/raw.html` |
| `scripts/scrape_kitchen_cars.py` | `data/kitchencars/raw.html` | `data/kitchencars/scraped.json` |
| `scripts/generator.py` | 上記2つ＋アーカイブ＋マスター | `static/api/` |

`generator.py` の必須引数は6つあります。`--cafeteria-dir`, `--kitchen-cars`, `--kitchen-cars-archive`, `--master`, `--base-url`, 出力先の `-o` です。`data/cafeterias/` と `data/kitchencars/` は追跡対象外の中間生成物で、毎回作り直されます。

生成後、Hugo が `static/` を `public/` へコピーし、`public/` を gh-pages ブランチとして公開します。

## Invariants

### キッチンカーのアーカイブ

`data/kitchen_cars_past.json` は、その日に何が出店していたかの**唯一の記録**です。情報源は過去の出店情報をすぐ削除するため、失うと復元できません。

- 過去（`date < today`, JST）のエントリは凍結し、削除も変更もしない
- 当日以降はスクレイプ結果を正とし、出店の取りやめや時間変更を反映する
- スクレイプ結果が0件のときはフェッチ失敗の可能性があるため、アーカイブに手を加えない
- 更新のたびに main ブランチへコミットする（CIは毎回リポジトリを取得し直すため、戻さないと蓄積が失われる）

夏期休暇中（7月中旬〜9月末）は出店自体がないため、0件が正常な状態です。

### ベースURL

サイトのURLは `hugo.toml` の `baseURL` を唯一の情報源とします。`Makefile` は `hugo config` から導出し、フロントエンドは `layouts/_default/baseof.html` が `relURL` で解決した値を `window.BASE_PATH` として渡します。**どこにもハードコードしないでください。**

サブパス（`/welfare-time/`）で配信しているため、ルート絶対パス（`/foo.png`）は常に誤りになります。

## Workflow Rules

- **削除操作:** 生成物の削除は許容します。`make clean` は `data/` を、デプロイ時は `public/api/` を削除して作り直します。追跡対象のファイルやデータを消す変更は、事前に確認を取ってください。特に `data/kitchen_cars_past.json` は復元不能です。
- **入力パス:** スクリプト内にハードコードせず、CLI引数（`argparse`）で受け取ります。
- **出力パス:** 既定は標準出力とし、ファイル出力は `-o` / `--output` で指定します。
- **正規化:** 上記の `squash_name` / `squash_field` を必ず適用します。
- **回帰テスト:** 解析処理を変更したら `make test` を実行します。食堂パーサとキッチンカーのスクレイパーの両方が対象です。
- **状態管理:** PDFの取得状況は `data/pdfs/.metadata.json` で追跡します。`make generate` がこれを `static/daily/` へコピーし、`generator.py` が出力先から読みます。

## Notes for Testing

夏期休暇中は情報源の出店が0件になるため、実データでスクレイパーを動かしても出店をループする本体を一度も通りません。**この期間、実データでの動作確認は不具合の検出にほとんど役立ちません。** `testdata/kitchen_cars_sample.html` を使う `make test` で確認してください。

`make test` は `PYTHON` 変数が指すインタプリタで動きます。依存関係を入れた環境を指定してください。

```bash
make test PYTHON=/path/to/venv/bin/python
```
