import json
import os
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.request import Request, urlopen

KST = timezone(timedelta(hours=9))
ROOT = Path(__file__).resolve().parents[1]
DATA_PATH = ROOT / "data" / "events.json"
MODEL = os.environ.get("OPENAI_MODEL", "gpt-4.1")


def yesterday_kst():
    now = datetime.now(KST)
    target = now.date() - timedelta(days=1)
    return target.isoformat()


def load_events():
    if not DATA_PATH.exists():
        return []
    return json.loads(DATA_PATH.read_text(encoding="utf-8"))


def save_events(events):
    DATA_PATH.write_text(json.dumps(events, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def call_openai(target_date, existing):
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY secret is not set")

    existing_brief = [
        {"id": e.get("id"), "title": e.get("title"), "url": e.get("url"), "sourceUrl": e.get("sourceUrl")}
        for e in existing
    ]

    prompt = f"""
You collect Korean coupon/giveaway events for a static GitHub Pages archive.
Target date: {target_date} 00:00-23:59 Asia/Seoul. Include only events newly posted on that date.

Find official or reliable-source events where participants can receive or win coffee coupons, gifticons, mobile vouchers, points, gift cards, food coupons, or prizes. Include survey response, quiz answer, comments, sharing, friend tagging, follow, KakaoTalk channel add, QR participation, and similar events.

Exclude: blog-only ads, unclear sources, illegal/gambling events, excessive personal data requests, dead links, simple sale discounts without prize/coupon/giveaway, duplicates already in existing events.

Existing events:
{json.dumps(existing_brief, ensure_ascii=False)}

Return JSON only in this shape:
{{
  "events": [
    {{
      "id": "YYYY-MM-DD-short-slug",
      "title": "event name",
      "organizer": "official organizer",
      "category": "카카오톡 이벤트|경품 이벤트|공유 이벤트|커피쿠폰",
      "reward": "main reward",
      "summary": "1-2 sentence factual summary in Korean",
      "method": "participation method in Korean",
      "caution": "important caution in Korean",
      "startDate": "YYYY-MM-DD",
      "endDate": "YYYY-MM-DD or 확인 필요",
      "announcementDate": "YYYY-MM-DD or 확인 필요",
      "url": "event/original URL",
      "sourceUrl": "source URL",
      "tags": ["keyword"]
    }}
  ],
  "excluded": ["short reasons"]
}}
"""

    body = {
        "model": MODEL,
        "tools": [{"type": "web_search"}],
        "input": prompt,
        "text": {"format": {"type": "json_object"}},
    }

    req = Request(
        "https://api.openai.com/v1/responses",
        data=json.dumps(body).encode("utf-8"),
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        method="POST",
    )
    with urlopen(req, timeout=180) as res:
        payload = json.loads(res.read().decode("utf-8"))

    text = payload.get("output_text")
    if not text:
        parts = []
        for item in payload.get("output", []):
            for content in item.get("content", []):
                if content.get("type") in {"output_text", "text"}:
                    parts.append(content.get("text", ""))
        text = "".join(parts)

    if not text:
        raise RuntimeError("OpenAI response did not contain text")

    return json.loads(text)


def dedupe(existing, new_events):
    seen = set()
    for e in existing:
        for key in (e.get("id"), e.get("title"), e.get("url"), e.get("sourceUrl")):
            if key:
                seen.add(str(key).strip())

    added = []
    for e in new_events:
        keys = [e.get("id"), e.get("title"), e.get("url"), e.get("sourceUrl")]
        if any(k and str(k).strip() in seen for k in keys):
            continue
        added.append(e)
        for k in keys:
            if k:
                seen.add(str(k).strip())
    return added


def main():
    target_date = os.environ.get("TARGET_DATE") or yesterday_kst()
    events = load_events()
    result = call_openai(target_date, events)
    additions = dedupe(events, result.get("events", []))

    if additions:
        save_events(additions + events)

    report = {
        "targetDate": target_date,
        "added": len(additions),
        "titles": [e.get("title") for e in additions],
        "excluded": result.get("excluded", []),
    }
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
