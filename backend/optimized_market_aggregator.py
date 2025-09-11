"""
Optimized Market Aggregator with Smart Caching
Version optimisée du market aggregator avec cache intelligent intégré
pour réduire les appels API redondants et améliorer les performances
"""

import asyncio
import aiohttp
import logging
import time
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime, timezone
from dataclasses import dataclass
import pandas as pd

# Import our smart cache system
from smart_api_cache import smart_cache, CacheType
from advanced_market_aggregator import (
    MarketDataResponse, UltraRobustMarketAggregator, 
    APIEndpoint, APIStatus
)

logger = logging.getLogger(__name__)

@dataclass
class OptimizedMarketRequest:
    """Request structure for optimized market data fetching"""
    symbol: str
    max_age: int = 60  # Maximum age of cached data in seconds
    force_refresh: bool = False
    priority_sources: List[str] = None  # Preferred API sources
    fallback_enabled: bool = True

class OptimizedMarketAggregator(UltraRobustMarketAggregator):
    """
    🚀 Market Aggregator optimisé avec cache intelligent
    Hérite de UltraRobustMarketAggregator et ajoute les optimisations de cache
    """
    
    def __init__(self):
        super().__init__()
        self.cache = smart_cache
        self.batch_requests = {}  # For batching similar requests
        self.batch_delay = 0.1  # 100ms batch window
        self._request_locks = {}  # Prevent duplicate concurrent requests
        
        # Performance metrics
        self.metrics = {
            "api_calls_saved": 0,
            "cache_hits": 0,
            "batch_optimizations": 0,
            "total_requests": 0
        }
    
    async def get_comprehensive_market_data_optimized(
        self, 
        symbol: str, 
        max_age: int = 60,
        force_refresh: bool = False
    ) -> Optional[MarketDataResponse]:
        """
        🎯 Version optimisée avec cache intelligent
        """
        self.metrics["total_requests"] += 1
        
        # Normalize symbol
        symbol = symbol.upper()
        
        # Check if we already have a pending request for this symbol
        if symbol in self._request_locks and not force_refresh:
            logger.debug(f"⏳ Waiting for pending request: {symbol}")
            try:
                await self._request_locks[symbol]
                # Try to get from cache after the pending request completes
                cached_data = await self.cache.get(CacheType.MARKET_DATA, symbol)
                if cached_data:
                    return cached_data
            except Exception as e:
                logger.warning(f"Error waiting for pending request {symbol}: {e}")
        
        # Create request lock to prevent duplicate requests
        if symbol not in self._request_locks:
            self._request_locks[symbol] = asyncio.Event()
        
        try:
            # Try cache first unless force refresh
            if not force_refresh:
                # Check if we have fresh enough data
                cached_data = await self.cache.get(CacheType.MARKET_DATA, symbol)
                if cached_data:
                    # Check data age
                    data_age = time.time() - cached_data.timestamp.timestamp()
                    if data_age <= max_age:
                        self.metrics["cache_hits"] += 1
                        logger.debug(f"🎯 Cache hit for {symbol} (age: {data_age:.1f}s)")
                        return cached_data
                    else:
                        logger.debug(f"⏰ Cache data too old for {symbol} (age: {data_age:.1f}s)")
            
            # Fetch fresh data using parent class method
            logger.debug(f"🔄 Fetching fresh market data for {symbol}")
            fresh_data = await super().get_comprehensive_market_data(symbol)
            
            if fresh_data:
                # Cache the fresh data with appropriate TTL
                await self.cache.set(CacheType.MARKET_DATA, symbol, fresh_data)
                logger.debug(f"💾 Cached fresh market data for {symbol}")
                self.metrics["api_calls_saved"] += 1
                
                return fresh_data
            else:
                # If fresh fetch failed, try to return stale cache data as fallback
                logger.warning(f"⚠️ Fresh fetch failed for {symbol}, trying stale cache")
                stale_data = await self.cache.get(CacheType.MARKET_DATA, symbol)
                if stale_data:
                    logger.info(f"📤 Returning stale cache data for {symbol}")
                    return stale_data
                
                return None
                
        except Exception as e:
            logger.error(f"Error in optimized market data fetch for {symbol}: {e}")
            
            # Try stale cache as final fallback
            stale_data = await self.cache.get(CacheType.MARKET_DATA, symbol)
            if stale_data:
                logger.info(f"🆘 Emergency fallback to stale cache for {symbol}")
                return stale_data
            
            return None
            
        finally:
            # Release the request lock
            if symbol in self._request_locks:
                self._request_locks[symbol].set()
                # Clean up the lock after a delay to prevent memory leaks
                asyncio.create_task(self._cleanup_request_lock(symbol))
    
    async def _cleanup_request_lock(self, symbol: str, delay: float = 1.0):
        """Clean up request locks after a delay"""
        await asyncio.sleep(delay)
        if symbol in self._request_locks:
            del self._request_locks[symbol]
    
    async def get_batch_market_data_optimized(
        self, 
        symbols: List[str], 
        max_age: int = 60,
        batch_size: int = 10
    ) -> Dict[str, MarketDataResponse]:
        """
        🚀 Batch fetch with intelligent caching and request optimization
        """
        results = {}
        
        # Normalize symbols
        symbols = [s.upper() for s in symbols]
        
        # Separate cached vs non-cached symbols
        cached_symbols = []
        fetch_symbols = []
        
        # Check cache for each symbol
        for symbol in symbols:
            cached_data = await self.cache.get(CacheType.MARKET_DATA, symbol)
            if cached_data:
                data_age = time.time() - cached_data.timestamp.timestamp()
                if data_age <= max_age:
                    results[symbol] = cached_data
                    cached_symbols.append(symbol)
                    self.metrics["cache_hits"] += 1
                else:
                    fetch_symbols.append(symbol)
            else:
                fetch_symbols.append(symbol)
        
        logger.info(f"📊 Batch request: {len(cached_symbols)} cached, {len(fetch_symbols)} to fetch")
        
        if fetch_symbols:
            # Batch API calls for non-cached symbols
            await self._batch_fetch_symbols(fetch_symbols, results, batch_size)
            self.metrics["batch_optimizations"] += 1
        
        return results
    
    async def _batch_fetch_symbols(
        self, 
        symbols: List[str], 
        results: Dict[str, MarketDataResponse],
        batch_size: int
    ):
        """Fetch symbols in batches with rate limiting"""
        
        # Split into batches
        for i in range(0, len(symbols), batch_size):
            batch = symbols[i:i + batch_size]
            
            # Create fetch tasks for this batch
            tasks = []
            for symbol in batch:
                task = asyncio.create_task(
                    self.get_comprehensive_market_data_optimized(
                        symbol, 
                        max_age=0,  # Force fresh fetch for batch requests
                        force_refresh=True
                    )
                )
                tasks.append((symbol, task))
            
            # Wait for batch completion
            for symbol, task in tasks:
                try:
                    result = await task
                    if result:
                        results[symbol] = result
                        logger.debug(f"✅ Batch fetch successful: {symbol}")
                    else:
                        logger.warning(f"❌ Batch fetch failed: {symbol}")
                except Exception as e:
                    logger.error(f"❌ Batch fetch error for {symbol}: {e}")
            
            # Rate limiting between batches
            if i + batch_size < len(symbols):
                await asyncio.sleep(0.5)  # 500ms between batches
    
    async def get_price_only_optimized(self, symbol: str, max_age: int = 30) -> Optional[float]:
        """
        ⚡ Ultra-fast price-only fetch with aggressive caching
        Utilisé pour les prix fréquents (monitoring, stop-loss, etc.)
        """
        symbol = symbol.upper()
        
        # Try price-specific cache with shorter TTL
        cached_price = await self.cache.get(CacheType.PRICE, symbol)
        if cached_price:
            price_age = time.time() - cached_price['timestamp']
            if price_age <= max_age:
                self.metrics["cache_hits"] += 1
                return cached_price['price']
        
        # Fetch full market data (which will be cached)
        market_data = await self.get_comprehensive_market_data_optimized(
            symbol, max_age=max_age
        )
        
        if market_data:
            # Cache price specifically for fast access
            price_data = {
                'price': market_data.price,
                'timestamp': time.time()
            }
            await self.cache.set(CacheType.PRICE, symbol, price_data, custom_ttl=30)
            return market_data.price
        
        return None
    
    async def preload_trending_symbols(self, symbols: List[str]):
        """
        🔄 Preload cache for trending symbols to improve response time
        Appelé par le Scout pour préparer les données avant IA1
        """
        logger.info(f"🚀 Preloading cache for {len(symbols)} trending symbols")
        
        # Use batch fetch to load all symbols efficiently
        await self.get_batch_market_data_optimized(symbols, max_age=300)  # 5min max age
        
        logger.info(f"✅ Preload completed for trending symbols")
    
    async def invalidate_symbol_cache(self, symbol: str):
        """Invalidate all cached data for a specific symbol"""
        symbol = symbol.upper()
        
        # Invalidate all cache types for this symbol
        for cache_type in [CacheType.PRICE, CacheType.MARKET_DATA, CacheType.TECHNICAL]:
            self.cache.invalidate(cache_type, symbol)
        
        logger.info(f"🗑️ Cache invalidated for {symbol}")
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get performance metrics including cache statistics"""
        cache_stats = self.cache.get_stats()
        
        return {
            "aggregator_metrics": self.metrics.copy(),
            "cache_stats": cache_stats,
            "efficiency": {
                "cache_hit_rate": cache_stats["hit_rate"],
                "api_calls_saved": self.metrics["api_calls_saved"],
                "total_requests": self.metrics["total_requests"]
            }
        }
    
    async def shutdown(self):
        """Cleanup resources"""
        # Cancel any pending request locks
        for event in self._request_locks.values():
            event.set()
        
        self._request_locks.clear()
        
        # Close parent session
        if self.session:
            await self.session.close()
        
        logger.info("🛑 Optimized Market Aggregator shutdown completed")

# Global optimized instance
optimized_market_aggregator = OptimizedMarketAggregator()

# Convenience functions for backward compatibility
async def get_market_data_cached(symbol: str, max_age: int = 60) -> Optional[MarketDataResponse]:
    """Get market data with cache optimization"""
    return await optimized_market_aggregator.get_comprehensive_market_data_optimized(
        symbol, max_age=max_age
    )

async def get_price_cached(symbol: str, max_age: int = 30) -> Optional[float]:
    """Get price only with cache optimization"""
    return await optimized_market_aggregator.get_price_only_optimized(
        symbol, max_age=max_age
    )

async def preload_trending_cache(symbols: List[str]):
    """Preload cache for trending symbols"""
    await optimized_market_aggregator.preload_trending_symbols(symbols)

# Export components
__all__ = [
    'OptimizedMarketAggregator',
    'OptimizedMarketRequest', 
    'optimized_market_aggregator',
    'get_market_data_cached',
    'get_price_cached',
    'preload_trending_cache'
]