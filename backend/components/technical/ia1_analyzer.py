"""
🧠 IA1 Technical Analyzer - Refactored Technical Analysis Module
Responsible for multi-timeframe technical analysis and pattern detection
Part of Phase 2 architecture refactoring
"""

import asyncio
import logging
import time
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime

# Import shared components
from data_models import MarketOpportunity, TechnicalAnalysis, get_paris_time
from advanced_technical_indicators import AdvancedTechnicalIndicators
from optimized_market_aggregator import optimized_market_aggregator
from api_coordinator import api_coordinator
from components.events import publish_event, EventType, event_handler

logger = logging.getLogger(__name__)

class IA1TechnicalAnalyzer:
    """
    🧠 IA1 Technical Analyzer - Refactored Technical Analysis Component
    
    Responsibilities:
    - Multi-timeframe technical analysis (Daily/4H/1H)
    - 6-indicator confluence matrix analysis
    - Pattern detection and validation
    - Risk-reward calculation and filtering
    - Event-driven communication with other components
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        """Initialize IA1 Technical Analyzer"""
        
        # Default configuration
        default_config = {
            'min_risk_reward_ratio': 2.0,
            'confidence_threshold': 0.3,
            'enable_multi_timeframe': True,
            'enable_confluence_matrix': True,
            'enable_pattern_detection': True,
            'cache_analysis_results': True
        }
        
        self.config = {**default_config, **(config or {})}
        
        # Initialize components
        try:
            from server import get_ia1_chat  # Import here to avoid circular imports
            self.chat = get_ia1_chat()
        except ImportError:
            logger.warning("IA1 chat not available - running in simulation mode")
            self.chat = None
        
        self.market_aggregator = optimized_market_aggregator
        self.advanced_indicators = AdvancedTechnicalIndicators()
        self.api_coordinator = api_coordinator
        
        # Performance metrics
        self.metrics = {
            'total_analyses': 0,
            'successful_analyses': 0,
            'failed_analyses': 0,
            'escalations_to_ia2': 0,
            'avg_analysis_time': 0.0,
            'cache_hits': 0
        }
        
        # Analysis cache (temporary, until proper cache integration)
        self._analysis_cache: Dict[str, Tuple[TechnicalAnalysis, datetime]] = {}
        self._cache_ttl = 300  # 5 minutes
    
    async def analyze_opportunity(self, opportunity: MarketOpportunity) -> Optional[TechnicalAnalysis]:
        """
        🎯 Main method to analyze market opportunity
        
        Args:
            opportunity: Market opportunity to analyze
            
        Returns:
            Technical analysis result or None if analysis fails
        """
        analysis_start = time.time()
        self.metrics['total_analyses'] += 1
        
        try:
            logger.info(f"🧠 Starting IA1 analysis for {opportunity.symbol}")
            
            # Check cache first
            cached_analysis = self._get_cached_analysis(opportunity.symbol)
            if cached_analysis and self.config['cache_analysis_results']:
                self.metrics['cache_hits'] += 1
                logger.debug(f"🎯 Cache hit for IA1 analysis: {opportunity.symbol}")
                
                # Publish cache hit event
                await publish_event(
                    EventType.IA1_ANALYSIS_COMPLETED,
                    {
                        'symbol': opportunity.symbol,
                        'cached': True,
                        'analysis_time': 0.0
                    },
                    'ia1_analyzer'
                )
                
                return cached_analysis
            
            # Perform fresh analysis
            analysis = await self._perform_analysis(opportunity)
            
            if analysis:
                # Cache the result
                if self.config['cache_analysis_results']:
                    self._cache_analysis(opportunity.symbol, analysis)
                
                # Update metrics
                analysis_time = time.time() - analysis_start
                self.metrics['successful_analyses'] += 1
                self._update_avg_analysis_time(analysis_time)
                
                # Check if should escalate to IA2
                should_escalate = self._should_escalate_to_ia2(analysis)
                if should_escalate:
                    self.metrics['escalations_to_ia2'] += 1
                
                # Publish analysis completed event
                await publish_event(
                    EventType.IA1_ANALYSIS_COMPLETED,
                    {
                        'symbol': opportunity.symbol,
                        'analysis': analysis.to_dict() if hasattr(analysis, 'to_dict') else str(analysis),
                        'should_escalate': should_escalate,
                        'escalation_reason': should_escalate,
                        'analysis_time': analysis_time,
                        'cached': False
                    },
                    'ia1_analyzer'
                )
                
                logger.info(f"✅ IA1 analysis completed for {opportunity.symbol} in {analysis_time:.2f}s")
                logger.info(f"   🎯 Escalate to IA2: {'Yes' if should_escalate else 'No'}")
                
                return analysis
                
            else:
                self.metrics['failed_analyses'] += 1
                
                # Publish analysis failed event
                await publish_event(
                    EventType.IA1_ANALYSIS_FAILED,
                    {
                        'symbol': opportunity.symbol,
                        'error': 'Analysis failed',
                        'analysis_time': time.time() - analysis_start
                    },
                    'ia1_analyzer'
                )
                
                logger.warning(f"❌ IA1 analysis failed for {opportunity.symbol}")
                return None
                
        except Exception as e:
            self.metrics['failed_analyses'] += 1
            logger.error(f"❌ IA1 analysis error for {opportunity.symbol}: {e}")
            
            # Publish error event
            await publish_event(
                EventType.IA1_ANALYSIS_FAILED,
                {
                    'symbol': opportunity.symbol,
                    'error': str(e),
                    'analysis_time': time.time() - analysis_start
                },
                'ia1_analyzer'
            )
            
            return None
    
    async def _perform_analysis(self, opportunity: MarketOpportunity) -> Optional[TechnicalAnalysis]:
        """Perform the actual technical analysis"""
        try:
            # Get additional market data if needed
            symbol = opportunity.symbol
            
            # Get technical indicators
            technical_data = await self._get_technical_indicators(symbol)
            if not technical_data:
                return None
            
            # Perform multi-timeframe analysis
            timeframe_analysis = None
            if self.config['enable_multi_timeframe']:
                timeframe_analysis = await self._analyze_multi_timeframe(opportunity, technical_data)
            
            # Perform confluence matrix analysis
            confluence_analysis = None
            if self.config['enable_confluence_matrix']:
                confluence_analysis = await self._analyze_confluence_matrix(technical_data)
            
            # Calculate risk-reward ratio
            risk_reward_data = await self._calculate_risk_reward(opportunity, technical_data)
            
            # Generate final analysis
            analysis = self._compile_analysis(
                opportunity, 
                technical_data, 
                timeframe_analysis,
                confluence_analysis,
                risk_reward_data
            )
            
            return analysis
            
        except Exception as e:
            logger.error(f"Analysis performance error for {opportunity.symbol}: {e}")
            return None
    
    async def _get_technical_indicators(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Get technical indicators for symbol"""
        try:
            # Use advanced technical indicators
            indicators = await self.advanced_indicators.get_scientific_indicators(symbol)
            
            if indicators:
                return {
                    'rsi': indicators.get('rsi', 50),
                    'macd_signal': indicators.get('macd_signal', 'NEUTRAL'),
                    'bollinger_position': indicators.get('bollinger_position', 'MIDDLE'),
                    'stochastic': indicators.get('stochastic', 50),
                    'mfi': indicators.get('mfi', 50),
                    'vwap_position': indicators.get('vwap_position', 0),
                    'ema_hierarchy': indicators.get('ema_hierarchy', 'NEUTRAL'),
                    'volume_analysis': indicators.get('volume_analysis', 'NORMAL')
                }
            
            return None
            
        except Exception as e:
            logger.error(f"Technical indicators error for {symbol}: {e}")
            return None
    
    async def _analyze_multi_timeframe(self, opportunity: MarketOpportunity, technical_data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze multiple timeframes for hierarchy"""
        try:
            current_price = opportunity.current_price
            price_change_24h = opportunity.price_change_24h or 0
            volatility = opportunity.volatility or 0.05
            
            # Daily trend analysis
            daily_trend = self._analyze_daily_context(price_change_24h, volatility)
            
            # 4H trend analysis
            h4_trend = self._analyze_h4_context(technical_data, current_price)
            
            # 1H trend analysis  
            h1_trend = self._analyze_h1_context(technical_data)
            
            # Determine dominant timeframe
            daily_strength = daily_trend.get('strength', 0)
            h4_strength = h4_trend.get('strength', 0)
            h1_strength = h1_trend.get('strength', 0)
            
            if daily_strength >= 0.7:
                dominant_timeframe = "DAILY"
                decisive_pattern = daily_trend.get('pattern')
                hierarchy_confidence = daily_strength
            elif h4_strength >= 0.6:
                dominant_timeframe = "4H"
                decisive_pattern = h4_trend.get('pattern')
                hierarchy_confidence = h4_strength
            else:
                dominant_timeframe = "1H"
                decisive_pattern = h1_trend.get('pattern')
                hierarchy_confidence = h1_strength
            
            return {
                "daily_trend": daily_trend,
                "h4_trend": h4_trend,
                "h1_trend": h1_trend,
                "dominant_timeframe": dominant_timeframe,
                "decisive_pattern": decisive_pattern,
                "hierarchy_confidence": hierarchy_confidence
            }
            
        except Exception as e:
            logger.error(f"Multi-timeframe analysis error: {e}")
            return {}
    
    def _analyze_daily_context(self, price_change_24h: float, volatility: float) -> Dict[str, Any]:
        """Analyze daily context"""
        abs_change = abs(price_change_24h)
        
        if abs_change > 8.0:  # Strong daily movement
            strength = min(abs_change / 15.0, 1.0)
            direction = "BULLISH" if price_change_24h > 0 else "BEARISH"
            pattern = f"DAILY_{direction}_MOMENTUM"
        elif abs_change > 3.0:  # Moderate movement
            strength = min(abs_change / 8.0, 0.8)
            direction = "BULLISH" if price_change_24h > 0 else "BEARISH"
            pattern = f"DAILY_{direction}_TREND"
        else:  # Consolidation
            strength = 0.3
            pattern = "DAILY_CONSOLIDATION"
        
        return {
            "strength": strength,
            "pattern": pattern,
            "price_change": price_change_24h,
            "timeframe": "1D"
        }
    
    def _analyze_h4_context(self, technical_data: Dict[str, Any], current_price: float) -> Dict[str, Any]:
        """Analyze 4H context"""
        rsi = technical_data.get('rsi', 50)
        macd = technical_data.get('macd_signal', 'NEUTRAL')
        bollinger = technical_data.get('bollinger_position', 'MIDDLE')
        
        # Infer 4H trend from indicators
        bullish_signals = 0
        bearish_signals = 0
        
        if rsi < 40:
            bullish_signals += 1
        elif rsi > 60:
            bearish_signals += 1
        
        if macd == 'BULLISH':
            bullish_signals += 1
        elif macd == 'BEARISH':
            bearish_signals += 1
        
        if bollinger == 'LOWER':
            bullish_signals += 1
        elif bollinger == 'UPPER':
            bearish_signals += 1
        
        if bullish_signals > bearish_signals:
            pattern = "H4_BULLISH_SETUP"
            strength = min(bullish_signals / 3.0, 1.0)
        elif bearish_signals > bullish_signals:
            pattern = "H4_BEARISH_SETUP"
            strength = min(bearish_signals / 3.0, 1.0)
        else:
            pattern = "H4_CONSOLIDATION"
            strength = 0.4
        
        return {
            "strength": strength,
            "pattern": pattern,
            "bullish_signals": bullish_signals,
            "bearish_signals": bearish_signals,
            "timeframe": "4H"
        }
    
    def _analyze_h1_context(self, technical_data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze 1H context"""
        stochastic = technical_data.get('stochastic', 50)
        mfi = technical_data.get('mfi', 50)
        
        # Simple 1H analysis based on short-term indicators
        if stochastic < 30 and mfi < 30:
            pattern = "H1_OVERSOLD"
            strength = 0.7
        elif stochastic > 70 and mfi > 70:
            pattern = "H1_OVERBOUGHT"
            strength = 0.7
        else:
            pattern = "H1_NEUTRAL"
            strength = 0.4
        
        return {
            "strength": strength,
            "pattern": pattern,
            "stochastic": stochastic,
            "mfi": mfi,
            "timeframe": "1H"
        }
    
    async def _analyze_confluence_matrix(self, technical_data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze 6-indicator confluence matrix"""
        try:
            indicators = {
                'rsi': technical_data.get('rsi', 50),
                'macd': technical_data.get('macd_signal', 'NEUTRAL'),
                'bollinger': technical_data.get('bollinger_position', 'MIDDLE'),
                'stochastic': technical_data.get('stochastic', 50),
                'mfi': technical_data.get('mfi', 50),
                'ema_hierarchy': technical_data.get('ema_hierarchy', 'NEUTRAL')
            }
            
            # Score each indicator
            bullish_score = 0
            bearish_score = 0
            
            # RSI scoring
            if indicators['rsi'] < 40:
                bullish_score += 1
            elif indicators['rsi'] > 60:
                bearish_score += 1
            
            # MACD scoring
            if indicators['macd'] == 'BULLISH':
                bullish_score += 1
            elif indicators['macd'] == 'BEARISH':
                bearish_score += 1
            
            # Bollinger scoring
            if indicators['bollinger'] == 'LOWER':
                bullish_score += 1
            elif indicators['bollinger'] == 'UPPER':
                bearish_score += 1
            
            # Stochastic scoring
            if indicators['stochastic'] < 30:
                bullish_score += 1
            elif indicators['stochastic'] > 70:
                bearish_score += 1
            
            # MFI scoring
            if indicators['mfi'] < 30:
                bullish_score += 1
            elif indicators['mfi'] > 70:
                bearish_score += 1
            
            # EMA Hierarchy scoring
            if indicators['ema_hierarchy'] == 'BULLISH':
                bullish_score += 1
            elif indicators['ema_hierarchy'] == 'BEARISH':
                bearish_score += 1
            
            # Calculate confluence
            total_indicators = 6
            confluence_strength = abs(bullish_score - bearish_score) / total_indicators
            
            if bullish_score > bearish_score:
                confluence_direction = 'BULLISH'
            elif bearish_score > bullish_score:
                confluence_direction = 'BEARISH'
            else:
                confluence_direction = 'NEUTRAL'
            
            return {
                'bullish_score': bullish_score,
                'bearish_score': bearish_score,
                'confluence_direction': confluence_direction,
                'confluence_strength': confluence_strength,
                'indicators': indicators
            }
            
        except Exception as e:
            logger.error(f"Confluence matrix analysis error: {e}")
            return {}
    
    async def _calculate_risk_reward(self, opportunity: MarketOpportunity, technical_data: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate risk-reward ratio"""
        try:
            current_price = opportunity.current_price
            volatility = opportunity.volatility or 0.05
            
            # Simple support/resistance calculation
            atr_estimate = current_price * volatility
            
            # Support and resistance levels
            support_level = current_price - (atr_estimate * 2.0)
            resistance_level = current_price + (atr_estimate * 2.5)
            
            # Calculate RR for both directions
            long_rr = (resistance_level - current_price) / (current_price - support_level)
            short_rr = (current_price - support_level) / (resistance_level - current_price)
            
            best_rr = max(long_rr, short_rr) if long_rr > 0 and short_rr > 0 else 0
            preferred_direction = 'LONG' if long_rr > short_rr else 'SHORT'
            
            return {
                'long_rr': long_rr,
                'short_rr': short_rr,
                'best_rr': best_rr,
                'preferred_direction': preferred_direction,
                'support_level': support_level,
                'resistance_level': resistance_level,
                'current_price': current_price
            }
            
        except Exception as e:
            logger.error(f"Risk-reward calculation error: {e}")
            return {'best_rr': 0, 'preferred_direction': 'UNKNOWN'}
    
    def _compile_analysis(
        self, 
        opportunity: MarketOpportunity,
        technical_data: Dict[str, Any],
        timeframe_analysis: Optional[Dict[str, Any]],
        confluence_analysis: Optional[Dict[str, Any]],
        risk_reward_data: Dict[str, Any]
    ) -> TechnicalAnalysis:
        """Compile all analysis into final result"""
        
        # Calculate overall confidence
        confidence = 0.5  # Base confidence
        
        # Boost confidence based on confluence
        if confluence_analysis:
            confluence_boost = confluence_analysis.get('confluence_strength', 0) * 0.3
            confidence += confluence_boost
        
        # Boost confidence based on timeframe alignment
        if timeframe_analysis:
            hierarchy_boost = timeframe_analysis.get('hierarchy_confidence', 0) * 0.2
            confidence += hierarchy_boost
        
        # Ensure confidence is within bounds
        confidence = min(max(confidence, 0.0), 1.0)
        
        # Determine signal based on analysis
        signal = 'HOLD'  # Default
        
        if confluence_analysis:
            conf_direction = confluence_analysis.get('confluence_direction')
            conf_strength = confluence_analysis.get('confluence_strength', 0)
            
            if conf_direction == 'BULLISH' and conf_strength >= 0.5:
                signal = 'LONG'
            elif conf_direction == 'BEARISH' and conf_strength >= 0.5:
                signal = 'SHORT'
        
        # Create technical analysis object
        analysis = TechnicalAnalysis(
            symbol=opportunity.symbol,
            signal=signal,
            confidence=confidence,
            rsi=technical_data.get('rsi', 50),
            macd_signal=technical_data.get('macd_signal', 'NEUTRAL'),
            bollinger_position=technical_data.get('bollinger_position', 'MIDDLE'),
            support_level=risk_reward_data.get('support_level', opportunity.current_price * 0.95),
            resistance_level=risk_reward_data.get('resistance_level', opportunity.current_price * 1.05),
            risk_reward_ratio=risk_reward_data.get('best_rr', 0),
            volume_analysis=technical_data.get('volume_analysis', 'NORMAL'),
            pattern_detected=timeframe_analysis.get('decisive_pattern', 'UNKNOWN') if timeframe_analysis else 'UNKNOWN',
            reasoning=self._generate_reasoning(timeframe_analysis, confluence_analysis, risk_reward_data),
            timestamp=get_paris_time()
        )
        
        return analysis
    
    def _generate_reasoning(
        self, 
        timeframe_analysis: Optional[Dict[str, Any]],
        confluence_analysis: Optional[Dict[str, Any]], 
        risk_reward_data: Dict[str, Any]
    ) -> str:
        """Generate human-readable analysis reasoning"""
        
        reasoning_parts = []
        
        # Timeframe analysis reasoning
        if timeframe_analysis:
            dominant = timeframe_analysis.get('dominant_timeframe', 'Unknown')
            pattern = timeframe_analysis.get('decisive_pattern', 'Unknown')
            confidence = timeframe_analysis.get('hierarchy_confidence', 0)
            
            reasoning_parts.append(
                f"Multi-timeframe: {dominant} dominates with {pattern} "
                f"(confidence: {confidence:.1%})"
            )
        
        # Confluence analysis reasoning
        if confluence_analysis:
            direction = confluence_analysis.get('confluence_direction', 'NEUTRAL')
            strength = confluence_analysis.get('confluence_strength', 0)
            bullish = confluence_analysis.get('bullish_score', 0)
            bearish = confluence_analysis.get('bearish_score', 0)
            
            reasoning_parts.append(
                f"6-Indicator confluence: {direction} bias "
                f"({bullish}B vs {bearish}B, strength: {strength:.1%})"
            )
        
        # Risk-reward reasoning
        best_rr = risk_reward_data.get('best_rr', 0)
        direction = risk_reward_data.get('preferred_direction', 'UNKNOWN')
        
        reasoning_parts.append(
            f"Risk-Reward: {best_rr:.2f}:1 favoring {direction}"
        )
        
        return " | ".join(reasoning_parts)
    
    def _should_escalate_to_ia2(self, analysis: TechnicalAnalysis) -> bool:
        """Determine if analysis should be escalated to IA2"""
        
        # VOIE 1: LONG/SHORT with confidence >= 70%
        if analysis.signal in ['LONG', 'SHORT'] and analysis.confidence >= 0.7:
            return True
        
        # VOIE 2: Risk-reward >= 2.0 (any signal)
        if analysis.risk_reward_ratio >= self.config['min_risk_reward_ratio']:
            return True
        
        # VOIE 3: Exceptional confidence >= 95% (override RR)
        if analysis.signal in ['LONG', 'SHORT'] and analysis.confidence >= 0.95:
            return True
        
        return False
    
    def _get_cached_analysis(self, symbol: str) -> Optional[TechnicalAnalysis]:
        """Get cached analysis if still valid"""
        if symbol in self._analysis_cache:
            analysis, timestamp = self._analysis_cache[symbol]
            if (datetime.now() - timestamp).total_seconds() < self._cache_ttl:
                return analysis
            else:
                # Remove expired cache
                del self._analysis_cache[symbol]
        
        return None
    
    def _cache_analysis(self, symbol: str, analysis: TechnicalAnalysis):
        """Cache analysis result"""
        self._analysis_cache[symbol] = (analysis, datetime.now())
        
        # Limit cache size
        if len(self._analysis_cache) > 100:
            # Remove oldest entries
            oldest_symbol = min(self._analysis_cache.keys(), 
                              key=lambda k: self._analysis_cache[k][1])
            del self._analysis_cache[oldest_symbol]
    
    def _update_avg_analysis_time(self, new_time: float):
        """Update average analysis time"""
        if self.metrics['successful_analyses'] == 1:
            self.metrics['avg_analysis_time'] = new_time
        else:
            # Running average
            count = self.metrics['successful_analyses']
            current_avg = self.metrics['avg_analysis_time']
            self.metrics['avg_analysis_time'] = (current_avg * (count - 1) + new_time) / count
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get analyzer performance metrics"""
        success_rate = 0
        if self.metrics['total_analyses'] > 0:
            success_rate = self.metrics['successful_analyses'] / self.metrics['total_analyses']
        
        escalation_rate = 0
        if self.metrics['successful_analyses'] > 0:
            escalation_rate = self.metrics['escalations_to_ia2'] / self.metrics['successful_analyses']
        
        return {
            'analyzer_metrics': self.metrics.copy(),
            'success_rate': success_rate,
            'escalation_rate': escalation_rate,
            'cache_size': len(self._analysis_cache),
            'config': self.config.copy()
        }
    
    def update_config(self, new_config: Dict[str, Any]):
        """Update analyzer configuration"""
        self.config.update(new_config)
        logger.info(f"📝 IA1 Analyzer configuration updated: {new_config}")
    
    async def shutdown(self):
        """Cleanup analyzer resources"""
        self._analysis_cache.clear()
        logger.info("🛑 IA1 Technical Analyzer shutdown completed")

# Export main class
__all__ = ['IA1TechnicalAnalyzer']