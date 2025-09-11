"""
Smart API Cache System for Dual AI Trading Bot
Implémente un système de cache intelligent pour optimiser les appels API
et réduire la latence entre Scouter → IA1 → IA2
"""

import asyncio
import time
import logging
from typing import Dict, Any, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass
import json
import hashlib
from enum import Enum

logger = logging.getLogger(__name__)

class CacheType(Enum):
    PRICE = "price"           # Current price data
    OHLCV = "ohlcv"          # OHLCV historical data  
    MARKET_DATA = "market"    # Market cap, volume, etc.
    TECHNICAL = "technical"   # Technical indicators
    GLOBAL_MARKET = "global"  # Global market context

@dataclass
class CacheEntry:
    """Single cache entry with metadata"""
    data: Any
    timestamp: float
    ttl: int  # Time to live in seconds
    access_count: int = 0
    last_access: float = 0
    
    def is_expired(self) -> bool:
        """Check if cache entry is expired"""
        return time.time() - self.timestamp > self.ttl
    
    def is_fresh(self, max_age: int = None) -> bool:
        """Check if cache entry is fresh enough"""
        age = time.time() - self.timestamp
        return age < (max_age or self.ttl)
    
    def touch(self):
        """Update access metadata"""
        self.access_count += 1
        self.last_access = time.time()

class SmartAPICache:
    """
    🧠 Cache intelligent avec TTL adaptatif et éviction LRU
    Optimisé pour les patterns d'accès du trading bot
    """
    
    def __init__(self):
        self.caches = {
            CacheType.PRICE: {},      # TTL: 30s (price changes fast)
            CacheType.OHLCV: {},      # TTL: 5min (OHLCV relatively stable)
            CacheType.MARKET_DATA: {},# TTL: 2min (market data medium frequency)  
            CacheType.TECHNICAL: {},  # TTL: 10min (technical indicators stable)
            CacheType.GLOBAL_MARKET: {} # TTL: 15min (global context slow change)
        }
        
        # TTL configuration per cache type
        self.ttl_config = {
            CacheType.PRICE: 30,        # 30 seconds
            CacheType.OHLCV: 300,       # 5 minutes
            CacheType.MARKET_DATA: 120, # 2 minutes
            CacheType.TECHNICAL: 600,   # 10 minutes
            CacheType.GLOBAL_MARKET: 900 # 15 minutes
        }
        
        # Maximum entries per cache type to prevent memory bloat
        self.max_entries = {
            CacheType.PRICE: 100,       # 100 symbols max
            CacheType.OHLCV: 50,        # 50 symbols max
            CacheType.MARKET_DATA: 200, # 200 symbols max
            CacheType.TECHNICAL: 75,    # 75 symbols max  
            CacheType.GLOBAL_MARKET: 10 # 10 global contexts max
        }
        
        # Stats tracking
        self.stats = {
            "hits": 0,
            "misses": 0,
            "evictions": 0,
            "errors": 0
        }
        
        # Background cleanup task
        self._cleanup_task = None
        self._start_cleanup_task()
    
    def _start_cleanup_task(self):
        """Start background cleanup task"""
        self._cleanup_task = asyncio.create_task(self._cleanup_loop())
    
    async def _cleanup_loop(self):
        """Background task to clean expired entries"""
        while True:
            try:
                await asyncio.sleep(60)  # Cleanup every minute
                self._cleanup_expired()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Cache cleanup error: {e}")
                await asyncio.sleep(60)
    
    def _cleanup_expired(self):
        """Remove expired entries from all caches"""
        total_removed = 0
        
        for cache_type, cache in self.caches.items():
            removed = 0
            expired_keys = []
            
            for key, entry in cache.items():
                if entry.is_expired():
                    expired_keys.append(key)
            
            for key in expired_keys:
                del cache[key]
                removed += 1
            
            total_removed += removed
            
            if removed > 0:
                logger.debug(f"🧹 Cache cleanup: {cache_type.value} removed {removed} expired entries")
        
        if total_removed > 0:
            logger.info(f"🧹 Cache cleanup completed: {total_removed} expired entries removed")
    
    def _evict_lru(self, cache_type: CacheType):
        """Evict least recently used entries when cache is full"""
        cache = self.caches[cache_type]
        max_size = self.max_entries[cache_type]
        
        if len(cache) <= max_size:
            return
        
        # Sort by last access time (LRU first)
        sorted_entries = sorted(
            cache.items(), 
            key=lambda x: x[1].last_access or x[1].timestamp
        )
        
        # Remove oldest 25% of entries
        remove_count = len(cache) // 4
        for i in range(remove_count):
            key, _ = sorted_entries[i]
            del cache[key]
            self.stats["evictions"] += 1
        
        logger.debug(f"🗑️ Cache LRU eviction: {cache_type.value} removed {remove_count} entries")
    
    def _generate_key(self, symbol: str, params: Dict = None, prefix: str = "") -> str:
        """Generate cache key from symbol and parameters"""
        key_parts = [prefix, symbol.upper()]
        
        if params:
            # Sort params for consistent key generation
            sorted_params = sorted(params.items())
            params_str = json.dumps(sorted_params, sort_keys=True)
            # Use hash for long parameter strings
            if len(params_str) > 50:
                params_hash = hashlib.md5(params_str.encode()).hexdigest()[:8]
                key_parts.append(params_hash)
            else:
                key_parts.append(params_str)
        
        return ":".join(key_parts)
    
    async def get(self, cache_type: CacheType, symbol: str, params: Dict = None, 
                  prefix: str = "") -> Optional[Any]:
        """Get data from cache"""
        try:
            key = self._generate_key(symbol, params, prefix)
            cache = self.caches[cache_type]
            
            if key not in cache:
                self.stats["misses"] += 1
                return None
            
            entry = cache[key]
            
            # Check if expired
            if entry.is_expired():
                del cache[key]
                self.stats["misses"] += 1
                return None
            
            # Update access metadata
            entry.touch()
            self.stats["hits"] += 1
            
            logger.debug(f"🎯 Cache HIT: {cache_type.value}:{key}")
            return entry.data
            
        except Exception as e:
            logger.error(f"Cache get error: {e}")
            self.stats["errors"] += 1
            return None
    
    async def set(self, cache_type: CacheType, symbol: str, data: Any,
                  params: Dict = None, prefix: str = "", custom_ttl: int = None):
        """Set data in cache"""
        try:
            key = self._generate_key(symbol, params, prefix)
            cache = self.caches[cache_type]
            
            # Use custom TTL or default
            ttl = custom_ttl or self.ttl_config[cache_type]
            
            # Create cache entry
            entry = CacheEntry(
                data=data,
                timestamp=time.time(),
                ttl=ttl
            )
            
            cache[key] = entry
            
            # Evict LRU if cache is too full
            self._evict_lru(cache_type)
            
            logger.debug(f"💾 Cache SET: {cache_type.value}:{key} (TTL: {ttl}s)")
            
        except Exception as e:
            logger.error(f"Cache set error: {e}")
            self.stats["errors"] += 1
    
    async def get_or_fetch(self, cache_type: CacheType, symbol: str, 
                          fetch_func, params: Dict = None, prefix: str = "",
                          force_refresh: bool = False, max_age: int = None):
        """Get from cache or fetch if not available (cache-aside pattern)"""
        try:
            # Check cache first (unless force refresh)
            if not force_refresh:
                cached_data = await self.get(cache_type, symbol, params, prefix)
                if cached_data is not None:
                    # If max_age specified, check if data is fresh enough
                    if max_age:
                        key = self._generate_key(symbol, params, prefix)
                        entry = self.caches[cache_type].get(key)
                        if entry and not entry.is_fresh(max_age):
                            logger.debug(f"⏰ Cache data too old for {cache_type.value}:{key}")
                        else:
                            return cached_data
                    else:
                        return cached_data
            
            # Fetch fresh data
            logger.debug(f"🔄 Fetching fresh data: {cache_type.value}:{symbol}")
            fresh_data = await fetch_func()
            
            # Cache the fresh data
            await self.set(cache_type, symbol, fresh_data, params, prefix)
            
            return fresh_data
            
        except Exception as e:
            logger.error(f"Cache get_or_fetch error for {symbol}: {e}")
            self.stats["errors"] += 1
            # Try to return stale cache data as fallback
            return await self.get(cache_type, symbol, params, prefix)
    
    def invalidate(self, cache_type: CacheType, symbol: str = None, 
                   params: Dict = None, prefix: str = ""):
        """Invalidate cache entries"""
        try:
            cache = self.caches[cache_type]
            
            if symbol:
                # Invalidate specific symbol
                key = self._generate_key(symbol, params, prefix)
                if key in cache:
                    del cache[key]
                    logger.debug(f"🗑️ Cache invalidated: {cache_type.value}:{key}")
            else:
                # Invalidate entire cache type
                cache.clear()
                logger.info(f"🗑️ Cache cleared: {cache_type.value}")
                
        except Exception as e:
            logger.error(f"Cache invalidate error: {e}")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        total_entries = sum(len(cache) for cache in self.caches.values())
        cache_sizes = {ct.value: len(cache) for ct, cache in self.caches.items()}
        
        hit_rate = 0
        total_requests = self.stats["hits"] + self.stats["misses"]
        if total_requests > 0:
            hit_rate = self.stats["hits"] / total_requests
        
        return {
            "hit_rate": hit_rate,
            "total_entries": total_entries,
            "cache_sizes": cache_sizes,
            "stats": self.stats.copy(),
            "ttl_config": {ct.value: ttl for ct, ttl in self.ttl_config.items()}
        }
    
    def shutdown(self):
        """Shutdown cache system"""
        if self._cleanup_task:
            self._cleanup_task.cancel()
        
        # Clear all caches
        for cache in self.caches.values():
            cache.clear()
        
        logger.info("🛑 Smart API Cache shutdown completed")

# Global cache instance
smart_cache = SmartAPICache()

# Convenience functions for common cache operations
async def cache_price(symbol: str, data: Any, ttl: int = 30):
    """Cache price data with 30s TTL"""
    await smart_cache.set(CacheType.PRICE, symbol, data, custom_ttl=ttl)

async def get_cached_price(symbol: str) -> Optional[Any]:
    """Get cached price data"""
    return await smart_cache.get(CacheType.PRICE, symbol)

async def cache_ohlcv(symbol: str, timeframe: str, data: Any, ttl: int = 300):
    """Cache OHLCV data with 5min TTL"""
    params = {"timeframe": timeframe}
    await smart_cache.set(CacheType.OHLCV, symbol, data, params, custom_ttl=ttl)

async def get_cached_ohlcv(symbol: str, timeframe: str) -> Optional[Any]:
    """Get cached OHLCV data"""
    params = {"timeframe": timeframe}
    return await smart_cache.get(CacheType.OHLCV, symbol, params)

async def cache_technical_indicators(symbol: str, data: Any, ttl: int = 600):
    """Cache technical indicators with 10min TTL"""
    await smart_cache.set(CacheType.TECHNICAL, symbol, data, custom_ttl=ttl)

async def get_cached_technical_indicators(symbol: str) -> Optional[Any]:
    """Get cached technical indicators"""
    return await smart_cache.get(CacheType.TECHNICAL, symbol)

# Export main components
__all__ = [
    'SmartAPICache',
    'CacheType', 
    'smart_cache',
    'cache_price',
    'get_cached_price',
    'cache_ohlcv', 
    'get_cached_ohlcv',
    'cache_technical_indicators',
    'get_cached_technical_indicators'
]