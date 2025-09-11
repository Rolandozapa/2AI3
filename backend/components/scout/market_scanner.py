"""
🔍 Market Scanner Component - Refactored Scout Module
Responsible for detecting trading opportunities from market data
Part of Phase 2 architecture refactoring
"""

import asyncio
import logging
import time
from typing import List, Dict, Any, Optional
from datetime import datetime

# Import shared components
from data_models import MarketOpportunity
from optimized_market_aggregator import optimized_market_aggregator
from api_coordinator import api_coordinator, predictive_cache_symbols
from trending_auto_updater import trending_auto_updater
from bingx_symbol_fetcher import is_bingx_tradable

logger = logging.getLogger(__name__)

class MarketScanner:
    """
    🔍 Market Scanner - Refactored Scout Component
    
    Responsibilities:
    - Detect trading opportunities from market data
    - Filter symbols based on volume, market cap, and availability
    - Coordinate with cache system for optimal performance
    - Manage trending symbols and momentum detection
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        """Initialize Market Scanner with configuration"""
        
        # Default configuration
        default_config = {
            'max_cryptos_to_analyze': 30,
            'min_market_cap': 1_000_000,
            'min_volume_24h': 10_000,
            'min_price_change_threshold': 1.0,
            'volume_spike_multiplier': 2.0,
            'min_data_confidence': 0.7,
            'focus_trending': True,
            'auto_update_trending': True
        }
        
        # Merge with provided config
        self.config = {**default_config, **(config or {})}
        
        # Initialize components
        self.market_aggregator = optimized_market_aggregator
        self.trending_updater = trending_auto_updater
        self.api_coordinator = api_coordinator
        
        # Trending symbols configuration
        self.trending_symbols = self._get_default_trending_symbols()
        
        # Performance metrics
        self.metrics = {
            'total_scans': 0,
            'opportunities_found': 0,
            'cache_hits': 0,
            'scan_duration_avg': 0.0
        }
    
    def _get_default_trending_symbols(self) -> List[str]:
        """Get default trending symbols list"""
        return [
            # TOP 50 cryptomonnaies par market cap
            'BTC', 'ETH', 'SOL', 'BNB', 'XRP', 'ADA', 'DOGE', 'AVAX', 'DOT', 'MATIC', 
            'LINK', 'LTC', 'BCH', 'UNI', 'ATOM', 'FIL', 'APT', 'NEAR', 'VET', 'ICP',
            'HBAR', 'ALGO', 'ETC', 'MANA', 'SAND',
            # TOP 25-50 pour plus d'opportunités
            'XTZ', 'THETA', 'FTM', 'EGLD', 'AAVE', 'GRT', 'AXS', 'KLAY', 'RUNE', 'QNT',
            'CRV', 'SUSHI', 'ZEC', 'COMP', 'YFI', 'SNX', 'MKR', 'ENJ', 'BAT', 'FLOW',
            'KSM', 'ZRX', 'REN', 'LRC', '1INCH'
        ]
    
    async def initialize(self) -> bool:
        """Initialize the market scanner"""
        try:
            if self.config['auto_update_trending']:
                logger.info("🔄 Initializing trending system...")
                await self.trending_updater.start_auto_update()
                await self._sync_trending_symbols()
            
            logger.info(f"✅ Market Scanner initialized with {len(self.trending_symbols)} symbols")
            return True
            
        except Exception as e:
            logger.error(f"❌ Market Scanner initialization failed: {e}")
            return False
    
    async def _sync_trending_symbols(self):
        """Synchronize trending symbols with auto-updater"""
        try:
            current_symbols = self.trending_updater.get_current_trending_symbols()
            if current_symbols:
                self.trending_symbols = current_symbols
                logger.info(f"📈 Trending symbols updated: {len(current_symbols)} symbols")
            else:
                logger.info("📈 Using default trending symbols")
        except Exception as e:
            logger.error(f"Error syncing trending symbols: {e}")
    
    async def scan_market_opportunities(self) -> List[MarketOpportunity]:
        """
        🚀 Main method to scan for market opportunities
        """
        scan_start = time.time()
        self.metrics['total_scans'] += 1
        
        try:
            logger.info(f"🔍 Starting market scan with {len(self.trending_symbols)} symbols")
            
            # Sync trending if enabled
            if self.config['auto_update_trending']:
                await self._sync_trending_symbols()
            
            # Predictive cache warm-up
            cache_start = time.time()
            # await predictive_cache_symbols(self.trending_symbols)  # TODO: Re-enable when fixed
            cache_time = time.time() - cache_start
            
            opportunities = []
            
            if self.config['focus_trending']:
                # Scan trending and momentum opportunities
                trending_opportunities = await self._scan_trending_opportunities()
                momentum_opportunities = await self._scan_momentum_opportunities()
                
                # Combine and deduplicate
                all_opportunities = trending_opportunities + momentum_opportunities
                opportunities = self._deduplicate_opportunities(all_opportunities)
                
            else:
                # Comprehensive scan
                opportunities = await self._scan_comprehensive_opportunities()
            
            # Apply filters
            filtered_opportunities = await self._apply_filters(opportunities)
            
            # Limit results
            final_opportunities = filtered_opportunities[:self.config['max_cryptos_to_analyze']]
            
            # Update metrics
            scan_duration = time.time() - scan_start
            self.metrics['opportunities_found'] += len(final_opportunities)
            self.metrics['scan_duration_avg'] = (
                (self.metrics['scan_duration_avg'] * (self.metrics['total_scans'] - 1) + scan_duration) 
                / self.metrics['total_scans']
            )
            
            logger.info(f"🎯 Market scan completed in {scan_duration:.2f}s:")
            logger.info(f"   📊 Found {len(final_opportunities)} opportunities")
            logger.info(f"   ⚡ Cache warm-up: {cache_time:.2f}s")
            
            return final_opportunities
            
        except Exception as e:
            logger.error(f"❌ Market scan error: {e}")
            return []
    
    async def _scan_trending_opportunities(self) -> List[MarketOpportunity]:
        """Scan trending cryptocurrencies with cache optimization"""
        opportunities = []
        
        try:
            # Batch fetch trending symbols
            batch_symbols = self.trending_symbols[:25]  # Top 25 for efficiency
            
            market_data_dict = await self.market_aggregator.get_batch_market_data_optimized(
                batch_symbols, max_age=120
            )
            
            for symbol, market_data in market_data_dict.items():
                try:
                    # Check trending criteria
                    if self._meets_trending_criteria(market_data):
                        opportunity = self._convert_to_opportunity(market_data, 'trending')
                        opportunities.append(opportunity)
                        
                except Exception as e:
                    logger.warning(f"Error processing trending symbol {symbol}: {e}")
                    continue
            
            logger.debug(f"📈 Found {len(opportunities)} trending opportunities")
            
        except Exception as e:
            logger.error(f"Error in trending scan: {e}")
        
        return opportunities
    
    async def _scan_momentum_opportunities(self) -> List[MarketOpportunity]:
        """Scan high-momentum opportunities with cache coordination"""
        opportunities = []
        
        try:
            # Quick momentum screening
            momentum_candidates = []
            for symbol in self.trending_symbols:
                try:
                    current_price = await self.market_aggregator.get_price_only_optimized(
                        symbol, max_age=60
                    )
                    if current_price:
                        momentum_candidates.append(symbol)
                except Exception:
                    continue
            
            # Get full data for candidates
            if momentum_candidates:
                market_data_dict = await self.market_aggregator.get_batch_market_data_optimized(
                    momentum_candidates[:15], max_age=90
                )
                
                for symbol, market_data in market_data_dict.items():
                    try:
                        if self._meets_momentum_criteria(market_data):
                            opportunity = self._convert_to_opportunity(market_data, 'momentum')
                            opportunities.append(opportunity)
                            
                    except Exception as e:
                        logger.warning(f"Error processing momentum symbol {symbol}: {e}")
                        continue
            
            logger.debug(f"💨 Found {len(opportunities)} momentum opportunities")
            
        except Exception as e:
            logger.error(f"Error in momentum scan: {e}")
        
        return opportunities
    
    async def _scan_comprehensive_opportunities(self) -> List[MarketOpportunity]:
        """Comprehensive market scan with extended symbol list"""
        opportunities = []
        
        try:
            # Extended symbol list for comprehensive analysis
            comprehensive_symbols = self.trending_symbols + [
                'PEPE', 'SHIB', 'DOGE', 'FLOKI', 'WIF', 'BONK',  # Meme coins
                'AR', 'FET', 'OCEAN', 'AGIX', 'RLC', 'CTXC',     # AI/Web3
                'INJ', 'SEI', 'SUI', 'APTOS', 'CELO', 'ROSE'     # Layer 1
            ]
            
            unique_symbols = list(dict.fromkeys(comprehensive_symbols))[:40]
            
            market_data_dict = await self.market_aggregator.get_batch_market_data_optimized(
                unique_symbols, max_age=180
            )
            
            for symbol, market_data in market_data_dict.items():
                try:
                    if self._meets_basic_criteria(market_data):
                        opportunity = self._convert_to_opportunity(market_data, 'comprehensive')
                        opportunities.append(opportunity)
                        
                except Exception as e:
                    logger.warning(f"Error processing comprehensive symbol {symbol}: {e}")
                    continue
            
            logger.debug(f"🔍 Found {len(opportunities)} comprehensive opportunities")
            
        except Exception as e:
            logger.error(f"Error in comprehensive scan: {e}")
        
        return opportunities
    
    def _meets_trending_criteria(self, market_data) -> bool:
        """Check if market data meets trending criteria"""
        return (
            market_data.volatility > 0.05 and  # >5% volatility
            abs(market_data.price_change_24h) > self.config['min_price_change_threshold'] and
            market_data.volume_24h > 1_000_000  # Good volume
        )
    
    def _meets_momentum_criteria(self, market_data) -> bool:
        """Check if market data meets momentum criteria"""
        return (
            abs(market_data.price_change_24h) > (self.config['min_price_change_threshold'] * 2) and
            market_data.volume_24h > 5_000_000 and  # Higher volume for momentum
            0.03 < market_data.volatility < 0.15  # Sweet spot volatility
        )
    
    def _meets_basic_criteria(self, market_data) -> bool:
        """Check if market data meets basic criteria"""
        return (
            market_data.volume_24h > self.config['min_volume_24h'] and
            market_data.market_cap and 
            market_data.market_cap > self.config['min_market_cap']
        )
    
    def _convert_to_opportunity(self, market_data, scan_type: str) -> MarketOpportunity:
        """Convert market data to MarketOpportunity object"""
        # Base confidence
        confidence = 0.7
        
        # Boost confidence based on scan type
        if scan_type == 'trending':
            confidence = min(confidence + 0.15, 1.0)
        elif scan_type == 'momentum':
            confidence = min(confidence + 0.1, 1.0)
        
        return MarketOpportunity(
            symbol=market_data.symbol,
            current_price=market_data.price,
            volume_24h=market_data.volume_24h,
            price_change_24h=market_data.price_change_24h,
            volatility=market_data.volatility,
            market_cap=market_data.market_cap,
            market_cap_rank=market_data.market_cap_rank,
            data_confidence=confidence,
            source=market_data.source,
            timestamp=market_data.timestamp,
            additional_data={
                'scan_type': scan_type,
                'scanner_version': '2.0_refactored'
            }
        )
    
    def _deduplicate_opportunities(self, opportunities: List[MarketOpportunity]) -> List[MarketOpportunity]:
        """Remove duplicate opportunities by symbol"""
        seen = set()
        unique_opportunities = []
        
        for opp in opportunities:
            if opp.symbol not in seen:
                seen.add(opp.symbol)
                unique_opportunities.append(opp)
        
        return unique_opportunities
    
    async def _apply_filters(self, opportunities: List[MarketOpportunity]) -> List[MarketOpportunity]:
        """Apply trading filters to opportunities"""
        filtered = []
        stats = {'total': 0, 'bingx_passed': 0, 'bingx_rejected': 0}
        
        for opp in opportunities:
            stats['total'] += 1
            
            # BingX availability filter
            if is_bingx_tradable(opp.symbol):
                filtered.append(opp)
                stats['bingx_passed'] += 1
                logger.debug(f"✅ {opp.symbol} - BingX tradable")
            else:
                stats['bingx_rejected'] += 1
                logger.debug(f"❌ {opp.symbol} - Not BingX tradable")
        
        logger.info(f"🔧 Filtering results:")
        logger.info(f"   📊 Total: {stats['total']}")
        logger.info(f"   ✅ BingX compatible: {stats['bingx_passed']}")
        logger.info(f"   ❌ Non-BingX: {stats['bingx_rejected']}")
        
        return filtered
    
    def _sort_by_trending_score(self, opportunities: List[MarketOpportunity]) -> List[MarketOpportunity]:
        """Sort opportunities by trending score"""
        return sorted(
            opportunities, 
            key=lambda x: (
                x.data_confidence * 0.4 +
                min(abs(x.price_change_24h) / 10.0, 1.0) * 0.3 +
                min(x.volume_24h / 10_000_000, 1.0) * 0.3
            ),
            reverse=True
        )
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get scanner performance metrics"""
        return {
            'scanner_metrics': self.metrics.copy(),
            'config': self.config.copy(),
            'trending_symbols_count': len(self.trending_symbols),
            'cache_stats': self.api_coordinator.get_coordination_metrics() if self.api_coordinator else {}
        }
    
    def update_config(self, new_config: Dict[str, Any]):
        """Update scanner configuration"""
        self.config.update(new_config)
        logger.info(f"📝 Scanner configuration updated: {new_config}")
    
    async def shutdown(self):
        """Cleanup scanner resources"""
        logger.info("🛑 Market Scanner shutdown completed")

# Export main class
__all__ = ['MarketScanner']