"""
API Coordinator System
Système de coordination pour éviter les appels API redondants
entre Scouter → IA1 → IA2 et optimiser le flux de données
"""

import asyncio
import logging
import time
from typing import Dict, Any, Optional, List, Set
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum
import json

from smart_api_cache import smart_cache, CacheType
from optimized_market_aggregator import optimized_market_aggregator

logger = logging.getLogger(__name__)

class DataStage(Enum):
    SCOUT = "scout"
    IA1 = "ia1" 
    IA2 = "ia2"
    EXECUTION = "execution"

@dataclass
class DataPipeline:
    """Pipeline de données pour un symbole à travers Scout → IA1 → IA2"""
    symbol: str
    current_stage: DataStage = DataStage.SCOUT
    scout_data: Optional[Any] = None
    ia1_data: Optional[Any] = None 
    ia2_data: Optional[Any] = None
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    completed_stages: Set[DataStage] = field(default_factory=set)
    
    def advance_stage(self, stage: DataStage, data: Any):
        """Advance to next stage with data"""
        self.current_stage = stage
        self.completed_stages.add(stage)
        self.updated_at = datetime.now()
        
        if stage == DataStage.SCOUT:
            self.scout_data = data
        elif stage == DataStage.IA1:
            self.ia1_data = data
        elif stage == DataStage.IA2:
            self.ia2_data = data
    
    def is_fresh(self, max_age_minutes: int = 10) -> bool:
        """Check if pipeline data is still fresh"""
        age = datetime.now() - self.updated_at
        return age.total_seconds() < (max_age_minutes * 60)

class APICoordinator:
    """
    🎯 Coordinateur central pour optimiser les appels API
    - Évite la duplication d'appels API entre composants
    - Maintient un pipeline de données Scout → IA1 → IA2
    - Prédictif caching basé sur les patterns d'utilisation
    """
    
    def __init__(self):
        self.data_pipelines: Dict[str, DataPipeline] = {}
        self.active_requests: Dict[str, asyncio.Event] = {}
        self.request_history: Dict[str, List[float]] = {}  # Request timing patterns
        self.cache = smart_cache
        self.aggregator = optimized_market_aggregator
        
        # Configuration
        self.pipeline_ttl = 600  # 10 minutes pipeline lifetime
        self.prediction_window = 300  # 5 minutes prediction window
        self.batch_window = 2.0  # 2 seconds batch collection window
        
        # Batch processing
        self.pending_requests: Dict[DataStage, Set[str]] = {
            stage: set() for stage in DataStage
        }
        self._batch_task = None
        self._start_batch_processor()
        
        # Performance metrics
        self.metrics = {
            "api_calls_prevented": 0,
            "pipeline_reuses": 0,
            "batch_optimizations": 0,
            "predictive_caches": 0
        }
    
    def _start_batch_processor(self):
        """Start background batch processor"""
        self._batch_task = asyncio.create_task(self._batch_processor_loop())
    
    async def _batch_processor_loop(self):
        """Background task to process batched requests"""
        while True:
            try:
                await asyncio.sleep(self.batch_window)
                await self._process_pending_batches()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Batch processor error: {e}")
                await asyncio.sleep(1)
    
    async def _process_pending_batches(self):
        """Process all pending batch requests"""
        for stage, symbols in self.pending_requests.items():
            if symbols:
                symbols_list = list(symbols)
                symbols.clear()
                
                if len(symbols_list) > 1:
                    self.metrics["batch_optimizations"] += 1
                    logger.info(f"🚀 Batch processing {len(symbols_list)} symbols for {stage.value}")
                
                # Process batch based on stage
                if stage == DataStage.SCOUT:
                    await self._batch_scout_data(symbols_list)
                elif stage == DataStage.IA1:
                    await self._batch_ia1_data(symbols_list)
                elif stage == DataStage.IA2:
                    await self._batch_ia2_data(symbols_list)
    
    async def request_scout_data(self, symbol: str, force_refresh: bool = False) -> Optional[Any]:
        """
        🔍 Request data for Scout stage with pipeline coordination
        """
        symbol = symbol.upper()
        
        # Check if we have fresh pipeline data
        if not force_refresh and symbol in self.data_pipelines:
            pipeline = self.data_pipelines[symbol]
            if pipeline.scout_data and pipeline.is_fresh(5):  # 5 min freshness for scout
                self.metrics["pipeline_reuses"] += 1
                logger.debug(f"🎯 Pipeline reuse for Scout: {symbol}")
                return pipeline.scout_data
        
        # Check for active request
        if symbol in self.active_requests:
            logger.debug(f"⏳ Waiting for active Scout request: {symbol}")
            await self.active_requests[symbol].wait()
            # Return pipeline data after wait
            if symbol in self.data_pipelines:
                return self.data_pipelines[symbol].scout_data
        
        # Add to batch processing
        self.pending_requests[DataStage.SCOUT].add(symbol)
        
        # For immediate requests, process directly
        if force_refresh:
            return await self._fetch_scout_data_direct(symbol)
        
        # Wait for batch processing
        await asyncio.sleep(self.batch_window + 0.1)
        
        # Return data from pipeline
        if symbol in self.data_pipelines:
            return self.data_pipelines[symbol].scout_data
        
        return None
    
    async def request_ia1_data(self, symbol: str, scout_data: Any = None) -> Optional[Any]:
        """
        🧠 Request data for IA1 stage with Scout data reuse
        """
        symbol = symbol.upper()
        
        # Create or update pipeline
        if symbol not in self.data_pipelines:
            self.data_pipelines[symbol] = DataPipeline(symbol)
        
        pipeline = self.data_pipelines[symbol]
        
        # Use scout data if provided, otherwise get from pipeline
        if scout_data:
            pipeline.advance_stage(DataStage.SCOUT, scout_data)
        elif not pipeline.scout_data:
            # Need scout data first
            scout_data = await self.request_scout_data(symbol)
            if scout_data:
                pipeline.advance_stage(DataStage.SCOUT, scout_data)
        
        # Check if we have fresh IA1 data
        if pipeline.ia1_data and pipeline.is_fresh(8):  # 8 min freshness for IA1
            self.metrics["pipeline_reuses"] += 1
            logger.debug(f"🎯 Pipeline reuse for IA1: {symbol}")
            return pipeline.ia1_data
        
        # Add to batch processing
        self.pending_requests[DataStage.IA1].add(symbol)
        
        # Wait for batch processing
        await asyncio.sleep(self.batch_window + 0.1)
        
        return pipeline.ia1_data
    
    async def request_ia2_data(self, symbol: str, ia1_data: Any = None) -> Optional[Any]:
        """
        🎯 Request data for IA2 stage with IA1 data reuse
        """
        symbol = symbol.upper()
        
        # Get or create pipeline
        if symbol not in self.data_pipelines:
            self.data_pipelines[symbol] = DataPipeline(symbol)
        
        pipeline = self.data_pipelines[symbol]
        
        # Use IA1 data if provided
        if ia1_data:
            pipeline.advance_stage(DataStage.IA1, ia1_data)
        elif not pipeline.ia1_data:
            # Need IA1 data first
            ia1_data = await self.request_ia1_data(symbol)
            if ia1_data:
                pipeline.advance_stage(DataStage.IA1, ia1_data)
        
        # Check if we have fresh IA2 data
        if pipeline.ia2_data and pipeline.is_fresh(10):  # 10 min freshness for IA2
            self.metrics["pipeline_reuses"] += 1
            logger.debug(f"🎯 Pipeline reuse for IA2: {symbol}")
            return pipeline.ia2_data
        
        # Add to batch processing
        self.pending_requests[DataStage.IA2].add(symbol)
        
        # Wait for batch processing
        await asyncio.sleep(self.batch_window + 0.1)
        
        return pipeline.ia2_data
    
    async def _batch_scout_data(self, symbols: List[str]):
        """Batch fetch scout data"""
        try:
            # Use optimized market aggregator for batch fetching
            results = await self.aggregator.get_batch_market_data_optimized(symbols)
            
            for symbol, market_data in results.items():
                if symbol not in self.data_pipelines:
                    self.data_pipelines[symbol] = DataPipeline(symbol)
                
                # Convert to scout data format
                scout_data = {
                    'symbol': symbol,
                    'current_price': market_data.price,
                    'volume_24h': market_data.volume_24h,
                    'price_change_24h': market_data.price_change_24h,
                    'volatility': market_data.volatility,
                    'market_cap': market_data.market_cap,
                    'source': market_data.source,
                    'timestamp': market_data.timestamp
                }
                
                self.data_pipelines[symbol].advance_stage(DataStage.SCOUT, scout_data)
                logger.debug(f"📊 Scout data cached for {symbol}")
        
        except Exception as e:
            logger.error(f"Error in batch scout data fetch: {e}")
    
    async def _batch_ia1_data(self, symbols: List[str]):
        """Batch process IA1 analysis"""
        # IA1 analysis typically needs to be done individually due to complexity
        # But we can optimize by ensuring all required market data is cached
        
        # Preload technical indicators for all symbols
        await self._preload_technical_data(symbols)
        
        for symbol in symbols:
            try:
                # This would trigger IA1 analysis with cached data
                # The actual IA1 analysis happens in the main system
                logger.debug(f"🧠 IA1 data request queued for {symbol}")
            except Exception as e:
                logger.error(f"Error processing IA1 for {symbol}: {e}")
    
    async def _batch_ia2_data(self, symbols: List[str]):
        """Batch process IA2 decisions"""
        # Similar to IA1, IA2 is complex but we can optimize data preparation
        for symbol in symbols:
            try:
                logger.debug(f"🎯 IA2 data request queued for {symbol}")
            except Exception as e:
                logger.error(f"Error processing IA2 for {symbol}: {e}")
    
    async def _fetch_scout_data_direct(self, symbol: str) -> Optional[Any]:
        """Direct fetch for urgent scout data requests"""
        try:
            market_data = await self.aggregator.get_comprehensive_market_data_optimized(
                symbol, force_refresh=True
            )
            
            if market_data:
                scout_data = {
                    'symbol': symbol,
                    'current_price': market_data.price,
                    'volume_24h': market_data.volume_24h,
                    'price_change_24h': market_data.price_change_24h,
                    'volatility': market_data.volatility,
                    'market_cap': market_data.market_cap,
                    'source': market_data.source,
                    'timestamp': market_data.timestamp
                }
                
                # Update pipeline
                if symbol not in self.data_pipelines:
                    self.data_pipelines[symbol] = DataPipeline(symbol)
                self.data_pipelines[symbol].advance_stage(DataStage.SCOUT, scout_data)
                
                return scout_data
        
        except Exception as e:
            logger.error(f"Error in direct scout data fetch for {symbol}: {e}")
        
        return None
    
    async def _preload_technical_data(self, symbols: List[str]):
        """Preload technical indicators for symbols"""
        try:
            # Cache OHLCV data for technical analysis
            for symbol in symbols:
                # Check if we need to cache OHLCV data
                cached_ohlcv = await self.cache.get(CacheType.OHLCV, symbol, {"timeframe": "1d"})
                if not cached_ohlcv:
                    # This would fetch OHLCV data - integrate with your OHLCV fetcher
                    logger.debug(f"📈 Preloading OHLCV for {symbol}")
        except Exception as e:
            logger.error(f"Error preloading technical data: {e}")
    
    async def predict_and_cache(self, symbols: List[str]):
        """
        🔮 Predictive caching based on usage patterns
        Called by Scout to prepare data before IA1 analysis
        """
        logger.info(f"🔮 Predictive caching for {len(symbols)} symbols")
        
        # Preload market data
        await self.aggregator.preload_trending_symbols(symbols)
        
        # Preload technical data
        await self._preload_technical_data(symbols)
        
        self.metrics["predictive_caches"] += len(symbols)
        logger.info(f"✅ Predictive caching completed")
    
    def cleanup_old_pipelines(self, max_age_minutes: int = 30):
        """Clean up old pipeline data"""
        cutoff_time = datetime.now() - timedelta(minutes=max_age_minutes)
        old_symbols = []
        
        for symbol, pipeline in self.data_pipelines.items():
            if pipeline.updated_at < cutoff_time:
                old_symbols.append(symbol)
        
        for symbol in old_symbols:
            del self.data_pipelines[symbol]
        
        if old_symbols:
            logger.info(f"🧹 Cleaned up {len(old_symbols)} old pipelines")
    
    def get_pipeline_status(self, symbol: str) -> Dict[str, Any]:
        """Get current pipeline status for a symbol"""
        if symbol not in self.data_pipelines:
            return {"status": "not_found"}
        
        pipeline = self.data_pipelines[symbol]
        return {
            "symbol": symbol,
            "current_stage": pipeline.current_stage.value,
            "completed_stages": [stage.value for stage in pipeline.completed_stages],
            "created_at": pipeline.created_at.isoformat(),
            "updated_at": pipeline.updated_at.isoformat(),
            "is_fresh": pipeline.is_fresh(),
            "has_scout_data": pipeline.scout_data is not None,
            "has_ia1_data": pipeline.ia1_data is not None,
            "has_ia2_data": pipeline.ia2_data is not None
        }
    
    def get_coordination_metrics(self) -> Dict[str, Any]:
        """Get coordination performance metrics"""
        active_pipelines = len(self.data_pipelines)
        
        return {
            "coordinator_metrics": self.metrics.copy(),
            "active_pipelines": active_pipelines,
            "pending_batches": {
                stage.value: len(symbols) for stage, symbols in self.pending_requests.items()
            },
            "aggregator_metrics": self.aggregator.get_performance_metrics()
        }
    
    async def shutdown(self):
        """Shutdown coordinator"""
        if self._batch_task:
            self._batch_task.cancel()
            try:
                await self._batch_task
            except asyncio.CancelledError:
                pass
        
        # Clear data
        self.data_pipelines.clear()
        self.active_requests.clear()
        
        logger.info("🛑 API Coordinator shutdown completed")

# Global coordinator instance
api_coordinator = APICoordinator()

# Convenience functions
async def get_scout_data_coordinated(symbol: str, force_refresh: bool = False):
    """Get scout data with coordination"""
    return await api_coordinator.request_scout_data(symbol, force_refresh)

async def get_ia1_data_coordinated(symbol: str, scout_data: Any = None):
    """Get IA1 data with coordination"""
    return await api_coordinator.request_ia1_data(symbol, scout_data)

async def get_ia2_data_coordinated(symbol: str, ia1_data: Any = None):
    """Get IA2 data with coordination"""
    return await api_coordinator.request_ia2_data(symbol, ia1_data)

async def predictive_cache_symbols(symbols: List[str]):
    """Predictive cache for symbols"""
    await api_coordinator.predict_and_cache(symbols)

# Export components
__all__ = [
    'APICoordinator',
    'DataPipeline', 
    'DataStage',
    'api_coordinator',
    'get_scout_data_coordinated',
    'get_ia1_data_coordinated', 
    'get_ia2_data_coordinated',
    'predictive_cache_symbols'
]