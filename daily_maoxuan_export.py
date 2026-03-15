#!/usr/bin/env python3
"""将每日毛选内容写入静态站点目录，供 public/index.html 读取。"""

import json
import os
from typing import Any, Dict, Optional


def write_daily_json(
    output_dir: str,
    date: str,
    title: str,
    body: str,
) -> str:
    """
    将 date、title、body 写入 output_dir/daily.json。
    若 output_dir 不存在则创建。
    返回写入文件的绝对路径。
    """
    os.makedirs(output_dir, exist_ok=True)
    path = os.path.join(output_dir, "daily.json")
    payload: Dict[str, Any] = {
        "date": date,
        "title": title,
        "body": body,
    }
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    return os.path.abspath(path)


def read_daily_json(output_dir: str) -> Optional[Dict[str, Any]]:
    """
    读取 output_dir/daily.json，若不存在或格式无效则返回 None。
    用于测试与校验。
    """
    path = os.path.join(output_dir, "daily.json")
    if not os.path.isfile(path):
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return None
