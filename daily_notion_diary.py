#!/usr/bin/env python3
import json
import os
import sys
from datetime import datetime
from typing import Optional
from urllib import error, request


NOTION_API_VERSION = "2022-06-28"
DEFAULT_MODEL = "gemini-3.1-pro-preview"


def require_env(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


def http_json(url: str, method: str, headers: dict, payload: Optional[dict] = None) -> dict:
    data = None
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
    req = request.Request(url=url, data=data, headers=headers, method=method)
    try:
        with request.urlopen(req, timeout=30) as resp:
            raw = resp.read().decode("utf-8")
            return json.loads(raw) if raw else {}
    except error.HTTPError as e:
        body = e.read().decode("utf-8", errors="ignore")
        raise RuntimeError(f"HTTP {e.code} {method} {url}\n{body}") from e
    except error.URLError as e:
        raise RuntimeError(f"Network error calling {url}: {e}") from e


def generate_quote_style_text(gemini_api_key: str, model: str) -> str:
    url = (
        f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
        f"?key={gemini_api_key}"
    )
    today = datetime.now()
    date_str = today.strftime("%Y年%m月%d日")
    weekday = ["星期一", "星期二", "星期三", "星期四", "星期五", "星期六", "星期日"][today.weekday()]
    month_day = today.strftime("%m月%d日")

    prompt = (
        f"今天是{date_str}，{weekday}。\n"
        f'请你先简要回顾"历史上的{month_day}"发生过的一件有影响力的事件'
        f"（中国或世界均可），"
        f'然后以此为引子，用"毛泽东语录风格"写一段原创短文（120-200字）。\n'
        f"要求：\n"
        f"- 可以引用毛泽东的真实名句并加以发挥\n"
        f"- 将历史事件与今日反思、行动联系起来\n"
        f"- 语言铿锵有力，富有感召力\n"
        f"- 结尾以一句简短有力的今日行动口号收束\n"
        f"- 请直接输出正文，不要加标题或格式标记"
    )
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": 0.9,
            "maxOutputTokens": 8192,
            "thinkingConfig": {"thinkingBudget": 1024},
        },
    }
    headers = {"Content-Type": "application/json"}
    data = http_json(url, "POST", headers, payload)
    try:
        return data["candidates"][0]["content"]["parts"][0]["text"].strip()
    except (KeyError, IndexError, TypeError) as e:
        raise RuntimeError(f"Unexpected Gemini response: {json.dumps(data, ensure_ascii=False)}") from e


def notion_headers(notion_token: str) -> dict:
    return {
        "Authorization": f"Bearer {notion_token}",
        "Notion-Version": NOTION_API_VERSION,
        "Content-Type": "application/json",
    }


def get_database_schema(notion_token: str, database_id: str) -> dict:
    url = f"https://api.notion.com/v1/databases/{database_id}"
    return http_json(url, "GET", notion_headers(notion_token))


def pick_title_property_name(db_schema: dict) -> str:
    properties = db_schema.get("properties", {})
    for prop_name, prop_meta in properties.items():
        if prop_meta.get("type") == "title":
            return prop_name
    raise RuntimeError("No title property found in Notion database.")


def pick_date_property_name(db_schema: dict) -> Optional[str]:
    properties = db_schema.get("properties", {})
    for prop_name, prop_meta in properties.items():
        if prop_meta.get("type") == "date":
            return prop_name
    return None


def create_notion_page(
    notion_token: str,
    database_id: str,
    title_property_name: str,
    title_text: str,
    body_text: str,
    date_property_name: Optional[str] = None,
) -> dict:
    properties = {
        title_property_name: {
            "title": [{"type": "text", "text": {"content": title_text}}]
        }
    }
    if date_property_name:
        properties[date_property_name] = {
            "date": {"start": datetime.now().date().isoformat()}
        }

    payload = {
        "parent": {"database_id": database_id},
        "properties": properties,
        "children": [
            {
                "object": "block",
                "type": "paragraph",
                "paragraph": {
                    "rich_text": [{"type": "text", "text": {"content": body_text}}]
                },
            }
        ],
    }
    url = "https://api.notion.com/v1/pages"
    return http_json(url, "POST", notion_headers(notion_token), payload)


def main() -> int:
    try:
        gemini_api_key = require_env("GEMINI_API_KEY")
        notion_token = require_env("NOTION_TOKEN")
        database_id = require_env("NOTION_DATABASE_ID")
        model = os.getenv("GEMINI_MODEL", DEFAULT_MODEL).strip() or DEFAULT_MODEL

        quote_text = generate_quote_style_text(gemini_api_key, model)
        today = datetime.now().strftime("%Y-%m-%d")
        title = f"{today} 每日日记"

        db_schema = get_database_schema(notion_token, database_id)
        title_prop = pick_title_property_name(db_schema)
        date_prop = pick_date_property_name(db_schema)

        page = create_notion_page(
            notion_token=notion_token,
            database_id=database_id,
            title_property_name=title_prop,
            title_text=title,
            body_text=quote_text,
            date_property_name=date_prop,
        )

        print("Created Notion diary page successfully.")
        print(f"Page ID: {page.get('id', 'unknown')}")
        if page.get("url"):
            print(f"Page URL: {page['url']}")
        return 0
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
