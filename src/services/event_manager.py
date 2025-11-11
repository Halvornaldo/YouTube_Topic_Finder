"""Event Manager for real-time Server-Sent Events (SSE).

This service manages event broadcasting to connected clients for real-time updates.
"""

import asyncio
import json
import logging
from typing import Dict, Set, Any, Optional
from datetime import datetime
from dataclasses import dataclass, asdict
from enum import Enum

logger = logging.getLogger(__name__)


class EventType(str, Enum):
    """Event types for SSE."""
    JOB_STARTED = "job_started"
    JOB_PROGRESS = "job_progress"
    JOB_COMPLETED = "job_completed"
    JOB_FAILED = "job_failed"
    JOB_CANCELLED = "job_cancelled"
    TOPIC_DISCOVERED = "topic_discovered"
    VIDEO_DISCOVERED = "video_discovered"
    ROBOT_STATUS = "robot_status"
    SYSTEM_STATUS = "system_status"
    CONFIG_CHANGED = "config_changed"
    HEARTBEAT = "heartbeat"


@dataclass
class Event:
    """Event data structure."""
    type: EventType
    data: Dict[str, Any]
    timestamp: str = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.utcnow().isoformat()

    def to_sse_format(self) -> str:
        """Convert event to SSE format.

        Returns:
            SSE-formatted string
        """
        event_dict = {
            'type': self.type.value,
            'data': self.data,
            'timestamp': self.timestamp
        }

        # Format: event: <type>\ndata: <json>\n\n
        return f"event: {self.type.value}\ndata: {json.dumps(event_dict)}\n\n"


class EventManager:
    """
    Singleton event manager for SSE broadcasting.

    Manages active SSE connections and broadcasts events to subscribed clients.
    """

    _instance = None
    _initialized = False

    def __new__(cls):
        """Singleton pattern."""
        if cls._instance is None:
            cls._instance = super(EventManager, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        """Initialize the event manager."""
        if self._initialized:
            return

        self._connections: Dict[str, asyncio.Queue] = {}
        self._connection_filters: Dict[str, Set[EventType]] = {}
        self._max_connections = 100
        self._heartbeat_interval = 30  # seconds
        self._initialized = True

        logger.info("EventManager initialized")

    def register_connection(
        self,
        connection_id: str,
        event_types: Optional[Set[EventType]] = None
    ) -> asyncio.Queue:
        """Register a new SSE connection.

        Args:
            connection_id: Unique connection identifier
            event_types: Optional set of event types to filter by

        Returns:
            Queue for this connection to receive events

        Raises:
            ValueError: If max connections exceeded
        """
        if len(self._connections) >= self._max_connections:
            raise ValueError(f"Maximum connections ({self._max_connections}) exceeded")

        # Create queue for this connection
        queue = asyncio.Queue(maxsize=100)
        self._connections[connection_id] = queue

        # Set filters
        if event_types:
            self._connection_filters[connection_id] = event_types
        else:
            # No filter = receive all events
            self._connection_filters[connection_id] = set()

        logger.info(
            f"Registered SSE connection: {connection_id} "
            f"(filters: {[t.value for t in event_types] if event_types else 'none'})"
        )

        return queue

    def unregister_connection(self, connection_id: str):
        """Unregister an SSE connection.

        Args:
            connection_id: Connection identifier
        """
        if connection_id in self._connections:
            del self._connections[connection_id]

        if connection_id in self._connection_filters:
            del self._connection_filters[connection_id]

        logger.info(f"Unregistered SSE connection: {connection_id}")

    async def broadcast(
        self,
        event: Event,
        target_connections: Optional[Set[str]] = None
    ):
        """Broadcast an event to connected clients.

        Args:
            event: Event to broadcast
            target_connections: Optional set of specific connection IDs to target
        """
        if not self._connections:
            return

        # Determine which connections to send to
        connections_to_notify = self._connections.keys()
        if target_connections:
            connections_to_notify = target_connections & set(self._connections.keys())

        # Send to each connection
        for conn_id in connections_to_notify:
            # Check if connection has filters
            filters = self._connection_filters.get(conn_id, set())

            # If no filters or event type matches filter, send it
            if not filters or event.type in filters:
                try:
                    await self._connections[conn_id].put(event)
                except asyncio.QueueFull:
                    logger.warning(f"Queue full for connection {conn_id}, dropping event")
                except Exception as e:
                    logger.error(f"Error sending event to {conn_id}: {e}")

        logger.debug(f"Broadcast {event.type.value} to {len(connections_to_notify)} connections")

    async def send_heartbeat(self):
        """Send heartbeat event to all connections."""
        heartbeat = Event(
            type=EventType.HEARTBEAT,
            data={'message': 'heartbeat'}
        )
        await self.broadcast(heartbeat)

    def get_connection_count(self) -> int:
        """Get number of active connections.

        Returns:
            Number of active connections
        """
        return len(self._connections)

    def get_connection_info(self) -> Dict[str, Any]:
        """Get information about active connections.

        Returns:
            Dictionary with connection statistics
        """
        return {
            'total_connections': len(self._connections),
            'max_connections': self._max_connections,
            'connections': [
                {
                    'id': conn_id,
                    'filters': [t.value for t in self._connection_filters.get(conn_id, set())],
                    'queue_size': self._connections[conn_id].qsize()
                }
                for conn_id in self._connections
            ]
        }


# Global event manager instance
event_manager = EventManager()


# Helper functions for common events
async def broadcast_job_started(job_id: int, job_type: str, **kwargs):
    """Broadcast job started event."""
    event = Event(
        type=EventType.JOB_STARTED,
        data={'job_id': job_id, 'job_type': job_type, **kwargs}
    )
    await event_manager.broadcast(event)


async def broadcast_job_progress(job_id: int, progress: int, step: str = None, **kwargs):
    """Broadcast job progress event."""
    event = Event(
        type=EventType.JOB_PROGRESS,
        data={'job_id': job_id, 'progress': progress, 'step': step, **kwargs}
    )
    await event_manager.broadcast(event)


async def broadcast_job_completed(job_id: int, result_summary: Dict = None, **kwargs):
    """Broadcast job completed event."""
    event = Event(
        type=EventType.JOB_COMPLETED,
        data={'job_id': job_id, 'result_summary': result_summary, **kwargs}
    )
    await event_manager.broadcast(event)


async def broadcast_job_failed(job_id: int, error: str, **kwargs):
    """Broadcast job failed event."""
    event = Event(
        type=EventType.JOB_FAILED,
        data={'job_id': job_id, 'error': error, **kwargs}
    )
    await event_manager.broadcast(event)


async def broadcast_topic_discovered(topic: str, source: str, **kwargs):
    """Broadcast topic discovered event."""
    event = Event(
        type=EventType.TOPIC_DISCOVERED,
        data={'topic': topic, 'source': source, **kwargs}
    )
    await event_manager.broadcast(event)


async def broadcast_video_discovered(video_id: str, title: str, **kwargs):
    """Broadcast video discovered event."""
    event = Event(
        type=EventType.VIDEO_DISCOVERED,
        data={'video_id': video_id, 'title': title, **kwargs}
    )
    await event_manager.broadcast(event)


async def broadcast_robot_status(robot: str, status: str, **kwargs):
    """Broadcast robot status event."""
    event = Event(
        type=EventType.ROBOT_STATUS,
        data={'robot': robot, 'status': status, **kwargs}
    )
    await event_manager.broadcast(event)


async def broadcast_config_changed(config_type: str, config_id: int = None, **kwargs):
    """Broadcast configuration changed event."""
    event = Event(
        type=EventType.CONFIG_CHANGED,
        data={'config_type': config_type, 'config_id': config_id, **kwargs}
    )
    await event_manager.broadcast(event)
