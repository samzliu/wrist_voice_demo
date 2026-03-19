"""Anthropic SDK agentic loop for complex multi-step file operations."""

from __future__ import annotations

import asyncio
import fnmatch
from pathlib import Path

import anthropic

SYSTEM_PROMPT = """\
You are a file editing agent. You can read, write, and search files in the \
workspace directory. Complete the task and return a summary of what you did."""

TOOLS = [
    {
        "name": "read_file",
        "description": "Read the contents of a file.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "File path relative to workspace.",
                },
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
                "path": {
                    "type": "string",
                    "description": "File path relative to workspace.",
                },
                "content": {
                    "type": "string",
                    "description": "The content to write.",
                },
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
                "query": {
                    "type": "string",
                    "description": "Text to search for (case-insensitive).",
                },
                "glob_pattern": {
                    "type": "string",
                    "description": "Glob pattern to filter which files to search. Defaults to '*'.",
                },
            },
            "required": ["query"],
        },
    },
]

MAX_ITERATIONS = 30
TIMEOUT_SECONDS = 300


def _resolve_path(workspace: Path, rel_path: str) -> Path:
    """Resolve a path relative to workspace, rejecting escapes."""
    resolved = (workspace / rel_path).resolve()
    if not str(resolved).startswith(str(workspace.resolve())):
        raise ValueError(f"Path escapes workspace: {rel_path}")
    return resolved


def _execute_tool(name: str, input: dict, workspace: Path) -> str:
    """Execute a tool and return the result as a string."""
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

    return f"Error: unknown tool: {name}"


def _run_loop(task: str, workspace: Path) -> str:
    """Run the synchronous agentic loop. Called in a thread."""
    client = anthropic.Anthropic()
    messages: list[dict] = [{"role": "user", "content": task}]

    for _ in range(MAX_ITERATIONS):
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            system=SYSTEM_PROMPT,
            tools=TOOLS,
            messages=messages,
            max_tokens=4096,
        )

        # Collect tool uses from the response
        tool_uses = [b for b in response.content if b.type == "tool_use"]

        if not tool_uses:
            # No tool calls — extract final text and return
            text_parts = [b.text for b in response.content if hasattr(b, "text")]
            return "\n".join(text_parts) or "Done (no summary produced)."

        # Execute tools and build results
        messages.append({"role": "assistant", "content": response.content})
        tool_results = []
        for tool_use in tool_uses:
            try:
                result = _execute_tool(tool_use.name, tool_use.input, workspace)
            except ValueError as e:
                result = f"Error: {e}"
            tool_results.append({
                "type": "tool_result",
                "tool_use_id": tool_use.id,
                "content": result,
            })
        messages.append({"role": "user", "content": tool_results})

    return "Error: max iterations reached without completion."


async def run_deep_agent(task: str, workspace: Path) -> str:
    """Run the deep agent asynchronously with a timeout.

    Args:
        task: Description of the task to perform.
        workspace: Path to the workspace directory.

    Returns:
        Summary of what the agent did.
    """
    return await asyncio.wait_for(
        asyncio.to_thread(_run_loop, task, workspace),
        timeout=TIMEOUT_SECONDS,
    )
