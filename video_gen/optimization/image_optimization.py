#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
图片生成深度优化模块 - 不影响核心流程的解耦设计

优化目标:
1. 提升免费文生图 API 的成功率和速度
2. 智能缓存策略，减少重复请求
3. 多 API 提供商智能路由
4. 批量预取和并行生成
5. 图片质量后处理优化

使用方式:
    from video_gen.optimization.image_optimization import OptimizedImageGenerator
    
    # 包装现有 ImageGenerator
    opt_gen = OptimizedImageGenerator(base_generator=image_gen)
    
    # 使用优化后的生成方法
    success = opt_gen.generate_with_cache(prompt, output_file)
"""

import os
import time
import hashlib
import threading
import requests
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
import json

from ..config import ImageConfig, DEFAULT_CONFIG
from ..utils.logger import logger
from ..utils.file_utils import ensure_dir


@dataclass
class CacheEntry:
    """缓存条目"""
    prompt_hash: str
    image_path: str
    created_at: datetime = field(default_factory=datetime.now)
    access_count: int = 0
    last_access: datetime = field(default_factory=datetime.now)
    metadata: Dict = field(default_factory=dict)
    
    def to_dict(self) -> Dict:
        return {
            "prompt_hash": self.prompt_hash,
            "image_path": self.image_path,
            "created_at": self.created_at.isoformat(),
            "access_count": self.access_count,
            "last_access": self.last_access.isoformat(),
            "metadata": self.metadata,
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> "CacheEntry":
        return cls(
            prompt_hash=data["prompt_hash"],
            image_path=data["image_path"],
            created_at=datetime.fromisoformat(data["created_at"]),
            access_count=data.get("access_count", 0),
            last_access=datetime.fromisoformat(data["last_access"]),
            metadata=data.get("metadata", {}),
        )


@dataclass
class APIProvider:
    """API 提供商配置"""
    name: str
    base_url: str
    priority: int = 1  # 优先级，数字越小优先级越高
    weight: float = 1.0  # 负载均衡权重
    timeout: float = 30.0
    max_retries: int = 3
    rate_limit: int = 10  # 每分钟请求数限制
    enabled: bool = True
    consecutive_failures: int = 0
    last_failure_time: Optional[float] = None
    total_requests: int = 0
    successful_requests: int = 0
    
    def is_healthy(self) -> bool:
        """检查提供商是否健康"""
        if not self.enabled:
            return False
        
        # 连续失败超过阈值，暂时禁用
        if self.consecutive_failures >= 5:
            recovery_timeout = 300.0  # 5 分钟恢复期
            if self.last_failure_time:
                elapsed = time.time() - self.last_failure_time
                if elapsed < recovery_timeout:
                    return False
            # 重置状态尝试恢复
            self.consecutive_failures = 0
        
        return True
    
    def record_success(self):
        """记录成功"""
        self.consecutive_failures = 0
        self.successful_requests += 1
        self.total_requests += 1
    
    def record_failure(self):
        """记录失败"""
        self.consecutive_failures += 1
        self.last_failure_time = time.time()
        self.total_requests += 1
    
    @property
    def success_rate(self) -> float:
        """成功率"""
        if self.total_requests == 0:
            return 1.0
        return self.successful_requests / self.total_requests


class SmartCache:
    """智能缓存管理器"""
    
    def __init__(self, cache_dir: str = "./.image_cache", 
                 max_size: int = 10000,
                 ttl_hours: int = 168):  # 默认 7 天 TTL
        self.cache_dir = cache_dir
        self.max_size = max_size
        self.ttl = timedelta(hours=ttl_hours)
        self.entries: Dict[str, CacheEntry] = {}
        self._lock = threading.RLock()
        
        ensure_dir(cache_dir)
        self._load_index()
    
    def _compute_hash(self, prompt: str, seed: int = None) -> str:
        """计算提示词哈希"""
        key = f"{prompt}:{seed}" if seed else prompt
        return hashlib.md5(key.encode()).hexdigest()
    
    def _load_index(self):
        """加载缓存索引"""
        index_file = os.path.join(self.cache_dir, "cache_index.json")
        if os.path.exists(index_file):
            try:
                with open(index_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.entries = {
                        k: CacheEntry.from_dict(v) 
                        for k, v in data.items()
                    }
                logger.info(f"加载缓存索引：{len(self.entries)} 条记录")
            except Exception as e:
                logger.error(f"加载缓存索引失败：{e}")
                self.entries = {}
    
    def _save_index(self):
        """保存缓存索引"""
        index_file = os.path.join(self.cache_dir, "cache_index.json")
        try:
            with open(index_file, 'w', encoding='utf-8') as f:
                data = {k: v.to_dict() for k, v in self.entries.items()}
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"保存缓存索引失败：{e}")
    
    def get(self, prompt: str, seed: int = None) -> Optional[str]:
        """从缓存获取图片路径"""
        with self._lock:
            key = self._compute_hash(prompt, seed)
            entry = self.entries.get(key)
            
            if not entry:
                return None
            
            # 检查 TTL
            if datetime.now() - entry.created_at > self.ttl:
                logger.debug(f"缓存过期：{key}")
                self._remove_entry(key, entry)
                return None
            
            # 检查文件是否存在
            if not os.path.exists(entry.image_path):
                logger.debug(f"缓存文件不存在：{entry.image_path}")
                self._remove_entry(key, entry)
                return None
            
            # 更新访问统计
            entry.access_count += 1
            entry.last_access = datetime.now()
            
            logger.debug(f"缓存命中：{key} (访问次数：{entry.access_count})")
            return entry.image_path
    
    def set(self, prompt: str, image_path: str, seed: int = None, 
            metadata: Dict = None) -> bool:
        """将图片添加到缓存"""
        with self._lock:
            key = self._compute_hash(prompt, seed)
            
            # 如果已存在，跳过
            if key in self.entries:
                return True
            
            # 检查缓存大小，必要时清理
            if len(self.entries) >= self.max_size:
                self._evict_oldest()
            
            entry = CacheEntry(
                prompt_hash=key,
                image_path=image_path,
                metadata=metadata or {},
            )
            self.entries[key] = entry
            self._save_index()
            
            logger.debug(f"缓存添加：{key}")
            return True
    
    def _remove_entry(self, key: str, entry: CacheEntry):
        """移除缓存条目"""
        if key in self.entries:
            del self.entries[key]
            self._save_index()
    
    def _evict_oldest(self):
        """淘汰最旧的缓存"""
        if not self.entries:
            return
        
        # 按创建时间排序，删除最旧的 10%
        sorted_entries = sorted(
            self.entries.items(),
            key=lambda x: x[1].created_at
        )
        evict_count = max(1, len(self.entries) // 10)
        
        for i in range(evict_count):
            key, entry = sorted_entries[i]
            self._remove_entry(key, entry)
        
        logger.info(f"缓存清理：淘汰 {evict_count} 条旧记录")
    
    def get_stats(self) -> Dict:
        """获取缓存统计"""
        with self._lock:
            total_size = sum(
                os.path.getsize(e.image_path) 
                for e in self.entries.values() 
                if os.path.exists(e.image_path)
            )
            
            return {
                "total_entries": len(self.entries),
                "total_size_mb": round(total_size / 1024 / 1024, 2),
                "max_size": self.max_size,
                "hit_rate": self._calculate_hit_rate(),
            }
    
    def _calculate_hit_rate(self) -> float:
        """计算命中率（基于访问次数）"""
        if not self.entries:
            return 0.0
        
        total_accesses = sum(e.access_count for e in self.entries.values())
        unique_hits = sum(1 for e in self.entries.values() if e.access_count > 0)
        
        return round(unique_hits / len(self.entries) * 100, 2) if self.entries else 0.0


class APIRouter:
    """智能 API 路由器 - 动态选择最佳 API 提供商"""
    
    def __init__(self):
        self.providers: List[APIProvider] = []
        self._lock = threading.Lock()
        self._register_default_providers()
    
    def _register_default_providers(self):
        """注册默认 API 提供商"""
        # Pollinations 系列
        self.providers.extend([
            APIProvider(
                name="pollinations-flux",
                base_url="https://gen.pollinations.ai/image/{prompt}?model=flux&width=1080&height=1920&enhance=false&seed={seed}",
                priority=1,
                weight=1.0,
                timeout=30.0,
                rate_limit=15,
            ),
            APIProvider(
                name="pollinations-flux-realism",
                base_url="https://gen.pollinations.ai/image/{prompt}?model=flux-realism&width=1080&height=1920&enhance=false&seed={seed}",
                priority=2,
                weight=0.9,
                timeout=30.0,
                rate_limit=15,
            ),
            APIProvider(
                name="pollinations-turbo",
                base_url="https://gen.pollinations.ai/image/{prompt}?model=turbo&width=1080&height=1920&enhance=false&seed={seed}",
                priority=3,
                weight=0.8,
                timeout=20.0,
                rate_limit=20,
            ),
            APIProvider(
                name="pollinations-legacy",
                base_url="https://pollinations.ai/p/{prompt}?width=1080&height=1920&seed={seed}",
                priority=4,
                weight=0.7,
                timeout=45.0,
                rate_limit=10,
            ),
        ])
    
    def select_provider(self) -> Optional[APIProvider]:
        """选择最佳 API 提供商"""
        with self._lock:
            # 过滤出健康的提供商
            healthy = [p for p in self.providers if p.is_healthy()]
            
            if not healthy:
                logger.warning("所有 API 提供商都不健康")
                return None
            
            # 按优先级和成功率排序
            healthy.sort(key=lambda p: (p.priority, -p.success_rate))
            
            # 返回优先级最高的
            selected = healthy[0]
            logger.debug(f"选择 API 提供商：{selected.name} (成功率：{selected.success_rate:.1%})")
            return selected
    
    def get_fallback_providers(self, exclude: APIProvider = None) -> List[APIProvider]:
        """获取备用 API 提供商列表"""
        with self._lock:
            providers = [p for p in self.providers if p.is_healthy() and p != exclude]
            providers.sort(key=lambda p: (p.priority, -p.success_rate))
            return providers
    
    def get_all_providers(self) -> List[APIProvider]:
        """获取所有提供商"""
        return self.providers.copy()
    
    def get_stats(self) -> Dict:
        """获取所有提供商统计"""
        return {
            p.name: {
                "success_rate": f"{p.success_rate:.1%}",
                "total_requests": p.total_requests,
                "consecutive_failures": p.consecutive_failures,
                "enabled": p.enabled,
            }
            for p in self.providers
        }


class OptimizedImageGenerator:
    """优化的图片生成器 - 装饰器模式，不修改原有逻辑"""
    
    def __init__(self, base_generator=None, config: ImageConfig = None):
        """
        Args:
            base_generator: 原有的 ImageGenerator 实例
            config: 图片配置
        """
        self.base_generator = base_generator
        self.config = config or DEFAULT_CONFIG.image
        
        # 初始化优化组件
        self.cache = SmartCache(
            cache_dir="./.image_cache",
            max_size=5000,
            ttl_hours=168,  # 7 天
        )
        
        self.router = APIRouter()
        
        # 并发控制
        self.max_workers = 5
        self.executor = ThreadPoolExecutor(max_workers=self.max_workers)
        
        # 速率限制
        self.rate_limiter_lock = threading.Lock()
        self.last_call_time = 0.0
        self.min_interval = 60.0 / 15.0  # 每秒调用次数
    
    def generate_with_cache(self, prompt: str, output_file: str, 
                           scene_id: int = None, seed: int = None,
                           force: bool = False) -> bool:
        """
        带缓存的图片生成 - 优先检查缓存
        
        Args:
            prompt: 提示词
            output_file: 输出路径
            scene_id: 场景 ID
            seed: 随机种子
            force: 是否强制重新生成（忽略缓存）
        
        Returns:
            是否成功
        """
        # 检查输出文件是否已存在
        if not force and os.path.exists(output_file) and os.path.getsize(output_file) > 10240:
            logger.debug(f"文件已存在：{output_file}")
            return True
        
        # 检查缓存（除非强制重新生成）
        if not force:
            cached_path = self.cache.get(prompt, seed)
            if cached_path and os.path.exists(cached_path):
                # 复制缓存文件到输出位置
                try:
                    ensure_dir(os.path.dirname(output_file))
                    import shutil
                    shutil.copy2(cached_path, output_file)
                    logger.info(f"使用缓存图片：{cached_path} -> {output_file}")
                    return True
                except Exception as e:
                    logger.warning(f"复制缓存文件失败：{e}")
        
        # 缓存未命中，执行实际生成
        success = self._generate_with_smart_retry(prompt, output_file, scene_id, seed)
        
        # 如果成功，添加到缓存
        if success and os.path.exists(output_file):
            self.cache.set(prompt, output_file, seed)
        
        return success
    
    def _generate_with_smart_retry(self, prompt: str, output_file: str,
                                   scene_id: int = None, seed: int = None) -> bool:
        """
        智能重试生成 - 使用 API 路由器动态选择最佳提供商
        
        Returns:
            是否成功
        """
        # 准备提示词
        processed_prompt = self._prepare_prompt(prompt)
        actual_seed = seed or int(time.time() * 1000) % 1000000000
        
        # 尝试主提供商
        provider = self.router.select_provider()
        if not provider:
            logger.error("没有可用的 API 提供商")
            return self._fallback_to_placeholder(output_file)
        
        # 构建 URL
        url = provider.base_url.format(
            prompt=requests.utils.quote(processed_prompt),
            seed=actual_seed
        )
        
        # 执行请求
        success = self._call_api(provider, url, output_file)
        
        if success:
            provider.record_success()
            return True
        
        # 主提供商失败，尝试备用提供商
        logger.warning(f"主提供商 {provider.name} 失败，尝试备用提供商...")
        provider.record_failure()
        
        for fallback in self.router.get_fallback_providers(exclude=provider):
            url = fallback.base_url.format(
                prompt=requests.utils.quote(processed_prompt),
                seed=actual_seed + hash(fallback.name) % 1000
            )
            
            if self._call_api(fallback, url, output_file):
                fallback.record_success()
                return True
            
            fallback.record_failure()
        
        # 所有提供商都失败，使用占位图
        logger.error("所有 API 提供商都失败，使用占位图")
        return self._fallback_to_placeholder(output_file)
    
    def _prepare_prompt(self, prompt: str) -> str:
        """优化提示词"""
        processed = prompt.strip()
        
        # 自动添加纵横比
        if '--ar' not in processed.lower():
            processed += ' --ar 9:16'
        
        # 自动添加风格
        if '--style' not in processed.lower():
            processed += ' --style raw'
        
        return processed
    
    def _call_api(self, provider: APIProvider, url: str, 
                  output_file: str) -> bool:
        """调用 API 生成图片"""
        # 速率限制
        self._apply_rate_limit(provider.rate_limit)
        
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Accept': 'image/webp,image/apng,image/*,*/*;q=0.8',
            }
            
            response = requests.get(url, headers=headers, timeout=provider.timeout)
            
            if response.status_code == 200:
                content = response.content
                
                # 验证图片
                if self._is_valid_image(content):
                    ensure_dir(os.path.dirname(output_file))
                    with open(output_file, 'wb') as f:
                        f.write(content)
                    
                    logger.success(f"{provider.name}: 生成成功 ({len(content)} bytes)")
                    return True
                else:
                    logger.debug(f"{provider.name}: 返回内容无效")
            else:
                logger.debug(f"{provider.name}: HTTP {response.status_code}")
        
        except requests.exceptions.Timeout:
            logger.debug(f"{provider.name}: 超时")
        except requests.exceptions.ConnectionError:
            logger.debug(f"{provider.name}: 连接错误")
        except Exception as e:
            logger.debug(f"{provider.name}: {str(e)[:80]}")
        
        return False
    
    def _apply_rate_limit(self, rate_limit: int):
        """应用速率限制"""
        with self.rate_limiter_lock:
            min_interval = 60.0 / rate_limit
            now = time.time()
            elapsed = now - self.last_call_time
            
            if elapsed < min_interval:
                wait_time = min_interval - elapsed
                time.sleep(wait_time)
            
            self.last_call_time = time.time()
    
    def _is_valid_image(self, content: bytes) -> bool:
        """验证图片有效性"""
        if len(content) < 10240:
            return False
        
        # 检查文件头
        valid_headers = [b'\xff\xd8', b'\x89PNG', b'RIFF']
        if not any(content.startswith(h) for h in valid_headers):
            return False
        
        # 排除 HTML
        if content.startswith(b'<!DOCTYPE') or content.startswith(b'<html'):
            return False
        
        return True
    
    def _fallback_to_placeholder(self, output_file: str) -> bool:
        """生成占位图"""
        try:
            from PIL import Image
            img = Image.new('RGB', (1080, 1920), color=(50, 50, 60))
            ensure_dir(os.path.dirname(output_file))
            img.save(output_file, 'JPEG', quality=85)
            logger.warning(f"使用占位图：{output_file}")
            return True
        except Exception as e:
            logger.error(f"生成占位图失败：{e}")
            return False
    
    def batch_generate_optimized(self, scenes: List[Dict], output_dir: str,
                                 project_name: str = None,
                                 progress_callback=None) -> List[str]:
        """
        优化的批量生成 - 并发处理
        
        Args:
            scenes: 场景列表
            output_dir: 输出目录
            project_name: 项目名称
            progress_callback: 进度回调
        
        Returns:
            图片文件路径列表
        """
        ensure_dir(output_dir)
        image_files = []
        total = len(scenes)
        
        # 准备任务
        tasks = []
        for i, scene in enumerate(scenes):
            prompt = scene.get('prompt', '')
            scene_id = scene.get('scene_id', i + 1)
            seed = scene.get('seed')
            image_path = os.path.join(output_dir, f"scene_{i:03d}.jpg")
            
            tasks.append({
                'prompt': prompt,
                'output_file': image_path,
                'scene_id': scene_id,
                'seed': seed,
                'index': i,
            })
        
        # 并发执行
        completed = 0
        results = []
        
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            future_to_task = {
                executor.submit(
                    self.generate_with_cache,
                    task['prompt'],
                    task['output_file'],
                    task['scene_id'],
                    task['seed']
                ): task
                for task in tasks
            }
            
            for future in as_completed(future_to_task):
                task = future_to_task[future]
                try:
                    success = future.result()
                    results.append((task['index'], task['output_file'], success))
                except Exception as e:
                    logger.error(f"场景 {task['scene_id']} 生成失败：{e}")
                    results.append((task['index'], task['output_file'], False))
                
                completed += 1
                if progress_callback:
                    progress_callback(completed, total, f"生成图片：{completed}/{total}")
        
        # 按顺序整理结果
        results.sort(key=lambda x: x[0])
        for _, path, success in results:
            image_files.append(path)
            if not success:
                logger.warning(f"场景图片生成失败：{path}")
        
        logger.success(f"批量生成完成：{sum(1 for _, _, s in results if s)}/{total}")
        return image_files
    
    def get_optimization_stats(self) -> Dict:
        """获取优化统计信息"""
        return {
            "cache": self.cache.get_stats(),
            "api_providers": self.router.get_stats(),
            "max_workers": self.max_workers,
        }
    
    def clear_cache(self, older_than_days: int = None):
        """清理缓存"""
        with self.cache._lock:
            if older_than_days is None:
                # 清空所有缓存
                self.cache.entries.clear()
                self.cache._save_index()
                logger.info("缓存已清空")
            else:
                # 清理指定天数之前的缓存
                cutoff = datetime.now() - timedelta(days=older_than_days)
                to_remove = [
                    k for k, v in self.cache.entries.items()
                    if v.created_at < cutoff
                ]
                for key in to_remove:
                    self.cache._remove_entry(key, self.cache.entries[key])
                logger.info(f"清理了 {len(to_remove)} 条旧缓存")
    
    def shutdown(self):
        """关闭资源"""
        self.executor.shutdown(wait=True)
        logger.info("优化器已关闭")
