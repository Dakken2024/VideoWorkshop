#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
OpenRouter 客户端 - 支持多模型聚合平台

OpenRouter 是一个统一的 API 接口，可访问多种 LLM 模型。
"""

import json
import time
from typing import Dict, List, Optional, Callable
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


class OpenRouterClient:
    """OpenRouter 客户端 - 支持多模型访问"""

    def __init__(self, api_key: str = None, base_url: str = "https://openrouter.ai/api/v1",
                 default_model: str = "deepseek/deepseek-chat-v4-flash"):
        self.api_key = api_key
        self.base_url = base_url.rstrip('/')
        self.default_model = default_model
        self._http_session = None

        # 支持的模型列表
        self.supported_models = [
            "deepseek/deepseek-chat-v4-flash",
            "deepseek/deepseek-r1",
            "openai/gpt-4o",
            "anthropic/claude-3.5-sonnet",
            "google/gemini-pro-1.5",
            "meta-llama/llama-3.1-405b-instruct",
            "qwen/qwen-2.5-72b-instruct",
        ]

    def _get_session(self):
        if self._http_session is None:
            import requests
            self._http_session = requests.Session()
            self._http_session.headers.update({
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
                "HTTP-Referer": "https://github.com/video-gen",
                "X-Title": "VideoGen Workshop",
            })
        return self._http_session

    def chat(self, messages: List[Dict[str, str]],
             model: str = None,
             temperature: float = 0.7,
             max_tokens: int = 4096,
             stream: bool = False,
             progress_callback: Optional[Callable] = None) -> ChatResponse:
        """
        调用聊天补全 API

        Args:
            messages: 消息列表
            model: 模型名称（默认使用 deepseek-chat-v4-flash）
            temperature: 温度
            max_tokens: 最大 token 数
            stream: 是否流式输出
            progress_callback: 进度回调

        Returns:
            ChatResponse
        """
        if not self.api_key:
            raise ValueError("OpenRouter API Key 未配置")

        start = time.time()
        url = f"{self.base_url}/chat/completions"

        payload = {
            "model": model or self.default_model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": stream,
        }

        try:
            if stream:
                return self._stream_chat(url, payload, progress_callback, start)

            resp = self._get_session().post(url, json=payload, timeout=120)
            resp.raise_for_status()
            data = resp.json()

            content = data["choices"][0]["message"]["content"]
            usage = data.get("usage", {})
            model_used = data.get("model", payload["model"])
            elapsed = time.time() - start

            logger.info(f"OpenRouter 调用成功：{model_used}, 耗时：{elapsed:.2f}s")
            return ChatResponse(content=content, model=model_used, usage=usage, elapsed=elapsed)

        except Exception as e:
            logger.error(f"OpenRouter 调用失败：{e}")
            raise

    def _stream_chat(self, url: str, payload: Dict,
                     progress_callback: Optional[Callable], start: float) -> ChatResponse:
        """流式聊天"""
        import requests as req
        full_content = ""
        payload["stream"] = True

        with req.post(url, json=payload, stream=True, timeout=120) as resp:
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
                         model: str = None,
                         progress_callback: Optional[Callable] = None) -> str:
        """生成文章"""
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]
        response = self.chat(messages, model=model, progress_callback=progress_callback)
        return response.content

    def generate_scripts_json(self, system_prompt: str, article: str,
                              model: str = None,
                              progress_callback: Optional[Callable] = None) -> Dict:
        """生成 scripts.json 格式数据"""
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
        response = self.chat(messages, model=model, progress_callback=progress_callback)
        return self._extract_json(response.content)

    def enhance_prompt(self, prompt: str, style: str = "default",
                       model: str = None,
                       progress_callback: Optional[Callable] = None) -> str:
        """
        优化文生图提示词

        Args:
            prompt: 原始提示词
            style: 风格（default, cinematic, anime, realistic, artistic）
            model: 使用的模型
            progress_callback: 进度回调

        Returns:
            优化后的提示词
        """
        style_prompts = {
            "default": "清晰、详细、适合 AI 绘画",
            "cinematic": "电影感、戏剧性光线、高对比度",
            "anime": "日系动漫风格、赛璐璐上色",
            "realistic": "超写实、照片级真实感",
            "artistic": "艺术风格、油画质感",
        }

        system_prompt = f"""你是一个专业的 AI 绘画提示词优化专家。
你的任务是将用户提供的简单提示词扩展为详细、专业、适合 Midjourney/Stable Diffusion 的高质量提示词。

## 要求
1. 保持原意不变
2. 添加具体的视觉细节（构图、光线、色彩、氛围）
3. 指定艺术风格和渲染方式
4. 输出英文提示词
5. 不包含解释说明，只输出优化后的提示词

## 目标风格
{style_prompts.get(style, style_prompts['default'])}"""

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"优化以下提示词：{prompt}"},
        ]
        response = self.chat(messages, model=model, progress_callback=progress_callback)
        return response.content.strip()

    def _extract_json(self, content: str) -> Dict:
        """从 AI 响应中提取 JSON"""
        import re
        json_pattern = r"```(?:json)?\s*\n?([\s\S]*?)\n?```"
        matches = re.findall(json_pattern, content)
        if matches:
            for match in matches:
                try:
                    return json.loads(match.strip())
                except json.JSONDecodeError:
                    continue

        try:
            return json.loads(content.strip())
        except json.JSONDecodeError:
            raise ValueError(f"无法从 AI 响应中提取 JSON:\n{content[:500]}")

    def list_models(self) -> List[str]:
        """获取支持的模型列表"""
        return self.supported_models.copy()
