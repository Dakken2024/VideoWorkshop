"""
异步并发 API 请求工具
使用 asyncio 实现高并发 API 调用，支持速率限制和重试
"""
import asyncio
import aiohttp
import time
from typing import Any, Dict, List, Optional, Callable
from dataclasses import dataclass
from functools import wraps


@dataclass
class RateLimitConfig:
    """速率限制配置"""
    requests_per_second: float = 1.0
    burst_size: int = 5
    retry_delay: float = 1.0
    max_retries: int = 3


class AsyncRateLimiter:
    """异步速率限制器"""
    
    def __init__(self, config: RateLimitConfig = None):
        self.config = config or RateLimitConfig()
        self._tokens = self.config.burst_size
        self._last_refill = time.time()
        self._lock = asyncio.Lock()
    
    async def acquire(self):
        """获取令牌"""
        async with self._lock:
            now = time.time()
            elapsed = now - self._last_refill
            
            # 补充令牌
            refill_amount = elapsed * self.config.requests_per_second
            self._tokens = min(self.config.burst_size, self._tokens + refill_amount)
            self._last_refill = now
            
            if self._tokens < 1:
                wait_time = (1 - self._tokens) / self.config.requests_per_second
                await asyncio.sleep(wait_time)
                self._tokens = 0
            else:
                self._tokens -= 1


class AsyncAPIClient:
    """异步 API 客户端"""
    
    def __init__(self, base_url: str, api_key: str, 
                 rate_limit: RateLimitConfig = None,
                 timeout: int = 60):
        self.base_url = base_url.rstrip('/')
        self.api_key = api_key
        self.rate_limiter = AsyncRateLimiter(rate_limit)
        self.timeout = timeout
        self._session: Optional[aiohttp.ClientSession] = None
    
    async def _get_session(self) -> aiohttp.ClientSession:
        """获取或创建会话"""
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(
                headers={
                    'Authorization': f'Bearer {self.api_key}',
                    'Content-Type': 'application/json'
                },
                timeout=aiohttp.ClientTimeout(total=self.timeout)
            )
        return self._session
    
    async def close(self):
        """关闭会话"""
        if self._session and not self._session.closed:
            await self._session.close()
    
    async def request(self, method: str, endpoint: str, 
                      data: Dict = None, params: Dict = None,
                      retry_count: int = 0) -> Dict[str, Any]:
        """发送 HTTP 请求"""
        await self.rate_limiter.acquire()
        
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        session = await self._get_session()
        
        try:
            async with session.request(
                method, url, json=data, params=params
            ) as response:
                result = await response.json()
                
                if response.status >= 400:
                    if retry_count < self.rate_limiter.config.max_retries:
                        delay = self.rate_limiter.config.retry_delay * (2 ** retry_count)
                        await asyncio.sleep(delay)
                        return await self.request(method, endpoint, data, params, retry_count + 1)
                    raise Exception(f"API Error: {response.status} - {result}")
                
                return result
        
        except aiohttp.ClientError as e:
            if retry_count < self.rate_limiter.config.max_retries:
                delay = self.rate_limiter.config.retry_delay * (2 ** retry_count)
                await asyncio.sleep(delay)
                return await self.request(method, endpoint, data, params, retry_count + 1)
            raise Exception(f"Request failed: {e}")
    
    async def post(self, endpoint: str, data: Dict = None) -> Dict[str, Any]:
        """POST 请求"""
        return await self.request('POST', endpoint, data)
    
    async def get(self, endpoint: str, params: Dict = None) -> Dict[str, Any]:
        """GET 请求"""
        return await self.request('GET', endpoint, params=params)
    
    async def stream_post(self, endpoint: str, data: Dict, 
                          callback: Callable[[str], None]) -> str:
        """流式 POST 请求"""
        await self.rate_limiter.acquire()
        
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        session = await self._get_session()
        
        full_content = []
        
        try:
            async with session.post(url, json=data) as response:
                if response.status >= 400:
                    raise Exception(f"API Error: {response.status}")
                
                async for line in response.content:
                    line = line.decode('utf-8').strip()
                    if line.startswith('data: '):
                        content = line[6:]
                        if content != '[DONE]':
                            full_content.append(content)
                            if callback:
                                callback(content)
                
                return ''.join(full_content)
        
        except aiohttp.ClientError as e:
            raise Exception(f"Stream request failed: {e}")


async def concurrent_map(func: Callable, items: List[Any], 
                         max_concurrency: int = 5) -> List[Any]:
    """并发执行映射"""
    semaphore = asyncio.Semaphore(max_concurrency)
    
    async def wrapped(item):
        async with semaphore:
            return await func(item)
    
    tasks = [wrapped(item) for item in items]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    # 处理异常
    processed = []
    for i, result in enumerate(results):
        if isinstance(result, Exception):
            print(f"Task {i} failed: {result}")
            processed.append(None)
        else:
            processed.append(result)
    
    return processed


def async_retry(max_retries: int = 3, delay: float = 1.0):
    """异步重试装饰器"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            last_exception = None
            for attempt in range(max_retries):
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    if attempt < max_retries - 1:
                        wait_time = delay * (2 ** attempt)
                        await asyncio.sleep(wait_time)
            raise last_exception
        return wrapper
    return decorator


# 示例用法
async def example_usage():
    """示例用法"""
    client = AsyncAPIClient(
        base_url="https://api.example.com",
        api_key="your-api-key",
        rate_limit=RateLimitConfig(requests_per_second=2.0)
    )
    
    try:
        # 单个请求
        result = await client.post('/generate', {'prompt': 'test'})
        
        # 并发请求
        prompts = ['prompt1', 'prompt2', 'prompt3']
        
        async def generate_one(prompt):
            return await client.post('/generate', {'prompt': prompt})
        
        results = await concurrent_map(generate_one, prompts, max_concurrency=3)
        
        # 流式请求
        full_text = await client.stream_post(
            '/stream_generate',
            {'prompt': 'long text'},
            callback=lambda chunk: print(chunk, end='')
        )
    
    finally:
        await client.close()


if __name__ == '__main__':
    asyncio.run(example_usage())
