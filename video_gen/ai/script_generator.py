#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
脚本生成器 - 搜索→AI生成→scripts.json 完整流水线

核心流程：
1. 用户输入主题 + 选择平台风格
2. 搜索互联网获取素材
3. 调用 AI 生成符合平台风格的文章（含配图提示词）
4. 调用 AI 将文章转为 scripts.json 格式
5. 返回最终的 scripts.json 数据
"""

import json
import os
from typing import Dict, List, Optional, Callable, Tuple
from datetime import datetime

from ..config import DEFAULT_CONFIG
from ..utils.logger import logger
from ..utils.file_utils import safe_write_json
from .deepseek import DeepSeekClient
from .search import SearchManager
from .prompts import get_platform_prompt, PLATFORM_PROMPTS


class ScriptGenerator:
    """
    脚本生成器

    整合搜索 + AI 生成，实现从主题到 scripts.json 的一键生成。
    """

    def __init__(self, ai_client: Optional[DeepSeekClient] = None,
                 search_manager: Optional[SearchManager] = None):
        self.ai = ai_client or DeepSeekClient()
        self.search = search_manager or SearchManager()

    def generate(self, topic: str, platform: str = "wechat",
                 extra_prompt: str = "",
                 search_results: Optional[List] = None,
                 progress_callback: Optional[Callable] = None) -> Dict:
        """
        一键生成完整视频脚本

        Args:
            topic: 主题（如"历史上的今天科技事件"）
            platform: 平台风格（wechat, science, short_video）
            extra_prompt: 补充提示词
            search_results: 预设搜索素材（可选，不传则自动搜索）
            progress_callback: 进度回调 (stage, message)

        Returns:
            {
                "success": bool,
                "article": str or None,        # 生成的 Markdown 文章
                "scripts_json": Dict or None,  # scripts.json 格式数据
                "search_results": List,        # 搜索素材
                "error": str or None,
            }
        """
        result = {
            "success": False,
            "article": None,
            "scripts_json": None,
            "search_results": [],
            "error": None,
        }

        try:
            # === 步骤1: 搜索素材 ===
            if search_results is None:
                self._report_progress(progress_callback, "search", "正在搜索互联网素材...")
                search_results = self.search.search(topic, max_results=10)
                result["search_results"] = search_results

            if not search_results:
                logger.warning("搜索未返回结果，将直接使用 AI 生成")

            # 构建搜索素材文本
            search_context = self._build_search_context(search_results, topic)

            # === 步骤2: AI 生成文章 ===
            self._report_progress(progress_callback, "generate_article", "AI 正在生成文章...")
            system_prompt = get_platform_prompt(platform)
            user_prompt = self._build_article_prompt(topic, search_context, extra_prompt)

            article = self.ai.generate_article(system_prompt, user_prompt)
            result["article"] = article

            # === 步骤3: AI 生成 scripts.json ===
            self._report_progress(progress_callback, "generate_scripts", "AI 正在生成视频脚本...")
            scripts_prompt = get_platform_prompt("scripts_json")
            scripts_data = self.ai.generate_scripts_json(scripts_prompt, article)

            # 补全 meta 信息
            if "meta" not in scripts_data:
                scripts_data["meta"] = {}
            scripts_data["meta"]["title"] = scripts_data["meta"].get("title", topic)
            scripts_data["meta"]["topic"] = topic
            scripts_data["meta"]["generated_at"] = datetime.now().isoformat()
            scripts_data["meta"]["platform"] = platform

            result["scripts_json"] = scripts_data
            result["success"] = True

            self._report_progress(progress_callback, "done", "生成完成!")

        except Exception as e:
            logger.error(f"脚本生成失败: {e}")
            result["error"] = str(e)
            self._report_progress(progress_callback, "error", f"生成失败: {e}")

        return result

    def generate_and_save(self, topic: str, platform: str = "wechat",
                          extra_prompt: str = "",
                          output_dir: str = None,
                          progress_callback: Optional[Callable] = None) -> Dict:
        """
        生成并保存到文件

        Returns:
            {
                "success": bool,
                "article_path": str or None,
                "scripts_path": str or None,
                ...
            }
        """
        result = self.generate(topic, platform, extra_prompt, progress_callback=progress_callback)

        if not result["success"]:
            return result

        output_dir = output_dir or "./output"
        os.makedirs(output_dir, exist_ok=True)

        # 保存文章
        article_path = os.path.join(output_dir, "article.md")
        if result["article"]:
            with open(article_path, "w", encoding="utf-8") as f:
                f.write(result["article"])
            result["article_path"] = article_path

        # 保存 scripts.json
        if result["scripts_json"]:
            scripts_path = os.path.join(output_dir, "scripts.json")
            safe_write_json(scripts_path, result["scripts_json"])
            result["scripts_path"] = scripts_path

        return result

    def _build_search_context(self, search_results: List, topic: str) -> str:
        """构建搜索素材上下文"""
        if not search_results:
            return f"主题：{topic}\n（无搜索结果）"

        lines = [f"## 搜索结果（主题：{topic}）\n"]
        for i, r in enumerate(search_results[:10], 1):
            lines.append(f"{i}. {r.title}")
            lines.append(f"   来源：{r.url}")
            lines.append(f"   摘要：{r.snippet}\n")

        return "\n".join(lines)

    def _build_article_prompt(self, topic: str, search_context: str,
                              extra_prompt: str) -> str:
        """构建文章生成提示词"""
        parts = [
            f"## 创作主题\n{topic}\n",
            f"## 素材参考\n{search_context}\n",
        ]
        if extra_prompt:
            parts.append(f"## 补充要求\n{extra_prompt}\n")
        parts.append(
            "请根据以上素材，按照系统提示词的要求生成一篇完整的文章。\n"
            "注意：每段必须包含**配图提示词**（英文），用于后续文生图。"
        )
        return "\n".join(parts)

    def _report_progress(self, callback: Optional[Callable], stage: str, message: str):
        """报告进度"""
        if callback:
            try:
                callback(stage, message)
            except Exception:
                pass