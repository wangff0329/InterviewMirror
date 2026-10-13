from typing import Any

import httpx

from app.config import Settings


def search_interview_experiences(
    settings: Settings,
    company: str,
    role: str,
    keywords: str = "",
    max_results: int = 8,
) -> list[dict[str, Any]]:
    if settings.research_provider != "tavily":
        raise ValueError(f"不支持的搜索服务：{settings.research_provider}")
    if not settings.research_api_key:
        raise ValueError("尚未配置面经搜索 API Key，请在后端环境变量中设置 RESEARCH_API_KEY。")
    query_parts = ["site:nowcoder.com", company.strip(), role.strip(), keywords.strip(), "面经"]
    query = " ".join(part for part in query_parts if part)
    if not query:
        raise ValueError("请至少填写公司或岗位。")
    try:
        response = httpx.post(
            settings.research_api_url,
            headers={"Authorization": f"Bearer {settings.research_api_key}"},
            json={
                "api_key": settings.research_api_key,
                "query": query,
                "search_depth": "basic",
                "topic": "general",
                "max_results": max(1, min(max_results, 20)),
                "include_answer": False,
                "include_raw_content": False,
            },
            timeout=20,
        )
        response.raise_for_status()
        payload = response.json()
    except httpx.HTTPError as error:
        raise ValueError(f"面经搜索服务请求失败：{error}") from error
    results = payload.get("results", [])
    if not isinstance(results, list):
        raise ValueError("面经搜索服务返回了无法识别的数据。")
    return [
        {
            "title": str(item.get("title") or "未命名结果")[:300],
            "url": str(item.get("url") or ""),
            "snippet": str(item.get("content") or "")[:1000],
            "source": "牛客网",
            "query": query,
        }
        for item in results
        if isinstance(item, dict) and item.get("url")
    ]
