"""Shared data channel broadcast utilities."""

from __future__ import annotations

import json
import logging
import time
import uuid

from livekit import rtc

logger = logging.getLogger(__name__)


async def broadcast(room: rtc.Room | None, payload: dict) -> None:
    """Send a JSON message to all participants via data channel."""
    if not room or not room.local_participant:
        return
    try:
        await room.local_participant.publish_data(
            json.dumps(payload).encode("utf-8"),
            reliable=True,
        )
    except Exception as e:
        logger.warning("Failed to broadcast %s: %s", payload.get("type"), e)


async def broadcast_doc_update(room: rtc.Room | None, file: str, content: str) -> None:
    await broadcast(room, {"type": "doc_update", "file": file, "content": content})


async def broadcast_file_list(room: rtc.Room | None, files: list[dict]) -> None:
    await broadcast(room, {"type": "file_list", "files": files})


async def broadcast_file_content(
    room: rtc.Room | None, file: str, content: str, file_type: str
) -> None:
    await broadcast(room, {
        "type": "file_content",
        "file": file,
        "content": content,
        "file_type": file_type,
    })


async def broadcast_tool_call(
    room: rtc.Room | None,
    tool: str,
    args: dict,
    source: str = "agent",
) -> str:
    """Broadcast tool start and return the generated call ID."""
    call_id = uuid.uuid4().hex[:8]
    await broadcast(room, {
        "type": "tool_call",
        "tool": tool,
        "args": args,
        "id": call_id,
        "source": source,
    })
    return call_id


async def broadcast_tool_result(
    room: rtc.Room | None,
    call_id: str,
    result: str,
    start_time: float,
) -> None:
    duration_ms = int((time.monotonic() - start_time) * 1000)
    await broadcast(room, {
        "type": "tool_result",
        "id": call_id,
        "result": result[:2000],  # truncate large results
        "duration_ms": duration_ms,
    })


async def broadcast_reasoning(room: rtc.Room | None, text: str) -> None:
    await broadcast(room, {"type": "reasoning", "text": text})


async def broadcast_search_results(
    room: rtc.Room | None, query: str, results: list[dict]
) -> None:
    await broadcast(room, {"type": "search_results", "query": query, "results": results})


async def broadcast_url_content(
    room: rtc.Room | None, url: str, content: str, title: str = ""
) -> None:
    await broadcast(room, {
        "type": "url_content",
        "url": url,
        "title": title,
        "content": content,
    })


async def broadcast_present_slide(
    room: rtc.Room | None, file: str, slide_index: int
) -> None:
    await broadcast(room, {
        "type": "present_slide",
        "file": file,
        "slide_index": slide_index,
    })


async def broadcast_agent_state(
    room: rtc.Room | None, state: str
) -> None:
    await broadcast(room, {"type": "agent_state", "state": state})
