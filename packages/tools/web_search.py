"""Web search tool — Tavily（主）/ DuckDuckGo（备用，无需 key）。"""

from __future__ import annotations

import os

from packages.tools.registry import register_tool

SCHEMA = {
    "name": "web_search",
    "description": "搜索互联网获取最新信息",
    "parameters": {
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "搜索关键词"},
            "max_results": {
                "type": "integer",
                "description": "最多返回结果数（1-10）",
                "default": 5,
            },
        },
        "required": ["query"],
    },
}


async def web_search_handler(query: str, max_results: int = 5) -> str:
    """执行网络搜索。优先用 Tavily，无 key 时降级到 DuckDuckGo。"""
    max_results = min(max(1, max_results), 10)

    tavily_key = os.getenv("TAVILY_API_KEY")
    if tavily_key:
        return await _tavily_search(query, max_results, tavily_key)

    return await _ddg_search(query, max_results)


async def _tavily_search(query: str, max_results: int, api_key: str) -> str:
    try:
        import httpx

        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                "https://api.tavily.com/search",
                json={"api_key": api_key, "query": query, "max_results": max_results},
            )
            resp.raise_for_status()
            data = resp.json()
            results = data.get("results", [])
            lines = [
                f"[{i + 1}] {r['title']}\n{r['url']}\n{r.get('content', '')[:300]}"
                for i, r in enumerate(results)
            ]
            return "\n\n".join(lines) or "No results"
    except Exception as exc:
        return f"Tavily error: {exc}. Falling back to DuckDuckGo..."


async def _ddg_search(query: str, max_results: int) -> str:
    """DuckDuckGo Instant Answer API（公开，无需 key，但结果有限）。"""
    try:
        import httpx

        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(
                "https://api.duckduckgo.com/",
                params={"q": query, "format": "json", "no_html": 1, "skip_disambig": 1},
            )
            data = resp.json()
            abstract = data.get("AbstractText", "")
            related = data.get("RelatedTopics", [])
            lines: list[str] = []
            if abstract:
                lines.append(f"摘要: {abstract}")
            for topic in related[:max_results]:
                if isinstance(topic, dict) and topic.get("Text"):
                    lines.append(f"• {topic['Text'][:200]}")
            return "\n".join(lines) or f"No results for: {query!r}"
    except Exception as exc:
        return f"Search error: {exc}"


register_tool("web_search", SCHEMA, web_search_handler)
