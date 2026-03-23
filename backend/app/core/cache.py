"""
TBAPS Redis Cache
Redis client for caching and session management
"""

import redis.asyncio as redis
from typing import Optional, Any
import json
import pickle
from datetime import timedelta

from app.core.config import settings

# Create Redis client
redis_client = redis.from_url(
    settings.REDIS_URL,
    encoding="utf-8",
    decode_responses=False,
    max_connections=50
)


class Cache:
    """Redis cache wrapper"""
    
    def __init__(self, client: redis.Redis):
        self.client = client
    
    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache"""
        try:
            value = await self.client.get(key)
            if value:
                return pickle.loads(value)
            return None
        except Exception as e:
            print(f"Cache get error: {e}")
            return None
    
    async def set(
        self,
        key: str,
        value: Any,
        expire: Optional[int] = None
    ) -> bool:
        """Set value in cache with optional expiration (seconds)"""
        try:
            serialized = pickle.dumps(value)
            if expire:
                await self.client.setex(key, expire, serialized)
            else:
                await self.client.set(key, serialized)
            return True
        except Exception as e:
            print(f"Cache set error: {e}")
            return False
    
    async def delete(self, key: str) -> bool:
        """Delete key from cache"""
        try:
            await self.client.delete(key)
            return True
        except Exception as e:
            print(f"Cache delete error: {e}")
            return False
    
    async def exists(self, key: str) -> bool:
        """Check if key exists"""
        try:
            return await self.client.exists(key) > 0
        except Exception as e:
            print(f"Cache exists error: {e}")
            return False
    
    async def increment(self, key: str, amount: int = 1) -> int:
        """Increment counter"""
        try:
            return await self.client.incrby(key, amount)
        except Exception as e:
            print(f"Cache increment error: {e}")
            return 0
    
    async def expire(self, key: str, seconds: int) -> bool:
        """Set expiration on key"""
        try:
            return await self.client.expire(key, seconds)
        except Exception as e:
            print(f"Cache expire error: {e}")
            return False
    
    async def ttl(self, key: str) -> int:
        """Get time to live for key"""
        try:
            return await self.client.ttl(key)
        except Exception as e:
            print(f"Cache ttl error: {e}")
            return -1
    
    async def flush(self) -> bool:
        """Flush all keys (use with caution!)"""
        try:
            await self.client.flushdb()
            return True
        except Exception as e:
            print(f"Cache flush error: {e}")
            return False


# Create cache instance
cache = Cache(redis_client)


async def get_cache() -> Cache:
    """Dependency for getting cache instance"""
    return cache


async def close_redis():
    """Close Redis connection"""
    await redis_client.close()
