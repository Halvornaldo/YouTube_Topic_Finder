"""API endpoints for Server-Sent Events (SSE) real-time monitoring."""

from fastapi import APIRouter, Query, Request
from fastapi.responses import StreamingResponse
from typing import List, Optional
import asyncio
import uuid
import logging
from datetime import datetime

from src.services.event_manager import (
    event_manager,
    EventType,
    Event
)

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/stream")
async def event_stream(
    request: Request,
    event_types: Optional[List[str]] = Query(
        None,
        description="Filter by event types (e.g., job_started, job_progress). Omit to receive all events."
    )
):
    """
    Server-Sent Events (SSE) endpoint for real-time monitoring.

    This endpoint establishes a persistent connection and streams events to the client
    in real-time. The client can filter events by type and will receive periodic
    heartbeats to keep the connection alive.

    Args:
        request: FastAPI request object (for disconnect detection)
        event_types: Optional list of event types to filter by

    Returns:
        StreamingResponse with SSE-formatted events

    Example:
        ```javascript
        const eventSource = new EventSource('/api/events/stream?event_types=job_started&event_types=job_progress');

        eventSource.addEventListener('job_started', (event) => {
            const data = JSON.parse(event.data);
            console.log('Job started:', data);
        });

        eventSource.addEventListener('job_progress', (event) => {
            const data = JSON.parse(event.data);
            console.log('Progress:', data.data.progress_percent);
        });
        ```
    """
    # Generate unique connection ID
    connection_id = f"sse_{uuid.uuid4().hex[:8]}_{datetime.utcnow().timestamp()}"

    # Parse event type filters
    event_type_filters = None
    if event_types:
        try:
            event_type_filters = {EventType(et) for et in event_types}
        except ValueError as e:
            logger.warning(f"Invalid event type in filter: {e}")
            event_type_filters = None

    # Register connection with event manager
    try:
        queue = event_manager.register_connection(connection_id, event_type_filters)
        logger.info(
            f"SSE connection established: {connection_id} "
            f"(filters: {[t.value for t in event_type_filters] if event_type_filters else 'none'})"
        )
    except ValueError as e:
        logger.error(f"Failed to register SSE connection: {e}")
        # Return error in SSE format
        async def error_stream():
            yield f"event: error\ndata: {{\"error\": \"{str(e)}\"}}\n\n"

        return StreamingResponse(
            error_stream(),
            media_type="text/event-stream",
            status_code=503
        )

    async def event_generator():
        """Generate SSE events from the queue."""
        try:
            # Send initial connection confirmation
            initial_event = Event(
                type=EventType.SYSTEM_STATUS,
                data={
                    'message': 'SSE connection established',
                    'connection_id': connection_id,
                    'filters': [t.value for t in event_type_filters] if event_type_filters else None,
                    'status': 'connected'
                }
            )
            yield initial_event.to_sse_format()

            # Start heartbeat task
            last_heartbeat = asyncio.get_event_loop().time()
            heartbeat_interval = 30  # seconds

            while True:
                # Check if client disconnected
                if await request.is_disconnected():
                    logger.info(f"Client disconnected: {connection_id}")
                    break

                # Send heartbeat if needed
                current_time = asyncio.get_event_loop().time()
                if current_time - last_heartbeat >= heartbeat_interval:
                    await event_manager.send_heartbeat()
                    last_heartbeat = current_time

                # Wait for events from queue (with timeout to check heartbeat/disconnect)
                try:
                    event = await asyncio.wait_for(queue.get(), timeout=5.0)
                    yield event.to_sse_format()
                except asyncio.TimeoutError:
                    # No event received, continue loop to check heartbeat/disconnect
                    continue
                except Exception as e:
                    logger.error(f"Error getting event from queue: {e}")
                    break

        except asyncio.CancelledError:
            logger.info(f"SSE stream cancelled for {connection_id}")
        except Exception as e:
            logger.error(f"Error in SSE stream for {connection_id}: {e}", exc_info=True)
        finally:
            # Unregister connection on disconnect
            event_manager.unregister_connection(connection_id)
            logger.info(f"SSE connection closed: {connection_id}")

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Disable buffering in nginx
        }
    )


@router.get("/status")
async def get_sse_status():
    """
    Get current SSE connection status and statistics.

    Returns:
        Dictionary with connection count and details
    """
    connection_info = event_manager.get_connection_info()

    return {
        "status": "operational",
        "sse_enabled": True,
        "connection_info": connection_info,
        "timestamp": datetime.utcnow().isoformat()
    }


@router.get("/event-types")
async def get_event_types():
    """
    Get list of available event types for filtering.

    Returns:
        List of event type names and descriptions
    """
    event_types_info = [
        {
            "type": EventType.JOB_STARTED.value,
            "description": "Emitted when a job starts execution",
            "example_data": {"job_id": 1, "job_type": "robot1", "niche": "ai_tech"}
        },
        {
            "type": EventType.JOB_PROGRESS.value,
            "description": "Emitted during job execution with progress updates",
            "example_data": {"job_id": 1, "progress": 50, "step": "Scraping Reddit"}
        },
        {
            "type": EventType.JOB_COMPLETED.value,
            "description": "Emitted when a job completes successfully",
            "example_data": {"job_id": 1, "result_summary": {"topics_found": 15}}
        },
        {
            "type": EventType.JOB_FAILED.value,
            "description": "Emitted when a job fails",
            "example_data": {"job_id": 1, "error": "API rate limit exceeded"}
        },
        {
            "type": EventType.JOB_CANCELLED.value,
            "description": "Emitted when a job is cancelled",
            "example_data": {"job_id": 1, "cancelled_by": "user"}
        },
        {
            "type": EventType.TOPIC_DISCOVERED.value,
            "description": "Emitted when a new topic is discovered",
            "example_data": {"topic": "AI Image Generation", "source": "reddit"}
        },
        {
            "type": EventType.VIDEO_DISCOVERED.value,
            "description": "Emitted when a new video is discovered",
            "example_data": {"video_id": "abc123", "title": "Top 10 AI Tools"}
        },
        {
            "type": EventType.ROBOT_STATUS.value,
            "description": "Emitted when robot status changes",
            "example_data": {"robot": "robot1", "status": "idle"}
        },
        {
            "type": EventType.SYSTEM_STATUS.value,
            "description": "Emitted for system-level status updates",
            "example_data": {"message": "System operational"}
        },
        {
            "type": EventType.CONFIG_CHANGED.value,
            "description": "Emitted when configuration changes",
            "example_data": {"config_type": "niche", "config_id": 5, "action": "updated"}
        },
        {
            "type": EventType.HEARTBEAT.value,
            "description": "Periodic heartbeat to keep connection alive",
            "example_data": {"message": "heartbeat"}
        }
    ]

    return {
        "event_types": event_types_info,
        "total_types": len(event_types_info)
    }
