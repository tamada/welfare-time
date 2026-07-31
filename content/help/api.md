---
title: "💻 API 利用ガイド"
type: "help"
---

Welfare-Time のデータを活用するためのAPIエンドポイントです。すべてGETリクエストでアクセス可能です。

## 1. 今日の予定 (`/api/schedule/today`)

当日の食堂およびキッチンカーの営業情報リストを返します。

```json
{
  "date": "2026-05-18",
  "timezone": "JST",
  "cafeterias": [
    {
      "id": "shop-id",
      "name": "食堂名",
      "location": "場所",
      "category": "食堂",
      "url": "...",
      "start_time": "11:00",
      "end_time": "14:00",
      "business_hours": "11:00～14:00",
      "note": "備考"
    }
  ],
  "kitchen_cars": ["..."]
}
```

### その他

- `/api/schedule/YYYY-MM-DD` の GET リクエストにより当該日時の営業店舗の情報を取得できます。
- `/api/schedule/tomorrow`, `/api/schedule/yesterday` で翌日、昨日の営業店舗の情報を取得できます。
- データ全体の更新時刻は `/api/status` の `last_updated` で取得できます。

## 2. 店舗一覧 (`/api/shops`)

登録されている全店舗のマスター情報および営業スケジュール履歴です。

```json
{
  "shops": [
    {
      "id": "shop-id",
      "name": "店舗名",
      "location": "場所",
      "category": "食堂",
      "url": "..."
    }
  ]
}
```

### 当該店舗の営業日時

`/api/shops/{shop-id}` で、その店舗の営業日時の一覧を取得できます。

## 3. ステータス情報 (`/api/status`)

データセット全体の更新状況と範囲を確認します。

```json
{
  "last_updated": "2026-05-18T07:00:00",
  "data_range": { "start": "2026-05-01", "end": "2026-06-30" },
  "shop_count": 42,
  "sources": [
    {
      "name": "2026_05.pdf",
      "url": "daily/2026_05.pdf"
    }
  ]
}
```
