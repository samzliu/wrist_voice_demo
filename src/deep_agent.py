"""Anthropic SDK agentic loop for complex multi-step operations with full tool access."""

from __future__ import annotations

import asyncio
import fnmatch
import json
import logging
from pathlib import Path

import anthropic

from . import broadcast as bc

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """\
You are a capable assistant with access to file operations, web search, and slide editing. \
Complete the task thoroughly and return a concise summary of what you did."""

# ── Core file tools (always available) ─────────────────────

FILE_TOOLS = [
    {
        "name": "read_file",
        "description": "Read the contents of a file.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "File path relative to workspace."},
            },
            "required": ["path"],
        },
    },
    {
        "name": "write_file",
        "description": "Write content to a file, creating or overwriting it.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "File path relative to workspace."},
                "content": {"type": "string", "description": "The content to write."},
            },
            "required": ["path", "content"],
        },
    },
    {
        "name": "list_files",
        "description": "List files in the workspace, optionally filtered by glob pattern.",
        "input_schema": {
            "type": "object",
            "properties": {
                "glob_pattern": {
                    "type": "string",
                    "description": "Glob pattern to filter files (e.g. '*.md'). Defaults to '*'.",
                },
            },
        },
    },
    {
        "name": "search_files",
        "description": "Search for text across files in the workspace.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Text to search for (case-insensitive)."},
                "glob_pattern": {
                    "type": "string",
                    "description": "Glob pattern to filter which files to search. Defaults to '*'.",
                },
            },
            "required": ["query"],
        },
    },
]

# ── Extended tools ─────────────────────────────────────────

SEARCH_TOOLS = [
    {
        "name": "web_search",
        "description": "Search the web using Exa. Returns titles, URLs, and snippets.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search query."},
            },
            "required": ["query"],
        },
    },
    {
        "name": "visit_website",
        "description": "Fetch a URL and extract its text content.",
        "input_schema": {
            "type": "object",
            "properties": {
                "url": {"type": "string", "description": "The URL to visit."},
            },
            "required": ["url"],
        },
    },
]

SLIDE_TOOLS = [
    {
        "name": "list_slides",
        "description": "List all slides in an HTML slide deck.",
        "input_schema": {
            "type": "object",
            "properties": {
                "file": {"type": "string", "description": "Path to the HTML slide deck."},
            },
            "required": ["file"],
        },
    },
    {
        "name": "get_slide",
        "description": "Get a single slide's HTML content by index.",
        "input_schema": {
            "type": "object",
            "properties": {
                "file": {"type": "string", "description": "Path to the HTML slide deck."},
                "slide_index": {"type": "integer", "description": "0-based slide index."},
            },
            "required": ["file", "slide_index"],
        },
    },
    {
        "name": "edit_slide",
        "description": "Replace a slide's inner HTML content.",
        "input_schema": {
            "type": "object",
            "properties": {
                "file": {"type": "string", "description": "Path to the HTML slide deck."},
                "slide_index": {"type": "integer", "description": "0-based slide index."},
                "html_content": {"type": "string", "description": "New inner HTML for the slide."},
            },
            "required": ["file", "slide_index", "html_content"],
        },
    },
]

ALL_TOOLS = FILE_TOOLS + SEARCH_TOOLS + SLIDE_TOOLS

MAX_ITERATIONS = 30
TIMEOUT_SECONDS = 300


class DeepAgentBridge:
    """Bridge for the deep agent thread to communicate with the voice agent's event loop."""

    def __init__(self, room, loop: asyncio.AbstractEventLoop):
        self._room = room
        self._loop = loop

    def on_progress(self, msg: str) -> None:
        asyncio.run_coroutine_threadsafe(
            bc.broadcast_reasoning(self._room, f"[deep] {msg}"),
            self._loop,
        )

    def on_tool_call(self, name: str, args: dict) -> None:
        asyncio.run_coroutine_threadsafe(
            bc.broadcast_tool_call(self._room, name, args, source="deep"),
            self._loop,
        )


def _resolve_path(workspace: Path, rel_path: str) -> Path:
    resolved = (workspace / rel_path).resolve()
    if not str(resolved).startswith(str(workspace.resolve())):
        raise ValueError(f"Path escapes workspace: {rel_path}")
    return resolved


def _execute_tool(
    name: str, input: dict, workspace: Path, bridge: DeepAgentBridge | None = None
) -> str:
    """Execute a tool and return the result as a string."""
    if bridge:
        bridge.on_tool_call(name, input)

    # ── File tools ──
    if name == "read_file":
        path = _resolve_path(workspace, input["path"])
        if not path.exists():
            return f"Error: file not found: {input['path']}"
        return path.read_text(encoding="utf-8")

    elif name == "write_file":
        path = _resolve_path(workspace, input["path"])
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(input["content"], encoding="utf-8")
        return f"Wrote {len(input['content'])} chars to {input['path']}"

    elif name == "list_files":
        pattern = input.get("glob_pattern", "*")
        files = sorted(
            str(f.relative_to(workspace))
            for f in workspace.rglob("*")
            if f.is_file() and fnmatch.fnmatch(f.name, pattern)
        )
        return "\n".join(files) if files else "No files found."

    elif name == "search_files":
        query = input["query"].lower()
        pattern = input.get("glob_pattern", "*")
        matches: list[str] = []
        for f in sorted(workspace.rglob("*")):
            if not f.is_file() or not fnmatch.fnmatch(f.name, pattern):
                continue
            try:
                content = f.read_text(encoding="utf-8")
            except (UnicodeDecodeError, OSError):
                continue
            for i, line in enumerate(content.split("\n"), 1):
                if query in line.lower():
                    rel = str(f.relative_to(workspace))
                    matches.append(f"{rel}:{i}: {line}")
        return "\n".join(matches[:100]) if matches else "No matches found."

    # ── Search tools ──
    elif name == "web_search":
        from . import exa_tools

        results = exa_tools.web_search(input["query"])
        return json.dumps(results, indent=2)

    elif name == "visit_website":
        from . import web_tools
        import asyncio as _aio

        # Run async fetch in a new event loop since we're in a thread
        result = _aio.run(web_tools.fetch_url(input["url"]))
        return result.get("content", "Failed to fetch")

    # ── Slide tools ──
    elif name == "list_slides":
        from . import slide_ops

        path = _resolve_path(workspace, input["file"])
        if not path.exists():
            return f"File not found: {input['file']}"
        html = path.read_text(encoding="utf-8")
        summary = slide_ops.slide_summary(html)
        return json.dumps(summary, indent=2)

    elif name == "get_slide":
        from . import slide_ops

        path = _resolve_path(workspace, input["file"])
        if not path.exists():
            return f"File not found: {input['file']}"
        html = path.read_text(encoding="utf-8")
        slide = slide_ops.get_slide(html, input["slide_index"])
        return slide if slide else f"Slide {input['slide_index']} not found."

    elif name == "edit_slide":
        from . import slide_ops

        path = _resolve_path(workspace, input["file"])
        if not path.exists():
            return f"File not found: {input['file']}"
        html = path.read_text(encoding="utf-8")
        try:
            new_html = slide_ops.replace_slide(html, input["slide_index"], input["html_content"])
            path.write_text(new_html, encoding="utf-8")
            return f"Slide {input['slide_index']} updated."
        except IndexError as e:
            return str(e)

    return f"Error: unknown tool: {name}"


def _run_loop(
    task: str,
    workspace: Path,
    bridge: DeepAgentBridge | None = None,
) -> str:
    """Run the synchronous agentic loop. Called in a thread."""
    client = anthropic.Anthropic()
    messages: list[dict] = [{"role": "user", "content": task}]

    if bridge:
        bridge.on_progress(f"Starting: {task[:100]}")

    for iteration in range(MAX_ITERATIONS):
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            system=SYSTEM_PROMPT,
            tools=ALL_TOOLS,
            messages=messages,
            max_tokens=4096,
        )

        tool_uses = [b for b in response.content if b.type == "tool_use"]

        if not tool_uses:
            text_parts = [b.text for b in response.content if hasattr(b, "text")]
            result = "\n".join(text_parts) or "Done (no summary produced)."
            if bridge:
                bridge.on_progress(f"Complete: {result[:100]}")
            return result

        messages.append({"role": "assistant", "content": response.content})
        tool_results = []
        for tool_use in tool_uses:
            try:
                result = _execute_tool(tool_use.name, tool_use.input, workspace, bridge)
            except ValueError as e:
                result = f"Error: {e}"
            if bridge:
                bridge.on_progress(f"{tool_use.name} → {result[:150]}")
            tool_results.append({
                "type": "tool_result",
                "tool_use_id": tool_use.id,
                "content": result,
            })
        messages.append({"role": "user", "content": tool_results})

    return "Error: max iterations reached without completion."


async def run_deep_agent(
    task: str,
    workspace: Path,
    bridge: DeepAgentBridge | None = None,
) -> str:
    """Run the deep agent asynchronously with a timeout."""
    return await asyncio.wait_for(
        asyncio.to_thread(_run_loop, task, workspace, bridge),
        timeout=TIMEOUT_SECONDS,
    )
