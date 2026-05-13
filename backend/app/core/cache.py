"""
性能监控和缓存
"""
import functools
import json
import logging
import time
from collections.abc import Callable
from typing import Any

import redis

from app.core.config import settings

logger = logging.getLogger(__name__)

# Redis 客户端
redis_client = redis.from_url(settings.REDIS_URL)


def cache_key(*args, **kwargs) -> str:
    """生成缓存键"""
    key_parts = [str(arg) for arg in args]
    key_parts.extend([f"{k}:{v}" for k, v in kwargs.items()])
    return ":".join(key_parts)


def cached(ttl: int = 3600):
    """缓存装饰器"""
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs) -> Any:
            # 生成缓存键
            key = f"{func.__name__}:{cache_key(*args, **kwargs)}"

            # 尝试从缓存获取
            try:
                cached_value = redis_client.get(key)
                if cached_value:
                    return json.loads(cached_value)
            except Exception as e:
                logger.info(f"Cache get error: {e}")

            # 执行函数
            result = await func(*args, **kwargs)

            # 存储到缓存
            try:
                redis_client.setex(key, ttl, json.dumps(result, default=str))
            except Exception as e:
                logger.info(f"Cache set error: {e}")

            return result

        return wrapper
    return decorator


def timed(func: Callable) -> Callable:
    """性能计时装饰器"""
    @functools.wraps(func)
    async def wrapper(*args, **kwargs) -> Any:
        start_time = time.time()
        result = await func(*args, **kwargs)
        elapsed_time = time.time() - start_time
        logger.info(f"{func.__name__} took {elapsed_time:.2f}s")
        return result
    return wrapper


def clear_cache(pattern: str = "*"):
    """清除缓存"""
    keys = redis_client.keys(pattern)
    if keys:
        redis_client.delete(*keys)
