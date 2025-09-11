"""
🏗️ Components Package - Refactored Trading System Architecture
Main package for all refactored trading system components
Part of Phase 2 architecture refactoring
"""

# Import refactored components
from .scout import MarketScanner
from .technical import IA1TechnicalAnalyzer
from .events import event_bus, EventType, publish_event
from .orchestrator import TradingOrchestrator, get_orchestrator, set_orchestrator

__all__ = [
    # Scout components
    'MarketScanner',
    
    # Technical analysis components
    'IA1TechnicalAnalyzer',
    
    # Event system
    'event_bus',
    'EventType', 
    'publish_event',
    
    # Orchestrator
    'TradingOrchestrator',
    'get_orchestrator',
    'set_orchestrator'
]