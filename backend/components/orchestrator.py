"""
🎯 Trading Orchestrator - Refactored Main Coordination Component
Coordinates all trading system components using event-driven architecture
Part of Phase 2 architecture refactoring
"""

import asyncio
import logging
import time
from typing import Dict, Any, List, Optional
from datetime import datetime

# Import refactored components
from components.scout import MarketScanner
from components.technical import IA1TechnicalAnalyzer
from components.events import event_bus, publish_event, subscribe_to_event, EventType, event_handler

# Import existing components (to be refactored later)
from data_models import MarketOpportunity, TechnicalAnalysis, TradingDecision
from active_position_manager import ActivePositionManager, TradeExecutionMode

logger = logging.getLogger(__name__)

class TradingOrchestrator:
    """
    🎯 Trading Orchestrator - Event-Driven Main Coordinator
    
    Responsibilities:
    - Coordinate Market Scanner (Scout), IA1, IA2 components
    - Manage event-driven communication between components
    - Handle system lifecycle and configuration
    - Monitor overall system performance and health
    - Manage trading execution and position monitoring
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        """Initialize Trading Orchestrator"""
        
        # Default configuration
        default_config = {
            'scout_cycle_interval': 14400,  # 4 hours
            'enable_auto_trading': False,
            'enable_adaptive_mode': True,
            'max_concurrent_analyses': 10,
            'system_health_check_interval': 300,  # 5 minutes
            'performance_monitoring': True
        }
        
        self.config = {**default_config, **(config or {})}
        
        # Initialize refactored components
        self.market_scanner = MarketScanner()
        self.ia1_analyzer = IA1TechnicalAnalyzer()
        
        # Initialize existing components
        self.active_position_manager = ActivePositionManager(
            execution_mode=TradeExecutionMode.SIMULATION
        )
        
        # Legacy IA2 (to be refactored in next iteration)
        self.ia2 = None  # Will initialize from server.py temporarily
        
        # System state
        self.is_running = False
        self.cycle_count = 0
        self._initialized = False
        
        # Background tasks
        self._scout_task = None
        self._health_monitor_task = None
        
        # Performance metrics
        self.metrics = {
            'system_uptime': 0,
            'total_cycles': 0,
            'successful_cycles': 0,
            'opportunities_processed': 0,
            'trades_executed': 0,
            'system_errors': 0
        }
        
        # Event subscriptions
        self._setup_event_handlers()
    
    def _setup_event_handlers(self):
        """Setup event handlers for component communication"""
        
        # Subscribe to market events
        subscribe_to_event(
            EventType.MARKET_OPPORTUNITIES_FOUND,
            self._handle_opportunities_found,
            priority=1
        )
        
        # Subscribe to analysis events
        subscribe_to_event(
            EventType.IA1_ANALYSIS_COMPLETED,
            self._handle_ia1_analysis_completed,
            priority=1
        )
        
        subscribe_to_event(
            EventType.IA1_ANALYSIS_FAILED,
            self._handle_ia1_analysis_failed,
            priority=2
        )
        
        # Subscribe to strategy events
        subscribe_to_event(
            EventType.IA2_DECISION_MADE,
            self._handle_ia2_decision_made,
            priority=1
        )
        
        # Subscribe to system events
        subscribe_to_event(
            EventType.ERROR_OCCURRED,
            self._handle_system_error,
            priority=1
        )
    
    async def initialize(self) -> bool:
        """Initialize the trading orchestrator and all components"""
        if self._initialized:
            return True
        
        try:
            logger.info("🚀 Initializing Trading Orchestrator...")
            
            # Start event bus
            await event_bus.start()
            
            # Initialize components
            await self.market_scanner.initialize()
            
            # Initialize legacy IA2 (temporary)
            await self._initialize_legacy_components()
            
            # Initialize performance monitoring
            if self.config['performance_monitoring']:
                self._setup_performance_monitoring()
            
            self._initialized = True
            
            # Publish system initialization event
            await publish_event(
                EventType.MARKET_DATA_UPDATED,
                {'status': 'orchestrator_initialized'},
                'orchestrator'
            )
            
            logger.info("✅ Trading Orchestrator initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"❌ Orchestrator initialization failed: {e}")
            return False
    
    async def _initialize_legacy_components(self):
        """Initialize legacy components temporarily"""
        try:
            # Import IA2 from server.py (temporary until refactored)
            from server import UltraProfessionalIA2DecisionAgent
            self.ia2 = UltraProfessionalIA2DecisionAgent(self.active_position_manager)
            logger.info("✅ Legacy IA2 component initialized")
        except ImportError as e:
            logger.warning(f"⚠️ Legacy IA2 not available: {e}")
            self.ia2 = None
    
    def _setup_performance_monitoring(self):
        """Setup performance monitoring"""
        logger.info("📊 Performance monitoring enabled")
        # Additional performance monitoring setup can be added here
    
    async def start(self) -> bool:
        """Start the trading orchestrator"""
        if not self._initialized:
            if not await self.initialize():
                return False
        
        if self.is_running:
            return True
        
        try:
            logger.info("🎯 Starting Trading Orchestrator...")
            
            self.is_running = True
            self.metrics['system_uptime'] = time.time()
            
            # Start background tasks
            self._scout_task = asyncio.create_task(self._scout_cycle_loop())
            
            if self.config['system_health_check_interval'] > 0:
                self._health_monitor_task = asyncio.create_task(self._health_monitor_loop())
            
            logger.info("✅ Trading Orchestrator started successfully")
            return True
            
        except Exception as e:
            logger.error(f"❌ Orchestrator start failed: {e}")
            return False
    
    async def stop(self):
        """Stop the trading orchestrator"""
        logger.info("🛑 Stopping Trading Orchestrator...")
        
        self.is_running = False
        
        # Cancel background tasks
        if self._scout_task:
            self._scout_task.cancel()
            try:
                await self._scout_task
            except asyncio.CancelledError:
                pass
        
        if self._health_monitor_task:
            self._health_monitor_task.cancel()
            try:
                await self._health_monitor_task
            except asyncio.CancelledError:
                pass
        
        # Shutdown components
        await self.market_scanner.shutdown()
        await self.ia1_analyzer.shutdown()
        
        # Stop event bus
        await event_bus.stop()
        
        logger.info("✅ Trading Orchestrator stopped")
    
    async def _scout_cycle_loop(self):
        """Main scout cycle loop"""
        logger.info(f"🔄 Scout cycle loop started (interval: {self.config['scout_cycle_interval']}s)")
        
        while self.is_running:
            try:
                cycle_start = time.time()
                logger.info(f"🔍 Starting trading cycle #{self.cycle_count + 1}")
                
                # Execute trading cycle
                success = await self._execute_trading_cycle()
                
                # Update metrics
                self.cycle_count += 1
                self.metrics['total_cycles'] += 1
                if success:
                    self.metrics['successful_cycles'] += 1
                
                cycle_time = time.time() - cycle_start
                logger.info(f"✅ Trading cycle #{self.cycle_count} completed in {cycle_time:.2f}s")
                
                # Wait for next cycle
                await asyncio.sleep(self.config['scout_cycle_interval'])
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"❌ Scout cycle error: {e}")
                self.metrics['system_errors'] += 1
                
                # Publish error event
                await publish_event(
                    EventType.ERROR_OCCURRED,
                    {'error': str(e), 'component': 'scout_cycle'},
                    'orchestrator'
                )
                
                # Wait before retrying
                await asyncio.sleep(60)
    
    async def _execute_trading_cycle(self) -> bool:
        """Execute a complete trading cycle"""
        try:
            # Step 1: Market Scanning
            opportunities = await self.market_scanner.scan_market_opportunities()
            
            if not opportunities:
                logger.info("📊 No opportunities found in this cycle")
                return True
            
            # Publish opportunities found event
            await publish_event(
                EventType.MARKET_OPPORTUNITIES_FOUND,
                {
                    'opportunities_count': len(opportunities),
                    'symbols': [opp.symbol for opp in opportunities]
                },
                'orchestrator'
            )
            
            # Step 2: Technical Analysis (IA1)
            analyses = await self._process_opportunities_with_ia1(opportunities)
            
            # Step 3: Strategy Decisions (IA2) - for escalated analyses
            if analyses:
                await self._process_analyses_with_ia2(analyses)
            
            self.metrics['opportunities_processed'] += len(opportunities)
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Trading cycle execution error: {e}")
            return False
    
    async def _process_opportunities_with_ia1(self, opportunities: List[MarketOpportunity]) -> List[TechnicalAnalysis]:
        """Process opportunities with IA1 technical analysis"""
        analyses = []
        
        # Process opportunities concurrently (with limit)
        semaphore = asyncio.Semaphore(self.config['max_concurrent_analyses'])
        
        async def analyze_opportunity(opportunity):
            async with semaphore:
                return await self.ia1_analyzer.analyze_opportunity(opportunity)
        
        # Create analysis tasks
        analysis_tasks = [
            analyze_opportunity(opp) for opp in opportunities
        ]
        
        # Execute analyses
        results = await asyncio.gather(*analysis_tasks, return_exceptions=True)
        
        # Collect successful analyses
        for i, result in enumerate(results):
            if isinstance(result, TechnicalAnalysis):
                analyses.append(result)
            elif isinstance(result, Exception):
                logger.warning(f"IA1 analysis failed for {opportunities[i].symbol}: {result}")
        
        logger.info(f"🧠 IA1 completed {len(analyses)}/{len(opportunities)} analyses")
        
        return analyses
    
    async def _process_analyses_with_ia2(self, analyses: List[TechnicalAnalysis]):
        """Process analyses with IA2 strategy decisions"""
        if not self.ia2:
            logger.warning("⚠️ IA2 not available, skipping strategy decisions")
            return
        
        escalated_count = 0
        
        for analysis in analyses:
            try:
                # Check if should escalate to IA2 (this logic is in IA1 analyzer)
                # For now, escalate high confidence analyses
                if analysis.confidence >= 0.7 or analysis.risk_reward_ratio >= 2.0:
                    
                    # Create mock opportunity for IA2 (temporary solution)
                    mock_opportunity = MarketOpportunity(
                        symbol=analysis.symbol,
                        current_price=0,  # Will be fetched by IA2
                        volume_24h=0,
                        price_change_24h=0,
                        volatility=0.05
                    )
                    
                    # Call IA2 decision making
                    decision = await self.ia2.make_decision(mock_opportunity, analysis)
                    
                    if decision:
                        escalated_count += 1
                        
                        # Publish IA2 decision event
                        await publish_event(
                            EventType.IA2_DECISION_MADE,
                            {
                                'symbol': analysis.symbol,
                                'decision': decision.signal if hasattr(decision, 'signal') else 'UNKNOWN',
                                'confidence': decision.confidence if hasattr(decision, 'confidence') else 0
                            },
                            'orchestrator'
                        )
                
            except Exception as e:
                logger.error(f"IA2 processing error for {analysis.symbol}: {e}")
        
        logger.info(f"🎯 IA2 processed {escalated_count} escalated analyses")
    
    async def _health_monitor_loop(self):
        """System health monitoring loop"""
        logger.info(f"💓 Health monitor started (interval: {self.config['system_health_check_interval']}s)")
        
        while self.is_running:
            try:
                await self._check_system_health()
                await asyncio.sleep(self.config['system_health_check_interval'])
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Health monitor error: {e}")
                await asyncio.sleep(60)
    
    async def _check_system_health(self):
        """Check system health and publish alerts if needed"""
        try:
            # Get component metrics
            scanner_metrics = self.market_scanner.get_metrics()
            ia1_metrics = self.ia1_analyzer.get_metrics()
            
            # Check for performance issues
            alerts = []
            
            # Check IA1 success rate
            ia1_success_rate = ia1_metrics.get('success_rate', 0)
            if ia1_success_rate < 0.8:  # Less than 80% success
                alerts.append(f"IA1 success rate low: {ia1_success_rate:.1%}")
            
            # Check cache performance
            cache_stats = scanner_metrics.get('cache_stats', {})
            if isinstance(cache_stats, dict):
                coordinator_metrics = cache_stats.get('coordinator_metrics', {})
                api_calls_prevented = coordinator_metrics.get('api_calls_prevented', 0)
                if api_calls_prevented == 0:
                    alerts.append("Cache coordination not working effectively")
            
            # Publish alerts if any
            if alerts:
                await publish_event(
                    EventType.PERFORMANCE_ALERT,
                    {'alerts': alerts, 'component': 'system_health'},
                    'orchestrator'
                )
                
                for alert in alerts:
                    logger.warning(f"⚠️ Health Alert: {alert}")
            
        except Exception as e:
            logger.error(f"Health check error: {e}")
    
    # Event handlers
    async def _handle_opportunities_found(self, event):
        """Handle market opportunities found event"""
        data = event.data
        count = data.get('opportunities_count', 0)
        symbols = data.get('symbols', [])
        
        logger.info(f"📊 Event: {count} opportunities found for symbols: {symbols[:5]}...")
    
    async def _handle_ia1_analysis_completed(self, event):
        """Handle IA1 analysis completed event"""
        data = event.data
        symbol = data.get('symbol', 'Unknown')
        should_escalate = data.get('should_escalate', False)
        analysis_time = data.get('analysis_time', 0)
        
        logger.debug(f"🧠 IA1 completed for {symbol} in {analysis_time:.2f}s (escalate: {should_escalate})")
    
    async def _handle_ia1_analysis_failed(self, event):
        """Handle IA1 analysis failed event"""
        data = event.data
        symbol = data.get('symbol', 'Unknown')
        error = data.get('error', 'Unknown error')
        
        logger.warning(f"❌ IA1 failed for {symbol}: {error}")
    
    async def _handle_ia2_decision_made(self, event):
        """Handle IA2 decision made event"""
        data = event.data
        symbol = data.get('symbol', 'Unknown')
        decision = data.get('decision', 'UNKNOWN')
        confidence = data.get('confidence', 0)
        
        logger.info(f"🎯 IA2 decision for {symbol}: {decision} (confidence: {confidence:.1%})")
        
        # Update metrics
        if decision in ['LONG', 'SHORT']:
            self.metrics['trades_executed'] += 1
    
    async def _handle_system_error(self, event):
        """Handle system error event"""
        data = event.data
        error = data.get('error', 'Unknown error')
        component = data.get('component', 'Unknown')
        
        logger.error(f"🚨 System error in {component}: {error}")
        self.metrics['system_errors'] += 1
    
    # Public methods
    def get_system_status(self) -> Dict[str, Any]:
        """Get comprehensive system status"""
        uptime = time.time() - self.metrics['system_uptime'] if self.metrics['system_uptime'] > 0 else 0
        
        return {
            'orchestrator': {
                'running': self.is_running,
                'initialized': self._initialized,
                'uptime_seconds': uptime,
                'cycle_count': self.cycle_count,
                'metrics': self.metrics.copy()
            },
            'components': {
                'market_scanner': self.market_scanner.get_metrics(),
                'ia1_analyzer': self.ia1_analyzer.get_metrics(),
                'event_bus': event_bus.get_stats()
            },
            'config': self.config.copy()
        }
    
    def update_config(self, new_config: Dict[str, Any]):
        """Update orchestrator configuration"""
        self.config.update(new_config)
        logger.info(f"📝 Orchestrator configuration updated: {new_config}")
    
    async def manual_cycle(self) -> Dict[str, Any]:
        """Manually trigger a trading cycle"""
        if not self.is_running:
            return {'error': 'Orchestrator not running'}
        
        logger.info("🔄 Manual trading cycle triggered")
        
        start_time = time.time()
        success = await self._execute_trading_cycle()
        execution_time = time.time() - start_time
        
        return {
            'success': success,
            'execution_time': execution_time,
            'cycle_count': self.cycle_count
        }

# Global orchestrator instance (will be initialized in main application)
orchestrator = None

def get_orchestrator() -> Optional[TradingOrchestrator]:
    """Get global orchestrator instance"""
    return orchestrator

def set_orchestrator(new_orchestrator: TradingOrchestrator):
    """Set global orchestrator instance"""
    global orchestrator
    orchestrator = new_orchestrator

# Export main components
__all__ = [
    'TradingOrchestrator',
    'get_orchestrator',
    'set_orchestrator'
]