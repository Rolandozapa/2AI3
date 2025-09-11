"""
🎭 Events Component Package - Event-Driven Architecture
Implements pub/sub pattern for decoupled component communication
"""

from .event_system import (
    EventBus, Event, EventType, EventHandler,
    event_bus, publish_event, subscribe_to_event, event_handler
)

__all__ = [
    'EventBus', 'Event', 'EventType', 'EventHandler',
    'event_bus', 'publish_event', 'subscribe_to_event', 'event_handler'
]