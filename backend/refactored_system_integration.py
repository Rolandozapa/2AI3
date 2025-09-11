"""
🔧 Refactored System Integration
Integration layer between refactored components and legacy server.py
Provides backward compatibility while enabling new architecture
"""

import asyncio
import logging
from typing import Dict, Any, Optional, List

# Import refactored components
from components import TradingOrchestrator, set_orchestrator, get_orchestrator
from components.events import event_bus

# Import performance monitoring
from performance_monitor import performance_monitor

logger = logging.getLogger(__name__)

class RefactoredSystemManager:
    """
    🔧 System Manager for Refactored Architecture
    
    Manages the integration between old and new system components
    Provides smooth migration path from monolithic to modular architecture
    """
    
    def __init__(self):
        self.orchestrator: Optional[TradingOrchestrator] = None
        self.legacy_mode = True  # Start in legacy mode for compatibility
        self.initialization_complete = False
        
        # Integration metrics
        self.metrics = {
            'refactored_system_active': False,
            'legacy_fallback_count': 0,
            'component_initialization_time': 0.0,
            'event_system_active': False
        }
    
    async def initialize_refactored_system(self, config: Dict[str, Any] = None) -> bool:
        """Initialize the refactored system components"""
        try:
            logger.info("🏗️ Initializing refactored trading system...")
            start_time = asyncio.get_event_loop().time()
            
            # Create and initialize orchestrator
            orchestrator_config = config.get('orchestrator', {}) if config else {}
            self.orchestrator = TradingOrchestrator(orchestrator_config)
            
            # Set global orchestrator reference
            set_orchestrator(self.orchestrator)
            
            # Initialize orchestrator
            success = await self.orchestrator.initialize()
            
            if success:
                self.initialization_complete = True
                self.metrics['refactored_system_active'] = True
                self.metrics['event_system_active'] = True
                
                initialization_time = asyncio.get_event_loop().time() - start_time
                self.metrics['component_initialization_time'] = initialization_time
                
                logger.info(f"✅ Refactored system initialized in {initialization_time:.2f}s")
                return True
            else:
                logger.error("❌ Refactored system initialization failed")
                return False
                
        except Exception as e:
            logger.error(f"❌ Refactored system initialization error: {e}")
            return False
    
    async def start_refactored_system(self) -> bool:
        """Start the refactored system (if initialized)"""
        if not self.initialization_complete:
            logger.warning("⚠️ Cannot start refactored system - not initialized")
            return False
        
        try:
            logger.info("🚀 Starting refactored trading system...")
            
            success = await self.orchestrator.start()
            
            if success:
                self.legacy_mode = False  # Switch to refactored mode
                logger.info("✅ Refactored system started successfully")
                return True
            else:
                logger.error("❌ Failed to start refactored system")
                return False
                
        except Exception as e:
            logger.error(f"❌ Refactored system start error: {e}")
            return False
    
    async def stop_refactored_system(self):
        """Stop the refactored system"""
        if self.orchestrator:
            logger.info("🛑 Stopping refactored trading system...")
            await self.orchestrator.stop()
            self.legacy_mode = True
            self.metrics['refactored_system_active'] = False
            logger.info("✅ Refactored system stopped")
    
    def is_refactored_mode_active(self) -> bool:
        """Check if refactored mode is active"""
        return (
            self.initialization_complete and 
            not self.legacy_mode and 
            self.orchestrator and 
            self.orchestrator.is_running
        )
    
    async def get_system_status(self) -> Dict[str, Any]:
        """Get comprehensive system status"""
        try:
            status = {
                'refactored_system': {
                    'active': self.is_refactored_mode_active(),
                    'initialized': self.initialization_complete,
                    'legacy_mode': self.legacy_mode,
                    'metrics': self.metrics.copy()
                }
            }
            
            # Add orchestrator status if available (avoid recursion)
            if self.orchestrator and hasattr(self.orchestrator, 'get_system_status'):
                try:
                    orchestrator_status = self.orchestrator.get_system_status()
                    status['orchestrator'] = orchestrator_status
                except Exception as e:
                    status['orchestrator'] = {'error': f'Status error: {str(e)}'}
            
            # Add event bus status (avoid recursion)
            try:
                if event_bus:
                    status['event_bus'] = event_bus.get_stats()
                else:
                    status['event_bus'] = {'status': 'not_available'}
            except Exception as e:
                status['event_bus'] = {'error': f'Event bus error: {str(e)}'}
            
            # Add performance monitoring status (avoid recursion)
            try:
                status['performance'] = performance_monitor.get_performance_summary(hours=1)
            except Exception as e:
                status['performance'] = {'error': f'Performance monitor error: {str(e)}'}
            
            return status
            
        except Exception as e:
            logger.error(f"Error in get_system_status: {e}")
            return {
                'error': f'System status error: {str(e)}',
                'refactored_system': {
                    'active': False,
                    'initialized': False,
                    'legacy_mode': True,
                    'metrics': {}
                }
            }
    
    async def manual_trading_cycle(self) -> Dict[str, Any]:
        """Manually trigger a trading cycle"""
        if not self.is_refactored_mode_active():
            return {
                'error': 'Refactored system not active',
                'legacy_mode': self.legacy_mode,
                'suggestion': 'Initialize and start refactored system first'
            }
        
        return await self.orchestrator.manual_cycle()
    
    # Legacy integration methods
    async def legacy_scout_scan(self) -> List[Any]:
        """
        Legacy scout scan integration
        Routes request to refactored scanner if active, otherwise returns empty
        """
        if self.is_refactored_mode_active():
            try:
                # Use refactored market scanner
                opportunities = await self.orchestrator.market_scanner.scan_market_opportunities()
                logger.info(f"🔄 Refactored scout scan: {len(opportunities)} opportunities")
                return opportunities
            except Exception as e:
                logger.error(f"❌ Refactored scout scan error: {e}")
                self.metrics['legacy_fallback_count'] += 1
                return []
        else:
            # Legacy mode - return empty (original system handles this)
            return []
    
    async def legacy_ia1_analysis(self, opportunity) -> Optional[Any]:
        """
        Legacy IA1 analysis integration
        Routes request to refactored analyzer if active
        """
        if self.is_refactored_mode_active():
            try:
                # Use refactored IA1 analyzer
                analysis = await self.orchestrator.ia1_analyzer.analyze_opportunity(opportunity)
                logger.debug(f"🧠 Refactored IA1 analysis for {opportunity.symbol}")
                return analysis
            except Exception as e:
                logger.error(f"❌ Refactored IA1 analysis error: {e}")
                self.metrics['legacy_fallback_count'] += 1
                return None
        else:
            # Legacy mode - return None (original system handles this)
            return None
    
    def get_integration_metrics(self) -> Dict[str, Any]:
        """Get integration-specific metrics"""
        return {
            'refactored_mode_active': self.is_refactored_mode_active(),
            'legacy_fallback_count': self.metrics['legacy_fallback_count'],
            'initialization_complete': self.initialization_complete,
            'component_init_time': self.metrics['component_initialization_time'],
            'event_system_status': event_bus.get_stats() if event_bus else None
        }

# Global system manager instance
refactored_system_manager = RefactoredSystemManager()

# Convenience functions for server.py integration
async def initialize_refactored_components(config: Dict[str, Any] = None) -> bool:
    """Initialize refactored components (called from server.py)"""
    return await refactored_system_manager.initialize_refactored_system(config)

async def start_refactored_components() -> bool:
    """Start refactored components (called from server.py)"""
    return await refactored_system_manager.start_refactored_system()

async def get_refactored_system_status() -> Dict[str, Any]:
    """Get refactored system status (called from API endpoints)"""
    return await refactored_system_manager.get_system_status()

def is_refactored_mode_active() -> bool:
    """Check if refactored mode is active"""
    return refactored_system_manager.is_refactored_mode_active()

async def refactored_scout_scan():
    """Refactored scout scan (integration point)"""
    return await refactored_system_manager.legacy_scout_scan()

async def refactored_ia1_analysis(opportunity):
    """Refactored IA1 analysis (integration point)"""
    return await refactored_system_manager.legacy_ia1_analysis(opportunity)

# Export main components
__all__ = [
    'RefactoredSystemManager',
    'refactored_system_manager',
    'initialize_refactored_components',
    'start_refactored_components', 
    'get_refactored_system_status',
    'is_refactored_mode_active',
    'refactored_scout_scan',
    'refactored_ia1_analysis'
]