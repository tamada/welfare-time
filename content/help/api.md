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
  "last_updated": "2026-05-18T07:00:00",
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
