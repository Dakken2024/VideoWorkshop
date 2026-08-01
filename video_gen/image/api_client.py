#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
API 客户端 - 图片生成 API 调用，含频率限制和重试机制
"""

import os
import time
import random
import hashlib
import requests
import threading
from typing import Dict, Optional, Callable, List

from ..config import ImageConfig, DEFAULT_CONFIG
from ..utils.logger import logger


class APIRateLimiter:
    """API 调用频率限制器"""

    def __init__(self, config: ImageConfig = None):
        self.config = config or DEFAULT_CONFIG.image
        self.last_call_time = 0.0
        self.consecutive_failures = 0
        self.total_calls = 0
        self.successful_calls = 0
        self._lock = threading.Lock()

    def wait_if_needed(self):
        """等待直到可以发起下一次调用"""
        with self._lock:
            now = time.time()
            elapsed = now - self.last_call_time
            interval = min(
                self.config.min_interval * (2 ** self.consecutive_failures),
                self.config.max_interval
            )
            if elapsed < interval:
                wait = interval - elapsed
                time.sleep(wait)
            self.last_call_time = time.time()

    def record_success(self):
        """记录成功"""
        with self._lock:
            self.consecutive_failures = 0
            self.successful_calls += 1
            self.total_calls += 1

    def record_failure(self) -> bool:
        """记录失败，返回是否应继续重试"""
        with self._lock:
            self.consecutive_failures += 1
            self.total_calls += 1
            return self.consecutive_failures < self.config.max_retries

    def get_stats(self) -> Dict:
        return {
            "total_calls": self.total_calls,
            "successful_calls": self.successful_calls,
            "success_rate": f"{self.successful_calls / max(self.total_calls, 1) * 100:.1f}%",
            "consecutive_failures": self.consecutive_failures
        }


class ImageAPIClient:
    """图片生成 API 客户端"""

    def __init__(self, config: ImageConfig = None):
        self.config = config or DEFAULT_CONFIG.image
        self.rate_limiter = APIRateLimiter(config)
        self.user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
        ]
        self.session = requests.Session()

    def generate(self, prompt: str, output_file: str, scene_id: int = None,
                 seed: int = None, progress_callback: Optional[Callable] = None) -> bool:
        """
        生成图片 - 多 API 策略

        Args:
            prompt: 提示词
            output_file: 输出路径
            scene_id: 场景 ID
            seed: 随机种子
            progress_callback: 进度回调

        Returns:
            是否成功
        """
        api_configs = self._get_api_configs(prompt, seed)

        for api_config in api_configs:
            self.rate_limiter.wait_if_needed()
            if self._call_api(api_config, output_file):
                self.rate_limiter.record_success()
                return True
            if not self.rate_limiter.record_failure():
                break

        return False

    def _get_api_configs(self, prompt: str, seed: int) -> List[Dict]:
        """获取 API 配置列表（按优先级排序）"""
        processed_prompt = prompt.strip()
        if '--ar' not in processed_prompt.lower():
            processed_prompt += ' --ar 9:16'
        if '--style' not in processed_prompt.lower():
            processed_prompt += ' --style raw'

        encoded = requests.utils.quote(processed_prompt)
        actual_seed = seed or random.randint(1, 999999999)

        return [
            {
                'name': 'Gen Pollinations (flux)',
                'url': f"https://gen.pollinations.ai/image/{encoded}?model=flux&width=1080&height=1920&enhance=false&seed={actual_seed}&key={self.config.api_key}",
                'timeout': self.config.api_timeout
            },
            {
                'name': 'Gen Pollinations (flux-realism)',
                'url': f"https://gen.pollinations.ai/image/{encoded}?model=flux-realism&width=1080&height=1920&enhance=false&seed={actual_seed + 1}&key={self.config.api_key}",
                'timeout': self.config.api_timeout
            },
            {
                'name': 'Gen Pollinations (turbo)',
                'url': f"https://gen.pollinations.ai/image/{encoded}?model=turbo&width=1080&height=1920&enhance=false&seed={actual_seed + 2}&key={self.config.api_key}",
                'timeout': self.config.api_timeout
            },
            {
                'name': 'Pollinations (legacy)',
                'url': f"https://pollinations.ai/p/{encoded}?width=1080&height=1920&seed={actual_seed + 3}",
                'timeout': 45
            }
        ]

    def _call_api(self, api_config: Dict, output_file: str) -> bool:
        """执行单个 API 调用"""
        try:
            headers = {
                'User-Agent': random.choice(self.user_agents),
                'Accept': 'image/webp,image/apng,image/*,*/*;q=0.8',
                'Cache-Control': 'no-cache',
            }

            logger.debug(f"API: {api_config['name']}")
            response = self.session.get(
                api_config['url'],
                headers=headers,
                timeout=api_config['timeout']
            )

            if response.status_code == 200:
                content = response.content
                if self._is_valid_image(content, len(content)):
                    os.makedirs(os.path.dirname(output_file), exist_ok=True)
                    with open(output_file, 'wb') as f:
                        f.write(content)
                    logger.success(f"{api_config['name']}: {len(content)} bytes")
                    return True
                else:
                    logger.debug(f"{api_config['name']}: 返回内容不是有效图片")
            else:
                logger.debug(f"{api_config['name']}: HTTP {response.status_code}")

        except requests.exceptions.Timeout:
            logger.debug(f"{api_config['name']}: 超时")
        except requests.exceptions.ConnectionError:
            logger.debug(f"{api_config['name']}: 连接错误")
        except Exception as e:
            logger.debug(f"{api_config['name']}: {str(e)[:80]}")

        return False

    def _is_valid_image(self, content: bytes, size: int) -> bool:
        """验证图片有效性"""
        if size < 10240:
            return False
        valid_headers = [b'\xff\xd8', b'\x89PNG', b'RIFF']
        if not any(content.startswith(h) for h in valid_headers):
            if content.startswith(b'RIFF') and len(content) > 12 and content[8:12] == b'WEBP':
                return True
            return False
        if content.startswith(b'<!DOCTYPE') or content.startswith(b'<html'):
            return False
        return True