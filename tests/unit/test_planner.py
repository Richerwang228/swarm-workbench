"""Unit tests — planner_node JSON 解析。"""

from __future__ import annotations

from packages.orchestrator.nodes.planner import _make_todo, _parse_todo


def test_parse_todo_valid_json():
    content = '[{"description": "搭建后端 API", "role": "backend", "depends_on": []}]'
    items = _parse_todo(content, [])
    assert len(items) == 1
    assert items[0]["description"] == "搭建后端 API"
    assert items[0]["assigned_role"] == "backend"
    assert items[0]["status"] == "pending"


def test_parse_todo_markdown_code_block():
    content = """
以下是任务列表：
```json
[{"description": "设计数据库", "role": "backend", "depends_on": []}]
```
"""
    items = _parse_todo(content, [])
    assert len(items) >= 1
    assert items[0]["description"] == "设计数据库"


def test_parse_todo_invalid_json_fallback():
    items = _parse_todo("这不是 JSON", [])
    assert len(items) == 1  # fallback 任务


def test_parse_todo_deduplication():
    existing_item = _make_todo("已存在任务", "pm")
    content = '[{"description": "新任务", "role": "pm", "depends_on": []}]'
    items = _parse_todo(content, [existing_item])
    assert len(items) == 1
    assert items[0]["description"] == "新任务"


def test_make_todo_defaults():
    item = _make_todo("测试任务")
    assert item["status"] == "pending"
    assert item["assigned_role"] == "pm"
    assert item["depends_on"] == []
    assert item["result"] is None
    assert len(item["id"]) == 8


def test_parse_todo_multiple_roles():
    content = """[
      {"description": "前端开发", "role": "frontend", "depends_on": []},
      {"description": "后端开发", "role": "backend", "depends_on": []},
      {"description": "测试", "role": "tester", "depends_on": []}
    ]"""
    items = _parse_todo(content, [])
    assert len(items) == 3
    roles = {i["assigned_role"] for i in items}
    assert roles == {"frontend", "backend", "tester"}
