#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
内容源适配器 - 解耦设计，支持多种内容来源

功能特性:
1. 统一接口，支持多种内容源（历史事件、科技新闻、自定义 API 等）
2. 可插拔设计，新增内容源无需修改核心逻辑
3. 支持批量生成和定时刷新
4. 内置缓存机制，减少重复请求

使用示例:
    from video_gen.content.sources import ContentSourceManager
    
    # 创建管理器
    manager = ContentSourceManager()
    
    # 注册内容源
    manager.register(HistoryEventSource())
    manager.register(TechNewsSource())
    
    # 获取内容
    contents = manager.fetch_batch("history_events", topic="科技", count=50)
    
    # 生成脚本
    for content in contents:
        script = generator.generate_from_content(content)
"""

import os
import json
import time
import hashlib
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path

from ..config import DEFAULT_CONFIG
from ..utils.logger import logger
from ..utils.file_utils import safe_read_json, safe_write_json, ensure_dir


@dataclass
class ContentItem:
    """内容项"""
    id: str
    title: str
    topic: str
    content_type: str  # "history_event", "tech_news", "fun_fact", etc.
    summary: str
    details: str
    source: str
    created_at: datetime = field(default_factory=datetime.now)
    metadata: Dict = field(default_factory=dict)
    
    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "title": self.title,
            "topic": self.topic,
            "content_type": self.content_type,
            "summary": self.summary,
            "details": self.details,
            "source": self.source,
            "created_at": self.created_at.isoformat(),
            "metadata": self.metadata,
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> "ContentItem":
        return cls(
            id=data["id"],
            title=data["title"],
            topic=data["topic"],
            content_type=data.get("content_type", "general"),
            summary=data["summary"],
            details=data["details"],
            source=data["source"],
            created_at=datetime.fromisoformat(data["created_at"]) if data.get("created_at") else datetime.now(),
            metadata=data.get("metadata", {}),
        )


class ContentSource(ABC):
    """内容源抽象基类"""
    
    @property
    @abstractmethod
    def name(self) -> str:
        """内容源名称"""
        pass
    
    @property
    @abstractmethod
    def supported_types(self) -> List[str]:
        """支持的内容类型列表"""
        pass
    
    @abstractmethod
    def fetch(self, topic: str, **kwargs) -> Optional[ContentItem]:
        """获取单个内容项"""
        pass
    
    @abstractmethod
    def fetch_batch(self, topic: str, count: int, **kwargs) -> List[ContentItem]:
        """批量获取内容项"""
        pass
    
    def validate(self, content: ContentItem) -> bool:
        """验证内容有效性"""
        return bool(content.title and content.summary)


class HistoryEventSource(ContentSource):
    """历史事件内容源 - 专注于历史上的今天事件"""
    
    @property
    def name(self) -> str:
        return "history_events"
    
    @property
    def supported_types(self) -> List[str]:
        return ["history_event", "tech_history", "science_history"]
    
    def __init__(self, cache_dir: str = None):
        self.cache_dir = cache_dir or "./.content_cache/history"
        ensure_dir(self.cache_dir)
        self._cache_ttl = timedelta(hours=24)
    
    def fetch(self, topic: str = "科技", **kwargs) -> Optional[ContentItem]:
        """获取单个历史事件"""
        month = kwargs.get("month")
        day = kwargs.get("day")
        
        if not month or not day:
            now = datetime.now()
            month = now.month
            day = now.day
        
        cache_key = f"{month}_{day}_{topic}"
        cached = self._load_cache(cache_key)
        if cached:
            return cached
        
        # 构建查询
        query = f"{month}月{day}日 历史上的今天 {topic} 事件"
        
        # 使用搜索获取内容
        try:
            from ..ai.search import SearchManager
            search_mgr = SearchManager()
            results = search_mgr.search(query, max_results=5)
            
            if results:
                result = results[0]
                content = ContentItem(
                    id=self._generate_id(result.url),
                    title=result.title,
                    topic=topic,
                    content_type="history_event",
                    summary=result.snippet[:200],
                    details=f"来源：{result.url}\n\n{result.snippet}",
                    source=result.url,
                    metadata={"month": month, "day": day, "search_title": result.title},
                )
                self._save_cache(cache_key, content)
                return content
        except Exception as e:
            logger.error(f"HistoryEventSource fetch error: {e}")
        
        return None
    
    def fetch_batch(self, topic: str = "科技", count: int = 50, **kwargs) -> List[ContentItem]:
        """批量获取历史事件"""
        items = []
        from datetime import date
        
        # 获取当前日期
        today = date.today()
        
        # 往前推 count 天，每天一个事件
        for i in range(count):
            delta = timedelta(days=i)
            target_date = today - delta
            
            try:
                content = self.fetch(
                    topic=topic,
                    month=target_date.month,
                    day=target_date.day
                )
                if content:
                    items.append(content)
            except Exception as e:
                logger.error(f"获取第{i+1}天的历史事件失败：{e}")
            
            # 避免请求过快
            if (i + 1) % 10 == 0:
                time.sleep(1.0)
        
        logger.info(f"批量获取历史事件完成：{len(items)}/{count}")
        return items
    
    def _generate_id(self, url: str) -> str:
        """生成唯一 ID"""
        return "hist_" + hashlib.md5(url.encode()).hexdigest()[:12]
    
    def _load_cache(self, key: str) -> Optional[ContentItem]:
        """加载缓存"""
        cache_file = os.path.join(self.cache_dir, f"{key}.json")
        if os.path.exists(cache_file):
            data = safe_read_json(cache_file)
            if data:
                # 检查是否过期
                created = datetime.fromisoformat(data.get("created_at", ""))
                if datetime.now() - created < self._cache_ttl:
                    return ContentItem.from_dict(data)
        return None
    
    def _save_cache(self, key: str, content: ContentItem):
        """保存缓存"""
        cache_file = os.path.join(self.cache_dir, f"{key}.json")
        safe_write_json(cache_file, content.to_dict())


class TechNewsSource(ContentSource):
    """科技新闻内容源"""
    
    @property
    def name(self) -> str:
        return "tech_news"
    
    @property
    def supported_types(self) -> List[str]:
        return ["tech_news", "ai_news", "startup_news"]
    
    def __init__(self):
        pass
    
    def fetch(self, topic: str = "人工智能", **kwargs) -> Optional[ContentItem]:
        """获取单条科技新闻"""
        try:
            from ..ai.search import SearchManager
            search_mgr = SearchManager()
            
            query = f"{topic} 最新科技新闻 2025"
            results = search_mgr.search(query, max_results=5)
            
            if results:
                result = results[0]
                return ContentItem(
                    id="tech_" + hashlib.md5(result.url.encode()).hexdigest()[:12],
                    title=result.title,
                    topic=topic,
                    content_type="tech_news",
                    summary=result.snippet[:200],
                    details=f"来源：{result.url}\n\n{result.snippet}",
                    source=result.url,
                    metadata={"search_time": datetime.now().isoformat()},
                )
        except Exception as e:
            logger.error(f"TechNewsSource fetch error: {e}")
        
        return None
    
    def fetch_batch(self, topic: str = "人工智能", count: int = 50, **kwargs) -> List[ContentItem]:
        """批量获取科技新闻"""
        items = []
        topics = [
            "人工智能", "机器学习", "深度学习",
            "量子计算", "区块链", "元宇宙",
            "机器人", "自动驾驶", "芯片技术",
            "生物技术", "太空探索", "新能源"
        ]
        
        per_topic = max(1, count // len(topics))
        
        for t in topics:
            for i in range(per_topic):
                try:
                    content = self.fetch(topic=f"{t} 第{i+1}波")
                    if content:
                        items.append(content)
                except Exception as e:
                    logger.error(f"获取科技新闻失败 ({t}): {e}")
                
                if len(items) >= count:
                    break
            
            time.sleep(0.5)  # 每个 topic 之间延迟
        
        return items[:count]


class FunFactSource(ContentSource):
    """趣味知识内容源"""
    
    @property
    def name(self) -> str:
        return "fun_facts"
    
    @property
    def supported_types(self) -> List[str]:
        return ["fun_fact", "trivia", "cold_knowledge"]
    
    def fetch(self, topic: str = "科学趣事", **kwargs) -> Optional[ContentItem]:
        """获取单个趣味知识"""
        prompts = [
            f"{topic} 冷知识 有趣事实",
            f"{topic} 鲜为人知的故事",
            f"{topic} 神奇现象解释",
        ]
        
        import random
        prompt = random.choice(prompts)
        
        try:
            from ..ai.search import SearchManager
            search_mgr = SearchManager()
            results = search_mgr.search(prompt, max_results=3)
            
            if results:
                result = results[0]
                return ContentItem(
                    id="fun_" + hashlib.md5(result.url.encode()).hexdigest()[:12],
                    title=result.title,
                    topic=topic,
                    content_type="fun_fact",
                    summary=result.snippet[:200],
                    details=f"来源：{result.url}\n\n{result.snippet}",
                    source=result.url,
                )
        except Exception as e:
            logger.error(f"FunFactSource fetch error: {e}")
        
        return None
    
    def fetch_batch(self, topic: str = "科学趣事", count: int = 50, **kwargs) -> List[ContentItem]:
        """批量获取趣味知识"""
        items = []
        subtopics = [
            "物理学趣事", "化学奇观", "生物学秘密",
            "天文奥秘", "数学趣题", "地理奇闻",
            "历史冷知识", "科技发明故事"
        ]
        
        per_topic = max(1, count // len(subtopics))
        
        for sub in subtopics:
            for i in range(per_topic):
                try:
                    content = self.fetch(topic=f"{sub} 第{i+1}辑")
                    if content:
                        items.append(content)
                except Exception as e:
                    logger.error(f"获取趣味知识失败 ({sub}): {e}")
                
                if len(items) >= count:
                    break
        
        return items[:count]


class CustomAPISource(ContentSource):
    """自定义 API 内容源 - 用户可配置自己的 API"""
    
    @property
    def name(self) -> str:
        return "custom_api"
    
    @property
    def supported_types(self) -> List[str]:
        return ["custom", "api_import"]
    
    def __init__(self, api_endpoint: str = None, api_key: str = None):
        self.api_endpoint = api_endpoint
        self.api_key = api_key
    
    def fetch(self, topic: str = "", **kwargs) -> Optional[ContentItem]:
        """从自定义 API 获取内容"""
        if not self.api_endpoint:
            logger.warning("CustomAPISource: API endpoint not configured")
            return None
        
        try:
            import requests
            
            headers = {}
            if self.api_key:
                headers["Authorization"] = f"Bearer {self.api_key}"
            
            params = {"topic": topic, **kwargs}
            resp = requests.get(self.api_endpoint, params=params, headers=headers, timeout=30)
            resp.raise_for_status()
            
            data = resp.json()
            
            return ContentItem(
                id=data.get("id", f"custom_{int(time.time())}"),
                title=data.get("title", "Untitled"),
                topic=topic,
                content_type=data.get("content_type", "custom"),
                summary=data.get("summary", ""),
                details=data.get("details", ""),
                source=self.api_endpoint,
                metadata=data.get("metadata", {}),
            )
        except Exception as e:
            logger.error(f"CustomAPISource fetch error: {e}")
            return None
    
    def fetch_batch(self, topic: str = "", count: int = 50, **kwargs) -> List[ContentItem]:
        """批量从 API 获取"""
        items = []
        
        # 尝试调用支持批量的 API
        try:
            import requests
            
            headers = {}
            if self.api_key:
                headers["Authorization"] = f"Bearer {self.api_key}"
            
            params = {"topic": topic, "count": count, **kwargs}
            resp = requests.get(self.api_endpoint, params=params, headers=headers, timeout=60)
            resp.raise_for_status()
            
            data = resp.json()
            batch_data = data.get("items", data.get("results", [data]))
            
            for item_data in batch_data[:count]:
                item = ContentItem(
                    id=item_data.get("id", f"custom_{len(items)}"),
                    title=item_data.get("title", "Untitled"),
                    topic=topic,
                    content_type=item_data.get("content_type", "custom"),
                    summary=item_data.get("summary", ""),
                    details=item_data.get("details", ""),
                    source=self.api_endpoint,
                    metadata=item_data.get("metadata", {}),
                )
                items.append(item)
        except Exception as e:
            logger.error(f"CustomAPISource batch fetch error: {e}")
            # 降级为单次获取
            for i in range(count):
                item = self.fetch(topic=f"{topic}_{i}", **kwargs)
                if item:
                    items.append(item)
        
        return items


class ContentSourceManager:
    """内容源管理器 - 统一管理所有内容源"""
    
    def __init__(self):
        self.sources: Dict[str, ContentSource] = {}
        self._register_builtin_sources()
    
    def _register_builtin_sources(self):
        """注册内置内容源"""
        self.register(HistoryEventSource())
        self.register(TechNewsSource())
        self.register(FunFactSource())
    
    def register(self, source: ContentSource):
        """注册内容源"""
        self.sources[source.name] = source
        logger.info(f"已注册内容源：{source.name} (支持类型：{source.supported_types})")
    
    def get_source(self, name: str) -> Optional[ContentSource]:
        """获取指定内容源"""
        return self.sources.get(name)
    
    def get_source_by_type(self, content_type: str) -> Optional[ContentSource]:
        """根据内容类型获取内容源"""
        for source in self.sources.values():
            if content_type in source.supported_types:
                return source
        return None
    
    def fetch(self, source_name: str, topic: str = "", **kwargs) -> Optional[ContentItem]:
        """从指定内容源获取内容"""
        source = self.get_source(source_name)
        if not source:
            logger.error(f"内容源不存在：{source_name}")
            return None
        
        return source.fetch(topic, **kwargs)
    
    def fetch_batch(self, source_name: str, topic: str = "", count: int = 50, **kwargs) -> List[ContentItem]:
        """从指定内容源批量获取内容"""
        source = self.get_source(source_name)
        if not source:
            logger.error(f"内容源不存在：{source_name}")
            return []
        
        return source.fetch_batch(topic, count, **kwargs)
    
    def fetch_auto(self, content_type: str, topic: str = "", count: int = 1) -> List[ContentItem]:
        """自动选择内容源获取内容"""
        source = self.get_source_by_type(content_type)
        if not source:
            logger.error(f"未找到支持类型 '{content_type}' 的内容源")
            return []
        
        if count == 1:
            item = source.fetch(topic)
            return [item] if item else []
        else:
            return source.fetch_batch(topic, count)
    
    def list_sources(self) -> List[Dict]:
        """列出所有可用内容源"""
        return [
            {
                "name": s.name,
                "supported_types": s.supported_types,
            }
            for s in self.sources.values()
        ]


# CLI 入口
def main():
    """命令行测试入口"""
    import argparse
    
    parser = argparse.ArgumentParser(description="内容源管理工具")
    parser.add_argument("--list", action="store_true", help="列出所有内容源")
    parser.add_argument("--fetch", type=str, help="从指定内容源获取内容")
    parser.add_argument("--type", type=str, default="history_event", help="内容类型")
    parser.add_argument("--topic", type=str, default="科技", help="主题")
    parser.add_argument("--count", type=int, default=5, help="获取数量")
    parser.add_argument("--output", type=str, default=None, help="输出文件路径")
    
    args = parser.parse_args()
    
    manager = ContentSourceManager()
    
    if args.list:
        print("\n=== 可用内容源 ===")
        for info in manager.list_sources():
            print(f"\n名称：{info['name']}")
            print(f"支持类型：{', '.join(info['supported_types'])}")
        return
    
    if args.fetch:
        print(f"\n正在从 '{args.fetch}' 获取内容...")
        items = manager.fetch_batch(args.fetch, args.topic, args.count)
        
        print(f"\n获取到 {len(items)} 条内容:\n")
        for i, item in enumerate(items[:5], 1):
            print(f"{i}. [{item.content_type}] {item.title}")
            print(f"   摘要：{item.summary[:100]}...\n")
        
        if args.output:
            output_data = [item.to_dict() for item in items]
            safe_write_json(args.output, output_data)
            print(f"\n已保存到：{args.output}")


if __name__ == "__main__":
    main()
