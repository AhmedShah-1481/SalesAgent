"""Live activity feed via Server-Sent Events (SSE).

REAL from Phase 1: subscribes to the in-process event bus and streams events to the
frontend. There are simply no publishers yet — pipeline nodes start emitting in Phase 3.
"""
from __future__ import annotations

from fastapi import APIRouter, Request
from sse_starlette.sse import EventSourceResponse

from app.core.events import event_bus

router = APIRouter(prefix="/activity", tags=["activity"])


@router.get("/stream")
async def stream(request: Request) -> EventSourceResponse:
    async def event_generator():
        async for event in event_bus.subscribe():
            if await request.is_disconnected():
                break
            yield {"event": "activity", "data": event.model_dump_json()}

    return EventSourceResponse(event_generator())
