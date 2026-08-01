#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
搜索集成 - SerpAPI + Tavily 统一搜索接口

策略：
1. 优先使用 Tavily（AI 优化搜索，结果结构化好）
2. 回退到 SerpAPI（通用搜索，覆盖面广）
3. 两者都可用时，并行搜索取合并结果
"""

import json
import time
from typing import List, Dict, Optional
from dataclasses import dataclass

from ..config import SearchConfig, DEFAULT_CONFIG
from ..utils.logger import logger


@dataclass
class SearchResult:
    title: str
    url: str
    snippet: str
    source: str  # "tavily" or "serpapi"


class SearchManager:
    """统一搜索管理器"""

    def __init__(self, config: Optional[SearchConfig] = None):
        self.config = config or DEFAULT_CONFIG.search

    def search(self, query: str, max_results: int = 10) -> List[SearchResult]:
        """
        统一搜索入口，自动选择可用服务

        Args:
            query: 搜索关键词
            max_results: 最大结果数

        Returns:
            搜索结果列表
        """
        results = []

        # 优先使用 Tavily
        if self.config.tavily_key:
            try:
                results = self._search_tavily(query, max_results)
                if results:
                    logger.info(f"Tavily 搜索返回 {len(results)} 条结果")
                    return results
            except Exception as e:
                logger.warning(f"Tavily 搜索失败: {e}")

        # 回退到 SerpAPI
        if self.config.serpapi_key:
            try:
                results = self._search_serpapi(query, max_results)
                if results:
                    logger.info(f"SerpAPI 搜索返回 {len(results)} 条结果")
                    return results
            except Exception as e:
                logger.warning(f"SerpAPI 搜索失败: {e}")

        if not results:
            logger.warning("搜索服务未配置或无可用服务，请先在设置页面配置搜索 API Key")
        return results

    def search_parallel(self, query: str, max_results: int = 10) -> List[SearchResult]:
        """
        并行搜索（Tavily + SerpAPI 同时搜索，合并结果去重）
        """
        import concurrent.futures

        results = []
        seen_urls = set()

        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
            futures = []
            if self.config.tavily_key:
                futures.append(executor.submit(self._search_tavily, query, max_results // 2))
            if self.config.serpapi_key:
                futures.append(executor.submit(self._search_serpapi, query, max_results // 2))

            for future in concurrent.futures.as_completed(futures):
                try:
                    for r in future.result():
                        if r.url not in seen_urls:
                            seen_urls.add(r.url)
                            results.append(r)
                except Exception as e:
                    logger.debug(f"并行搜索子任务失败: {e}")

        return results[:max_results]

    def search_today_in_history(self, month: int = None, day: int = None,
                                topic: str = "科技") -> List[SearchResult]:
        """
        搜索历史上的今天

        Args:
            month: 月份（默认当前）
            day: 日期（默认当前）
            topic: 主题，如"科技"、"科技事件"

        Returns:
            搜索结果
        """
        from datetime import datetime
        now = datetime.now()
        month = month or now.month
        day = day or now.day

        query = f"{month}月{day}日 历史上的今天 {topic} 事件"
        return self.search(query, max_results=15)

    def _search_tavily(self, query: str, max_results: int = 10) -> List[SearchResult]:
        """调用 Tavily Search API"""
        import requests

        url = "https://api.tavily.com/search"
        payload = {
            "api_key": self.config.tavily_key,
            "query": query,
            "max_results": max_results,
            "search_depth": "advanced",
            "include_answer": False,
            "include_raw_content": False,
        }

        resp = requests.post(url, json=payload, timeout=30)
        resp.raise_for_status()
        data = resp.json()

        results = []
        for item in data.get("results", []):
            results.append(SearchResult(
                title=item.get("title", ""),
                url=item.get("url", ""),
                snippet=item.get("content", ""),
                source="tavily",
            ))
        return results

    def _search_serpapi(self, query: str, max_results: int = 10) -> List[SearchResult]:
        """调用 SerpAPI Google Search"""
        import requests

        url = "https://serpapi.com/search"
        params = {
            "api_key": self.config.serpapi_key,
            "q": query,
            "num": max_results,
            "hl": "zh-CN",
            "gl": "cn",
        }

        resp = requests.get(url, params=params, timeout=30)
        resp.raise_for_status()
        data = resp.json()

        results = []
        for item in data.get("organic_results", []):
            results.append(SearchResult(
                title=item.get("title", ""),
                url=item.get("link", ""),
                snippet=item.get("snippet", ""),
                source="serpapi",
            ))
        return results