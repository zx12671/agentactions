#!/usr/bin/env python3
"""Smoke tests for Gemini, DashScope (Qwen), and Notion API connectivity."""

import json
import os
import sys
from typing import Optional, Tuple
from urllib import error, request


def require_env(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise RuntimeError(f"Missing environment variable: {name}")
    return value


def http_request(url: str, method: str, headers: dict, payload: Optional[dict] = None, timeout: int = 20):
    data = None
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
    req = request.Request(url=url, data=data, headers=headers, method=method)
    with request.urlopen(req, timeout=timeout) as resp:
        body = resp.read().decode("utf-8")
        return resp.status, json.loads(body) if body else {}


# ---------------------------------------------------------------------------
# Individual token tests
# ---------------------------------------------------------------------------

def test_gemini() -> bool:
    """Send a minimal generateContent request to Gemini and check for a valid response."""
    api_key = require_env("GEMINI_API_KEY")
    url = (
        "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent"
        f"?key={api_key}"
    )
    payload = {
        "contents": [{"parts": [{"text": "Say OK"}]}],
        "generationConfig": {"maxOutputTokens": 256, "thinkingConfig": {"thinkingBudget": 0}},
    }
    status, body = http_request(url, "POST", {"Content-Type": "application/json"}, payload)
    text = body["candidates"][0]["content"]["parts"][0]["text"]
    assert status == 200 and len(text) > 0, f"Unexpected Gemini response: {body}"
    return True


def test_dashscope_qwen() -> bool:
    """Send a minimal chat completion request to DashScope (Qwen) and check for a valid response."""
    api_key = require_env("DASHSCOPE_API_KEY")
    url = "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions"
    payload = {
        "model": "qwen-turbo",
        "messages": [{"role": "user", "content": "Say OK"}],
        "max_tokens": 16,
    }
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}",
    }
    status, body = http_request(url, "POST", headers, payload)
    text = body["choices"][0]["message"]["content"]
    assert status == 200 and len(text) > 0, f"Unexpected DashScope response: {body}"
    return True


def test_notion() -> bool:
    """Retrieve the target database metadata to verify Notion token and database access."""
    token = require_env("NOTION_TOKEN")
    db_id = require_env("NOTION_DATABASE_ID")
    url = f"https://api.notion.com/v1/databases/{db_id}"
    headers = {
        "Authorization": f"Bearer {token}",
        "Notion-Version": "2022-06-28",
    }
    status, body = http_request(url, "GET", headers)
    assert status == 200 and body.get("object") == "database", f"Unexpected Notion response: {body}"
    return True


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------

ALL_TESTS = [
    ("Gemini API", test_gemini),
    ("DashScope Qwen API", test_dashscope_qwen),
    ("Notion API", test_notion),
]


def main() -> int:
    passed, failed = 0, 0
    for name, fn in ALL_TESTS:
        try:
            fn()
            print(f"  PASS  {name}")
            passed += 1
        except Exception as e:
            print(f"  FAIL  {name}: {e}", file=sys.stderr)
            failed += 1

    print(f"\nResults: {passed} passed, {failed} failed, {passed + failed} total")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
