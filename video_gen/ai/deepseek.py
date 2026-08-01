#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DeepSeek V4 flash 客户端 - OpenAI 兼容接口封装

支持多服务商（通过 base_url 切换），默认 DeepSeek。
"""

import json
import time
from typing import Dict, List, Optional, Callable, Iterator
from dataclasses import dataclass

from ..config import AIConfig, DEFAULT_CONFIG
from ..utils.logger import logger


@dataclass
class ChatMessage:
    role: str  # system, user, assistant
    content: str


@dataclass
class ChatResponse:
    content: str
    model: str
    usage: Dict
    elapsed: float


class DeepSeekClient:
    """DeepSeek V4 flash 客户端（OpenAI 兼容接口）"""

    def __init__(self, config: Optional[AIConfig] = None):
        self.config = config or DEFAULT_CONFIG.ai
        self._http_session = None

    def _get_session(self):
        if self._http_session is None:
            import requests
            self._http_session = requests.Session()
        return self._http_session

    def chat(self, messages: List[Dict[str, str]],
             temperature: float = None,
             max_tokens: int = None,
             stream: bool = False,
             progress_callback: Optional[Callable] = None) -> ChatResponse:
        """
        调用聊天补全 API

        Args:
            messages: 消息列表 [{"role": "system", "content": "..."}, {"role": "user", "content": "..."}]
            temperature: 温度（默认使用配置值）
            max_tokens: 最大 token 数（默认使用配置值）
            stream: 是否流式输出
            progress_callback: 进度回调

        Returns:
            ChatResponse
        """
        if not self.config.api_key:
            raise ValueError("AI API Key 未配置，请在设置页面中填写")

        start = time.time()
        url = f"{self.config.base_url.rstrip('/')}/v1/chat/completions"

        payload = {
            "model": self.config.model,
            "messages": messages,
            "temperature": temperature if temperature is not None else self.config.temperature,
            "max_tokens": max_tokens or self.config.max_tokens,
            "stream": stream,
        }

        headers = {
            "Authorization": f"Bearer {self.config.api_key}",
            "Content-Type": "application/json",
        }

        try:
            if stream:
                return self._stream_chat(url, headers, payload, progress_callback, start)

            resp = self._get_session().post(url, json=payload, headers=headers, timeout=120)
            resp.raise_for_status()
            data = resp.json()

            content = data["choices"][0]["message"]["content"]
            usage = data.get("usage", {})
            elapsed = time.time() - start

            return ChatResponse(content=content, model=data["model"], usage=usage, elapsed=elapsed)

        except Exception as e:
            logger.error(f"AI 调用失败: {e}")
            raise

    def _stream_chat(self, url: str, headers: Dict, payload: Dict,
                     progress_callback: Optional[Callable], start: float) -> ChatResponse:
        """流式聊天"""
        import requests as req
        full_content = ""
        payload["stream"] = True

        with req.post(url, json=payload, headers=headers, stream=True, timeout=120) as resp:
            resp.raise_for_status()
            for line in resp.iter_lines(decode_unicode=True):
                if line:
                    if line.startswith("data: "):
                        data_str = line[6:]
                        if data_str.strip() == "[DONE]":
                            break
                        try:
                            chunk = json.loads(data_str)
                            delta = chunk["choices"][0]["delta"]
                            if "content" in delta:
                                full_content += delta["content"]
                                if progress_callback:
                                    progress_callback(full_content)
                        except json.JSONDecodeError:
                            continue

        elapsed = time.time() - start
        return ChatResponse(content=full_content, model=payload["model"], usage={}, elapsed=elapsed)

    def generate_article(self, system_prompt: str, user_prompt: str,
                         progress_callback: Optional[Callable] = None) -> str:
        """
        生成文章

        Args:
            system_prompt: 系统提示词（平台风格）
            user_prompt: 用户提示词（主题+搜索素材）

        Returns:
            生成的 Markdown 文章
        """
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]
        response = self.chat(messages, progress_callback=progress_callback)
        return response.content

    def generate_scripts_json(self, system_prompt: str, article: str,
                              progress_callback: Optional[Callable] = None) -> Dict:
        """
        生成 scripts.json 格式数据

        Args:
            system_prompt: 系统提示词
            article: 文章内容

        Returns:
            scripts.json 格式的字典
        """
        user_prompt = (
            f"请根据以下文章，生成完整的 scripts.json 格式数据（包含 meta 和 scenes 字段）。\n\n"
            f"每段场景需包含：scene_id, text（配音文案）, prompt（文生图提示词）, duration_sec, note。\n\n"
            f"文章内容：\n{article}\n\n"
            f"请只输出 JSON 代码块，不要包含其他内容。"
        )

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]
        response = self.chat(messages, progress_callback=progress_callback)
        return self._extract_json(response.content)

    def _extract_json(self, content: str) -> Dict:
        """从 AI 响应中提取 JSON"""
        # 尝试解析代码块中的 JSON
        import re
        json_pattern = r"```(?:json)?\s*\n?([\s\S]*?)\n?```"
        matches = re.findall(json_pattern, content)
        if matches:
            for match in matches:
                try:
                    return json.loads(match.strip())
                except json.JSONDecodeError:
                    continue

        # 直接尝试解析
        try:
            return json.loads(content.strip())
        except json.JSONDecodeError:
            raise ValueError(f"无法从 AI 响应中提取 JSON:\n{content[:500]}")