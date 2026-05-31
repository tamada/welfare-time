# 次のAIエージェントへの引き継ぎ事項：UI/CSS/JS アーキテクチャの理想状態

本プロジェクトは現在、Bootstrap から Tailwind CSS への移行および Hugo テンプレートの整理を行っています。これまでの修正で生じた不整合を解消するため、以下の「あるべき姿」に従って実装・リファクタリングを行ってください。

## 1. 目指すべきアーキテクチャの原則

- **CSS と Tailwind の役割分担**:
  - `tailwind.config.js` および HTML 上のユーティリティクラス（`flex`, `grid`, `rounded`, `shadow`, `dark:...`）でほとんどのスタイルを定義する。
  - **ビルド時にコンパイル**: Tailwind CSS は CDN ではなく、Tailwind CLI または PostCSS を用いてビルド時にコンパイルする構成に移行すること。
  - `static/assets/style.css` は、**Tailwind では表現が困難または非効率な動的レイアウトのみ**を記述する（例：マップの建物エリア `.building-area` の位置座標、`#map-wrapper` のスティッキー位置など）。
  - HTML や JS にインライン CSS を書くことは厳禁。

## 2. インタラクションとDOM管理

- **ツールチップの廃止**: 以前使用していた `tooltip` は廃止。マップホバーはリスト側の強調表示とマップ上の強調表示に専念する。
- **イベントバインディング**: `onmouseenter` などの個別バインドは行わず、`shop-grid` に対して **Event Delegation (イベント委譲)** を使用する。
- **レンダリングと同期**: `render()` 関数を呼び出す際は、必ず「描画完了後の処理（フック）」をコールバックとして渡し、DOM 構築が完了したことを保証してからマップのインタラクション初期化を行うこと。

## 3. クリーンアップの優先事項

- **JavaScript の整理**: ロジックは `static/js/` 配下にモジュール化して配置する（`filter.js`, `sort.js`, `main.js`）。`layouts/` 配下の HTML ファイルに `<script>` タグやインライン JS を残さない（ただし、`baseof.html` でのモジュール読み込みは除く）。
- **残骸の削除**: 過去の試行錯誤で作成された `<div id="tooltip">` や不要な `partial` ファイルがあれば、即座に削除すること。
- **名前空間の汚染**: `master.json` やデータパスの整合性を維持し、RESTful かつ拡張子のない API パス(`/api/schedule/YYYY-MM-DD`) を使用すること。

## 4. スタイルの修正手順

1. Tailwind CSS のクラスと `style.css` のクラスで競合が発生している場合は、Tailwind を優先し、`style.css` の不要なクラス定義を削除すること。
2. マップ上のホバーが反応しない場合は、`.map-layer` の `pointer-events: none;` と `.building-area` の `pointer-events: auto;` の設定が正しく、かつ `z-index` でエリアが最前面にきているかをチェックすること。
3. **マップのスティッキー位置の動的計算**:
  - 現在 `static/assets/style.css` で `top: 130px;` とハードコードされている値を削除すること。
  - JavaScript で `<header>` 要素の高さを取得し、CSS 変数 `--header-height` に動的にセットするロジックを実装せよ。
  - `#map-wrapper` の `top` 値は `calc(var(--header-height) + 1rem)` のように動的に計算させること。これにより、フォントサイズ変更や表示サイズの変化にも対応可能なレイアウトを実現せよ。

---
引き継ぎ担当者へ：
このプロジェクトでは、**「見た目の複雑さ」よりも「構造のシンプルさ」を最優先**してください。場当たり的な CSS の追加や JS のタイミング調整で解決しようとせず、HTML/JS のライフサイクルを整理することで問題を解決してください。
