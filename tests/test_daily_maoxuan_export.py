"""单元测试：daily_maoxuan_export 模块。"""

import json
import os
import tempfile
import unittest

# 从项目根导入（需在项目根或 PYTHONPATH 含根目录时运行）
from daily_maoxuan_export import read_daily_json, write_daily_json


class TestWriteDailyJson(unittest.TestCase):
    def setUp(self):
        self.tmp_dir = tempfile.mkdtemp()

    def tearDown(self):
        import shutil
        if os.path.isdir(self.tmp_dir):
            shutil.rmtree(self.tmp_dir, ignore_errors=True)

    def test_creates_file_and_dir(self):
        """写入时若目录不存在应自动创建。"""
        out = os.path.join(self.tmp_dir, "sub", "public")
        path = write_daily_json(out, "2025-03-15", "测试标题", "正文内容")
        self.assertTrue(os.path.isfile(path))
        self.assertEqual(path, os.path.abspath(os.path.join(out, "daily.json")))
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        self.assertEqual(data["date"], "2025-03-15")
        self.assertEqual(data["title"], "测试标题")
        self.assertEqual(data["body"], "正文内容")

    def test_overwrites_existing(self):
        """再次写入应覆盖已有 daily.json。"""
        path = write_daily_json(self.tmp_dir, "2025-03-14", "旧标题", "旧正文")
        write_daily_json(self.tmp_dir, "2025-03-15", "新标题", "新正文")
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        self.assertEqual(data["date"], "2025-03-15")
        self.assertEqual(data["title"], "新标题")
        self.assertEqual(data["body"], "新正文")

    def test_utf8_and_newlines(self):
        """支持中文与多行正文。"""
        body = "第一段\n\n第二段。\n调查就是解决问题。"
        write_daily_json(self.tmp_dir, "2025-03-15", "调查就像十月怀胎", body)
        path = os.path.join(self.tmp_dir, "daily.json")
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        self.assertEqual(data["body"], body)
        self.assertIn("十月怀胎", data["title"])


class TestReadDailyJson(unittest.TestCase):
    def setUp(self):
        self.tmp_dir = tempfile.mkdtemp()

    def tearDown(self):
        import shutil
        if os.path.isdir(self.tmp_dir):
            shutil.rmtree(self.tmp_dir, ignore_errors=True)

    def test_returns_dict_when_valid(self):
        """有效 daily.json 应返回解析后的字典。"""
        write_daily_json(self.tmp_dir, "2025-03-15", "标题", "正文")
        data = read_daily_json(self.tmp_dir)
        self.assertIsNotNone(data)
        self.assertEqual(data["date"], "2025-03-15")
        self.assertEqual(data["title"], "标题")
        self.assertEqual(data["body"], "正文")

    def test_returns_none_when_missing(self):
        """目录下无 daily.json 时返回 None。"""
        self.assertIsNone(read_daily_json(self.tmp_dir))

    def test_returns_none_when_invalid(self):
        """daily.json 内容非法时返回 None。"""
        path = os.path.join(self.tmp_dir, "daily.json")
        os.makedirs(self.tmp_dir, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write("not valid json {")
        self.assertIsNone(read_daily_json(self.tmp_dir))

    def test_write_then_read_roundtrip(self):
        """写入后立即读取应得到相同内容。"""
        write_daily_json(self.tmp_dir, "2025-03-15", "标题", "正文\n多行")
        data = read_daily_json(self.tmp_dir)
        self.assertEqual(data, {"date": "2025-03-15", "title": "标题", "body": "正文\n多行"})


if __name__ == "__main__":
    unittest.main()
