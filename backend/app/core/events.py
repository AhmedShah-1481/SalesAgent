"""In-process pub/sub event bus that feeds the live activity SSE stream.

Real and usable from Phase 1 (there are simply no publishers yet). Pipeline nodes
will call ``event_bus.publish(...)`` from Phase 3 onward to drive the frontend feed.

``publish`` is only safe on the event-loop thread. Background threads (e.g. the
APScheduler follow-up sweep, Phase 7) must use ``publish_threadsafe``, which hops the
event onto the bound loop via ``call_soon_threadsafe``.
"""
from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator

from app.schemas.activity import ActivityEvent


class EventBus:
    def __init__(self) -> None:
        self._subscribers: list[asyncio.Queue[ActivityEvent]] = []
        self._loop: asyncio.AbstractEventLoop | None = None

    def bind_loop(self, loop: asyncio.AbstractEventLoop) -> None:
        """Remember the running loop so background threads can publish onto it."""
        self._loop = loop

    def publish(self, event: ActivityEvent) -> None:
        for q in list(self._subscribers):
            q.put_nowait(event)

    def publish_threadsafe(self, event: ActivityEvent) -> None:
        """Publish from a non-event-loop thread (e.g. APScheduler). No-op if no loop is bound."""
        loop = self._loop
        if loop is None:  # e.g. tests without a running app -> drop silently
            return
        loop.call_soon_threadsafe(self.publish, event)

    async def subscribe(self) -> AsyncIterator[ActivityEvent]:
        q: asyncio.Queue[ActivityEvent] = asyncio.Queue()
        self._subscribers.append(q)
        try:
            while True:
                yield await q.get()
        finally:
            self._subscribers.remove(q)


event_bus = EventBus()
