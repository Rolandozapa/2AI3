"""
🎭 Event System - Event-Driven Architecture Core
Implements pub/sub pattern for decoupled component communication
Part of Phase 2 architecture refactoring
"""

import asyncio
import logging
import time
from typing import Dict, Any, List, Callable, Optional, Union
from datetime import datetime
from dataclasses import dataclass, field
from enum import Enum
import json
import uuid

logger = logging.getLogger(__name__)

class EventType(Enum):
    """Event types for the trading system"""
    # Market events
    MARKET_OPPORTUNITIES_FOUND = "market.opportunities.found"
    MARKET_DATA_UPDATED = "market.data.updated"
    
    # Analysis events  
    IA1_ANALYSIS_COMPLETED = "analysis.ia1.completed"
    IA1_ANALYSIS_FAILED = "analysis.ia1.failed"
    
    # Strategy events
    IA2_DECISION_MADE = "strategy.ia2.decision"
    IA2_DECISION_FAILED = "strategy.ia2.failed"
    
    # Execution events
    TRADE_EXECUTED = "execution.trade.executed"
    TRADE_FAILED = "execution.trade.failed"
    POSITION_OPENED = "execution.position.opened"
    POSITION_CLOSED = "execution.position.closed"
    
    # System events
    CACHE_INVALIDATED = "system.cache.invalidated"
    PERFORMANCE_ALERT = "system.performance.alert"
    ERROR_OCCURRED = "system.error.occurred"

@dataclass
class Event:
    """Event data structure"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    type: EventType = None
    data: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)
    source: str = "unknown"
    priority: int = 1  # 1=high, 2=medium, 3=low
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert event to dictionary"""
        return {
            'id': self.id,
            'type': self.type.value if self.type else None,
            'data': self.data,
            'timestamp': self.timestamp.isoformat(),
            'source': self.source,
            'priority': self.priority
        }

class EventHandler:
    """Event handler wrapper"""
    def __init__(self, callback: Callable, priority: int = 1, filter_func: Optional[Callable] = None):
        self.callback = callback
        self.priority = priority
        self.filter_func = filter_func
        self.call_count = 0
        self.last_called = None
        self.error_count = 0
    
    async def handle(self, event: Event) -> bool:
        """Handle an event"""
        try:
            # Apply filter if provided
            if self.filter_func and not self.filter_func(event):
                return False
            
            # Call handler
            if asyncio.iscoroutinefunction(self.callback):
                await self.callback(event)
            else:
                self.callback(event)
            
            self.call_count += 1
            self.last_called = datetime.now()
            return True
            
        except Exception as e:
            self.error_count += 1
            logger.error(f"Event handler error: {e}")
            return False

class EventBus:
    """
    🎭 Central Event Bus - Pub/Sub System
    
    Manages event publishing and subscription for decoupled communication
    between trading system components
    """
    
    def __init__(self, max_queue_size: int = 1000):
        self._handlers: Dict[EventType, List[EventHandler]] = {}
        self._event_queue = asyncio.Queue(maxsize=max_queue_size)
        self._processing_task = None
        self._running = False
        self._stats = {
            'events_published': 0,
            'events_processed': 0,
            'events_failed': 0,
            'handlers_registered': 0
        }
        
        # Event history (limited size)
        self._event_history: List[Event] = []
        self._max_history = 1000
    
    async def start(self):
        """Start the event processing system"""
        if self._running:
            return
        
        self._running = True
        self._processing_task = asyncio.create_task(self._process_events())
        logger.info("🎭 Event Bus started")
    
    async def stop(self):
        """Stop the event processing system"""
        self._running = False
        
        if self._processing_task:
            self._processing_task.cancel()
            try:
                await self._processing_task
            except asyncio.CancelledError:
                pass
        
        logger.info("🛑 Event Bus stopped")
    
    def subscribe(
        self, 
        event_type: EventType, 
        callback: Callable,
        priority: int = 1,
        filter_func: Optional[Callable] = None
    ) -> str:
        """
        Subscribe to an event type
        
        Args:
            event_type: Type of event to subscribe to
            callback: Function to call when event occurs
            priority: Handler priority (1=high, 2=medium, 3=low)
            filter_func: Optional filter function for events
            
        Returns:
            Subscription ID for unsubscribing
        """
        if event_type not in self._handlers:
            self._handlers[event_type] = []
        
        handler = EventHandler(callback, priority, filter_func)
        self._handlers[event_type].append(handler)
        
        # Sort handlers by priority
        self._handlers[event_type].sort(key=lambda h: h.priority)
        
        self._stats['handlers_registered'] += 1
        subscription_id = f"{event_type.value}_{len(self._handlers[event_type])}"
        
        logger.debug(f"📧 Subscribed to {event_type.value} with priority {priority}")
        return subscription_id
    
    def unsubscribe(self, event_type: EventType, handler_callback: Callable):
        """Unsubscribe from an event type"""
        if event_type in self._handlers:
            self._handlers[event_type] = [
                h for h in self._handlers[event_type] 
                if h.callback != handler_callback
            ]
            logger.debug(f"📧 Unsubscribed from {event_type.value}")
    
    async def publish(
        self, 
        event_type: EventType, 
        data: Dict[str, Any] = None,
        source: str = "unknown",
        priority: int = 1
    ) -> Event:
        """
        Publish an event to the bus
        
        Args:
            event_type: Type of event
            data: Event data payload
            source: Source component name
            priority: Event priority
            
        Returns:
            Created event object
        """
        event = Event(
            type=event_type,
            data=data or {},
            source=source,
            priority=priority
        )
        
        try:
            await self._event_queue.put(event)
            self._stats['events_published'] += 1
            
            # Add to history
            self._event_history.append(event)
            if len(self._event_history) > self._max_history:
                self._event_history = self._event_history[-self._max_history:]
            
            logger.debug(f"📡 Published event: {event_type.value}")
            return event
            
        except asyncio.QueueFull:
            logger.error(f"Event queue full, dropping event: {event_type.value}")
            raise
    
    async def publish_sync(
        self,
        event_type: EventType,
        data: Dict[str, Any] = None,
        source: str = "unknown"
    ) -> List[bool]:
        """
        Publish event and wait for all handlers to complete
        
        Returns:
            List of handler success/failure results
        """
        event = Event(
            type=event_type,
            data=data or {},
            source=source
        )
        
        results = []
        if event_type in self._handlers:
            for handler in self._handlers[event_type]:
                try:
                    result = await handler.handle(event)
                    results.append(result)
                except Exception as e:
                    logger.error(f"Sync event handler error: {e}")
                    results.append(False)
        
        return results
    
    async def _process_events(self):
        """Background event processing loop"""
        logger.info("🔄 Event processing loop started")
        
        while self._running:
            try:
                # Get event from queue with timeout
                try:
                    event = await asyncio.wait_for(
                        self._event_queue.get(), 
                        timeout=1.0
                    )
                except asyncio.TimeoutError:
                    continue
                
                # Process event
                await self._handle_event(event)
                self._stats['events_processed'] += 1
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Event processing error: {e}")
                self._stats['events_failed'] += 1
                await asyncio.sleep(0.1)
    
    async def _handle_event(self, event: Event):
        """Handle a single event"""
        if event.type not in self._handlers:
            return
        
        # Create handler tasks
        tasks = []
        for handler in self._handlers[event.type]:
            task = asyncio.create_task(handler.handle(event))
            tasks.append(task)
        
        # Wait for all handlers with timeout
        if tasks:
            try:
                await asyncio.wait_for(
                    asyncio.gather(*tasks, return_exceptions=True),
                    timeout=30.0  # 30 second timeout for handlers
                )
            except asyncio.TimeoutError:
                logger.warning(f"Event handlers timeout for {event.type.value}")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get event bus statistics"""
        handler_stats = {}
        for event_type, handlers in self._handlers.items():
            handler_stats[event_type.value] = {
                'count': len(handlers),
                'total_calls': sum(h.call_count for h in handlers),
                'total_errors': sum(h.error_count for h in handlers)
            }
        
        return {
            'stats': self._stats.copy(),
            'handlers': handler_stats,
            'queue_size': self._event_queue.qsize(),
            'running': self._running,
            'recent_events_count': len(self._event_history)
        }
    
    def get_recent_events(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get recent events from history"""
        recent = self._event_history[-limit:]
        return [event.to_dict() for event in recent]

# Global event bus instance
event_bus = EventBus()

# Convenience functions
async def publish_event(event_type: EventType, data: Dict[str, Any] = None, source: str = "unknown"):
    """Publish an event (convenience function)"""
    return await event_bus.publish(event_type, data, source)

def subscribe_to_event(event_type: EventType, callback: Callable, priority: int = 1):
    """Subscribe to an event (convenience function)"""
    return event_bus.subscribe(event_type, callback, priority)

# Event decorators
def event_handler(event_type: EventType, priority: int = 1):
    """Decorator to automatically register event handlers"""
    def decorator(func):
        event_bus.subscribe(event_type, func, priority)
        return func
    return decorator

# Export main components
__all__ = [
    'EventBus',
    'Event', 
    'EventType',
    'EventHandler',
    'event_bus',
    'publish_event',
    'subscribe_to_event',
    'event_handler'
]