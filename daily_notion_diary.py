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
    prompt = (
        "请生成一段中文“毛泽东语录风格”的原创短文（80-140字），"
        "主题是今日反思与行动，可以直接引用真实历史原句，"
        "结尾再补一句简短的今日行动口号。"
    )
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.8, "maxOutputTokens": 300},
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
