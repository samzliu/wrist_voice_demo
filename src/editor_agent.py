"""MarkdownEditorAgent with function tools for voice-controlled editing."""

from __future__ import annotations

import asyncio
import json
import logging
from pathlib import Path

from livekit import rtc
from livekit.agents import function_tool, Agent, RunContext

from . import markdown_ops
from .deep_agent import run_deep_agent

logger = logging.getLogger(__name__)


SYSTEM_PROMPT = """\
You are a collaborative writing and editing assistant. You work alongside the user \
in real time — they can see the document you're editing live on their screen. \
Think of yourself as a coworker sitting next to them, talking through ideas and \
making edits together.

## What you can do
- Create, read, and edit markdown files in the workspace.
- Help with any kind of writing: notes, blog posts, specs, plans, brainstorms, \
documentation, outlines, meeting notes, lists — whatever the user needs.
- Structure and reorganize content, fix prose, expand ideas, or trim things down.

## How to work
- Start by asking what the user wants to work on. Keep it casual and conversational.
- When the user describes something, start editing right away. Don't wait for \
perfect instructions — draft something and iterate. It's easier to react to \
something concrete than to plan in the abstract.
- After each edit, briefly say what you changed. The user can see the document \
updating live, so keep explanations short.
- If the user edits the document directly (you'll see their changes), acknowledge \
and build on their work rather than overwriting it.
- One question at a time. Let the user talk.

## Rules
- Be concise and natural. Short sentences. No corporate jargon.
- Do not use markdown formatting in your speech — speak naturally since the user \
is interacting by voice.
- When reading back content, summarize rather than reading verbatim. Only read \
the full text if the user asks.
- File paths are relative to the workspace directory. The user can refer to files \
by name without the .md extension.
- For complex multi-step tasks (restructuring documents, batch edits, or creating \
multiple related files), use the deep_think tool to delegate to a more capable agent.
"""


class MarkdownEditorAgent(Agent):
    def __init__(self, workspace_dir: str) -> None:
        super().__init__(
            instructions=SYSTEM_PROMPT,
        )
        self._workspace = Path(workspace_dir).resolve()
        self._backups: dict[str, str] = {}  # path -> previous content
        self._room: rtc.Room | None = None
        self._current_file: str | None = None  # currently active file (relative)

    def set_room(self, room: rtc.Room) -> None:
        """Set the LiveKit room for data channel communication."""
        self._room = room
        room.on("data_received", self._on_data_received)

    def _on_data_received(
        self,
        data: rtc.DataPacket,
    ) -> None:
        """Handle incoming data messages from the web client."""
        try:
            payload = data.data
            msg = json.loads(payload.decode("utf-8"))
            if msg.get("type") == "human_edit" and msg.get("content") is not None:
                file_name = msg.get("file") or self._current_file
                if file_name:
                    path = self._resolve_path(file_name)
                    self._backup_file(path)
                    path.write_text(msg["content"], encoding="utf-8")
                    logger.info("Received human edit for %s", file_name)
        except Exception as e:
            logger.warning("Error handling data message: %s", e)

    async def _broadcast_doc(self, file_path: str, content: str) -> None:
        """Send document content to connected web clients via data channel."""
        if not self._room or not self._room.local_participant:
            return
        self._current_file = file_path
        msg = json.dumps({"type": "doc_update", "file": file_path, "content": content})
        try:
            await self._room.local_participant.publish_data(
                msg.encode("utf-8"),
                reliable=True,
            )
        except Exception as e:
            logger.warning("Failed to broadcast doc update: %s", e)

    def _resolve_path(self, file_path: str) -> Path:
        """Resolve a path relative to workspace, rejecting escapes."""
        if not file_path.endswith(".md"):
            file_path = file_path + ".md"
        resolved = (self._workspace / file_path).resolve()
        if not str(resolved).startswith(str(self._workspace)):
            raise ValueError(f"Path escapes workspace: {file_path}")
        return resolved

    def _backup_file(self, path: Path) -> None:
        """Store a single-level backup for undo."""
        if path.exists():
            self._backups[str(path)] = path.read_text(encoding="utf-8")

    # ── Reading tools ──────────────────────────────────────────────

    @function_tool()
    async def list_files(self, context: RunContext) -> str:
        """List all markdown files in the workspace directory."""
        files = sorted(self._workspace.rglob("*.md"))
        if not files:
            return "No markdown files found in workspace."
        relative = [str(f.relative_to(self._workspace)) for f in files]
        return "\n".join(relative)

    @function_tool()
    async def read_file(self, context: RunContext, file_path: str) -> str:
        """Read the entire contents of a markdown file.

        Args:
            file_path: Path to the file relative to workspace.
        """
        path = self._resolve_path(file_path)
        if not path.exists():
            return f"File not found: {file_path}"
        content = path.read_text(encoding="utf-8")
        await self._broadcast_doc(file_path, content)
        return content

    @function_tool()
    async def read_section(self, context: RunContext, file_path: str, heading: str) -> str:
        """Read a specific section of a markdown file by its heading.

        Args:
            file_path: Path to the file relative to workspace.
            heading: The heading text to search for (case-insensitive substring match).
        """
        path = self._resolve_path(file_path)
        if not path.exists():
            return f"File not found: {file_path}"
        content = path.read_text(encoding="utf-8")
        matches = markdown_ops.find_section(content, heading)
        if not matches:
            return f"No section matching '{heading}' found."
        if len(matches) > 1:
            names = [f"- {s.heading} (line {s.start_line})" for s in matches]
            return "Multiple matches:\n" + "\n".join(names)
        s = matches[0]
        return f"## {s.heading} (lines {s.start_line}-{s.end_line})\n{s.body}"

    @function_tool()
    async def get_file_outline(self, context: RunContext, file_path: str) -> str:
        """Return the heading structure of a markdown file with line numbers.

        Args:
            file_path: Path to the file relative to workspace.
        """
        path = self._resolve_path(file_path)
        if not path.exists():
            return f"File not found: {file_path}"
        content = path.read_text(encoding="utf-8")
        outline = markdown_ops.get_outline(content)
        if not outline:
            return "No headings found."
        lines = []
        for line_num, level, text in outline:
            indent = "  " * (level - 1)
            lines.append(f"{indent}Line {line_num}: {'#' * level} {text}")
        return "\n".join(lines)

    @function_tool()
    async def search_in_file(self, context: RunContext, file_path: str, query: str) -> str:
        """Search for text in a file and return matching lines with line numbers.

        Args:
            file_path: Path to the file relative to workspace.
            query: Text to search for (case-insensitive).
        """
        path = self._resolve_path(file_path)
        if not path.exists():
            return f"File not found: {file_path}"
        content = path.read_text(encoding="utf-8")
        query_lower = query.lower()
        matches = []
        for i, line in enumerate(content.split("\n"), 1):
            if query_lower in line.lower():
                matches.append(f"Line {i}: {line}")
        if not matches:
            return f"No matches for '{query}'."
        return "\n".join(matches)

    # ── Editing tools ──────────────────────────────────────────────

    @function_tool()
    async def replace_section(
        self, context: RunContext, file_path: str, heading: str, new_content: str
    ) -> str:
        """Replace the body of a section (identified by heading) with new content.

        Args:
            file_path: Path to the file relative to workspace.
            heading: The heading text to search for.
            new_content: The new body text for the section.
        """
        path = self._resolve_path(file_path)
        if not path.exists():
            return f"File not found: {file_path}"
        content = path.read_text(encoding="utf-8")
        matches = markdown_ops.find_section(content, heading)
        if not matches:
            return f"No section matching '{heading}' found."
        if len(matches) > 1:
            names = [f"- {s.heading} (line {s.start_line})" for s in matches]
            return "Multiple matches, be more specific:\n" + "\n".join(names)
        self._backup_file(path)
        new = markdown_ops.replace_section_content(content, matches[0], new_content)
        path.write_text(new, encoding="utf-8")
        await self._broadcast_doc(file_path, new)
        return f"Replaced section '{matches[0].heading}'. New content:\n{new_content}"

    @function_tool()
    async def find_and_replace(
        self,
        context: RunContext,
        file_path: str,
        find_text: str,
        replace_text: str,
        occurrence: int = 0,
    ) -> str:
        """Find and replace text in a file.

        Args:
            file_path: Path to the file relative to workspace.
            find_text: The text to find.
            replace_text: The replacement text.
            occurrence: Which occurrence to replace (1-indexed). 0 means all.
        """
        path = self._resolve_path(file_path)
        if not path.exists():
            return f"File not found: {file_path}"
        content = path.read_text(encoding="utf-8")
        count = content.count(find_text)
        if count == 0:
            return f"'{find_text}' not found in file."
        self._backup_file(path)
        if occurrence == 0:
            new = content.replace(find_text, replace_text)
            path.write_text(new, encoding="utf-8")
            await self._broadcast_doc(file_path, new)
            return f"Replaced all {count} occurrences."
        else:
            # Replace the nth occurrence
            parts = content.split(find_text)
            if occurrence > count:
                return f"Only {count} occurrences found, cannot replace #{occurrence}."
            new = (
                find_text.join(parts[:occurrence])
                + replace_text
                + find_text.join(parts[occurrence:])
            )
            path.write_text(new, encoding="utf-8")
            await self._broadcast_doc(file_path, new)
            return f"Replaced occurrence #{occurrence} of {count}."

    @function_tool()
    async def insert_text(
        self, context: RunContext, file_path: str, after_text: str, new_text: str
    ) -> str:
        """Insert text after a specified anchor line.

        Args:
            file_path: Path to the file relative to workspace.
            after_text: Text to search for — new_text will be inserted after the line containing this.
            new_text: The text to insert.
        """
        path = self._resolve_path(file_path)
        if not path.exists():
            return f"File not found: {file_path}"
        content = path.read_text(encoding="utf-8")
        lines = content.split("\n")
        after_lower = after_text.lower()
        found_line = None
        for i, line in enumerate(lines):
            if after_lower in line.lower():
                found_line = i + 1  # 1-indexed
                break
        if found_line is None:
            return f"Anchor text '{after_text}' not found."
        self._backup_file(path)
        new = markdown_ops.insert_after_line(content, found_line, new_text)
        path.write_text(new, encoding="utf-8")
        await self._broadcast_doc(file_path, new)
        return f"Inserted text after line {found_line}."

    @function_tool()
    async def append_to_section(
        self, context: RunContext, file_path: str, heading: str, content: str
    ) -> str:
        """Append text to the end of a section.

        Args:
            file_path: Path to the file relative to workspace.
            heading: The heading text to search for.
            content: Text to append at the end of the section.
        """
        path = self._resolve_path(file_path)
        if not path.exists():
            return f"File not found: {file_path}"
        file_content = path.read_text(encoding="utf-8")
        matches = markdown_ops.find_section(file_content, heading)
        if not matches:
            return f"No section matching '{heading}' found."
        if len(matches) > 1:
            names = [f"- {s.heading} (line {s.start_line})" for s in matches]
            return "Multiple matches, be more specific:\n" + "\n".join(names)
        section = matches[0]
        self._backup_file(path)
        new = markdown_ops.insert_after_line(file_content, section.end_line, content)
        path.write_text(new, encoding="utf-8")
        await self._broadcast_doc(file_path, new)
        return f"Appended to section '{section.heading}'."

    @function_tool()
    async def append_to_file(
        self, context: RunContext, file_path: str, content: str
    ) -> str:
        """Append text to the end of a file.

        Args:
            file_path: Path to the file relative to workspace.
            content: Text to append.
        """
        path = self._resolve_path(file_path)
        if not path.exists():
            return f"File not found: {file_path}"
        self._backup_file(path)
        existing = path.read_text(encoding="utf-8")
        if existing and not existing.endswith("\n"):
            existing += "\n"
        new = existing + content + "\n"
        path.write_text(new, encoding="utf-8")
        await self._broadcast_doc(file_path, new)
        return "Content appended to end of file."

    @function_tool()
    async def delete_section(
        self, context: RunContext, file_path: str, heading: str
    ) -> str:
        """Delete an entire section including its heading.

        Args:
            file_path: Path to the file relative to workspace.
            heading: The heading text to search for.
        """
        path = self._resolve_path(file_path)
        if not path.exists():
            return f"File not found: {file_path}"
        file_content = path.read_text(encoding="utf-8")
        matches = markdown_ops.find_section(file_content, heading)
        if not matches:
            return f"No section matching '{heading}' found."
        if len(matches) > 1:
            names = [f"- {s.heading} (line {s.start_line})" for s in matches]
            return "Multiple matches, be more specific:\n" + "\n".join(names)
        section = matches[0]
        self._backup_file(path)
        new = markdown_ops.delete_line_range(file_content, section.start_line, section.end_line)
        path.write_text(new, encoding="utf-8")
        await self._broadcast_doc(file_path, new)
        return f"Deleted section '{section.heading}' (lines {section.start_line}-{section.end_line})."

    @function_tool()
    async def delete_lines(
        self, context: RunContext, file_path: str, start_line: int, end_line: int
    ) -> str:
        """Delete a range of lines from a file.

        Args:
            file_path: Path to the file relative to workspace.
            start_line: First line to delete (1-indexed).
            end_line: Last line to delete (1-indexed, inclusive).
        """
        path = self._resolve_path(file_path)
        if not path.exists():
            return f"File not found: {file_path}"
        file_content = path.read_text(encoding="utf-8")
        total = len(file_content.split("\n"))
        if start_line < 1 or end_line > total or start_line > end_line:
            return f"Invalid line range {start_line}-{end_line} (file has {total} lines)."
        self._backup_file(path)
        new = markdown_ops.delete_line_range(file_content, start_line, end_line)
        path.write_text(new, encoding="utf-8")
        await self._broadcast_doc(file_path, new)
        return f"Deleted lines {start_line}-{end_line}."

    # ── File management tools ──────────────────────────────────────

    @function_tool()
    async def create_file(
        self, context: RunContext, file_path: str, content: str = ""
    ) -> str:
        """Create a new markdown file.

        Args:
            file_path: Path for the new file relative to workspace.
            content: Initial content for the file.
        """
        path = self._resolve_path(file_path)
        if path.exists():
            return f"File already exists: {file_path}"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        await self._broadcast_doc(file_path, content)
        return f"Created {file_path}."

    @function_tool()
    async def undo(self, context: RunContext, file_path: str) -> str:
        """Revert the last change to a file (single-level undo).

        Args:
            file_path: Path to the file relative to workspace.
        """
        path = self._resolve_path(file_path)
        key = str(path)
        if key not in self._backups:
            return "No undo history for this file."
        path.write_text(self._backups[key], encoding="utf-8")
        del self._backups[key]
        return f"Reverted {file_path} to previous version."

    @function_tool()
    async def deep_think(self, context: RunContext, task: str) -> str:
        """Delegate a complex task to a more capable agent with full file access.

        Use for multi-step work: restructuring documents, batch edits, creating
        multiple related files, or tasks requiring planning and iteration.

        Args:
            task: Detailed description of what needs to be done.
        """
        return await run_deep_agent(task, self._workspace)
