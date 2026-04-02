"""MarkdownEditorAgent with function tools for voice-controlled editing."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import TYPE_CHECKING

from livekit import rtc
from livekit.agents import function_tool, Agent, AgentSession, RunContext

from . import markdown_ops
from .deep_agent import run_deep_agent

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)

DEFAULT_FILENAME = "doc.md"

SYSTEM_PROMPT = """\
You are a collaborative writing and editing assistant. You work alongside the user \
in real time — they can see the document you're editing live on their screen. \
Think of yourself as a coworker sitting next to them, talking through ideas and \
making edits together.

## What you can do
- Edit the shared markdown document in real time.
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
- For complex multi-step tasks, use the deep_think tool to delegate to a more \
capable agent.
- Use yield_turn when you expect the user to speak at length — telling a story, \
dictating content, outlining multiple points, or thinking through something \
complex with pauses. This prevents you from jumping in during their natural \
pauses. Do NOT use it for quick back-and-forth exchanges.
"""


class MarkdownEditorAgent(Agent):
    def __init__(self, workspace_dir: str) -> None:
        super().__init__(
            instructions=SYSTEM_PROMPT,
        )
        self._workspace = Path(workspace_dir).resolve()
        self._file_path = self._workspace / DEFAULT_FILENAME
        self._backup: str | None = None  # single-level undo
        self._room: rtc.Room | None = None
        self._session: AgentSession | None = None
        self._default_max_delay: float = 3.0
        self._yield_active: bool = False

        # Ensure the file exists
        self._workspace.mkdir(parents=True, exist_ok=True)
        if not self._file_path.exists():
            self._file_path.write_text("", encoding="utf-8")

    def set_session(self, session: AgentSession) -> None:
        """Set the agent session for yield_turn support."""
        self._session = session
        # Reset max_delay after each committed user turn
        session.on("user_state_changed", self._on_user_state_for_yield_reset)

    def _on_user_state_for_yield_reset(self, ev: object) -> None:
        """Reset max_delay after the user finishes speaking post-yield."""
        if not self._yield_active:
            return
        new_state = getattr(ev, "new_state", None)
        old_state = getattr(ev, "old_state", None)
        # User started speaking → they're responding. Reset yield after they finish.
        if old_state == "speaking" and new_state == "listening":
            self._yield_active = False
            if self._session is not None:
                self._session.update_options(
                    max_endpointing_delay=self._default_max_delay
                )
                logger.info("yield_turn reset: max_delay restored to %.1f", self._default_max_delay)

    def set_room(self, room: rtc.Room) -> None:
        """Set the LiveKit room for data channel communication."""
        self._room = room
        room.on("data_received", self._on_data_received)

    def _on_data_received(self, data: rtc.DataPacket) -> None:
        """Handle incoming edits from the web client."""
        try:
            payload = data.data
            msg = json.loads(payload.decode("utf-8"))
            if msg.get("type") == "human_edit" and msg.get("content") is not None:
                self._backup = self._file_path.read_text(encoding="utf-8")
                self._file_path.write_text(msg["content"], encoding="utf-8")
                logger.info("Received human edit")
        except Exception as e:
            logger.warning("Error handling data message: %s", e)

    def _read_doc(self) -> str:
        return self._file_path.read_text(encoding="utf-8")

    def _write_doc(self, content: str) -> None:
        self._backup = self._read_doc()
        self._file_path.write_text(content, encoding="utf-8")

    async def _broadcast(self, content: str) -> None:
        """Send document content to the web client via data channel."""
        if not self._room or not self._room.local_participant:
            return
        msg = json.dumps({
            "type": "doc_update",
            "file": DEFAULT_FILENAME,
            "content": content,
        })
        try:
            await self._room.local_participant.publish_data(
                msg.encode("utf-8"),
                reliable=True,
            )
        except Exception as e:
            logger.warning("Failed to broadcast doc update: %s", e)

    # ── Reading tools ─────────────────────────────────────────────��

    @function_tool()
    async def read_doc(self, context: RunContext) -> str:
        """Read the full document."""
        content = self._read_doc()
        await self._broadcast(content)
        return content or "(empty document)"

    @function_tool()
    async def read_section(self, context: RunContext, heading: str) -> str:
        """Read a specific section by its heading.

        Args:
            heading: The heading text to search for (case-insensitive).
        """
        content = self._read_doc()
        matches = markdown_ops.find_section(content, heading)
        if not matches:
            return f"No section matching '{heading}' found."
        if len(matches) > 1:
            names = [f"- {s.heading} (line {s.start_line})" for s in matches]
            return "Multiple matches:\n" + "\n".join(names)
        s = matches[0]
        return f"## {s.heading} (lines {s.start_line}-{s.end_line})\n{s.body}"

    @function_tool()
    async def get_outline(self, context: RunContext) -> str:
        """Return the heading structure of the document with line numbers."""
        content = self._read_doc()
        outline = markdown_ops.get_outline(content)
        if not outline:
            return "No headings found."
        lines = []
        for line_num, level, text in outline:
            indent = "  " * (level - 1)
            lines.append(f"{indent}Line {line_num}: {'#' * level} {text}")
        return "\n".join(lines)

    @function_tool()
    async def search(self, context: RunContext, query: str) -> str:
        """Search for text in the document.

        Args:
            query: Text to search for (case-insensitive).
        """
        content = self._read_doc()
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
        self, context: RunContext, heading: str, new_content: str
    ) -> str:
        """Replace the body of a section with new content.

        Args:
            heading: The heading text to search for.
            new_content: The new body text for the section.
        """
        content = self._read_doc()
        matches = markdown_ops.find_section(content, heading)
        if not matches:
            return f"No section matching '{heading}' found."
        if len(matches) > 1:
            names = [f"- {s.heading} (line {s.start_line})" for s in matches]
            return "Multiple matches, be more specific:\n" + "\n".join(names)
        new = markdown_ops.replace_section_content(content, matches[0], new_content)
        self._write_doc(new)
        await self._broadcast(new)
        return f"Replaced section '{matches[0].heading}'."

    @function_tool()
    async def find_and_replace(
        self,
        context: RunContext,
        find_text: str,
        replace_text: str,
        occurrence: int = 0,
    ) -> str:
        """Find and replace text in the document.

        Args:
            find_text: The text to find.
            replace_text: The replacement text.
            occurrence: Which occurrence to replace (1-indexed). 0 means all.
        """
        content = self._read_doc()
        count = content.count(find_text)
        if count == 0:
            return f"'{find_text}' not found."
        if occurrence == 0:
            new = content.replace(find_text, replace_text)
            self._write_doc(new)
            await self._broadcast(new)
            return f"Replaced all {count} occurrences."
        else:
            parts = content.split(find_text)
            if occurrence > count:
                return f"Only {count} occurrences found, cannot replace #{occurrence}."
            new = (
                find_text.join(parts[:occurrence])
                + replace_text
                + find_text.join(parts[occurrence:])
            )
            self._write_doc(new)
            await self._broadcast(new)
            return f"Replaced occurrence #{occurrence} of {count}."

    @function_tool()
    async def insert_text(
        self, context: RunContext, after_text: str, new_text: str
    ) -> str:
        """Insert text after a specified anchor line.

        Args:
            after_text: Text to search for — new_text is inserted after the line containing this.
            new_text: The text to insert.
        """
        content = self._read_doc()
        lines = content.split("\n")
        after_lower = after_text.lower()
        found_line = None
        for i, line in enumerate(lines):
            if after_lower in line.lower():
                found_line = i + 1
                break
        if found_line is None:
            return f"Anchor text '{after_text}' not found."
        new = markdown_ops.insert_after_line(content, found_line, new_text)
        self._write_doc(new)
        await self._broadcast(new)
        return f"Inserted text after line {found_line}."

    @function_tool()
    async def append_to_section(
        self, context: RunContext, heading: str, content: str
    ) -> str:
        """Append text to the end of a section.

        Args:
            heading: The heading text to search for.
            content: Text to append at the end of the section.
        """
        file_content = self._read_doc()
        matches = markdown_ops.find_section(file_content, heading)
        if not matches:
            return f"No section matching '{heading}' found."
        if len(matches) > 1:
            names = [f"- {s.heading} (line {s.start_line})" for s in matches]
            return "Multiple matches, be more specific:\n" + "\n".join(names)
        section = matches[0]
        new = markdown_ops.insert_after_line(file_content, section.end_line, content)
        self._write_doc(new)
        await self._broadcast(new)
        return f"Appended to section '{section.heading}'."

    @function_tool()
    async def append(self, context: RunContext, content: str) -> str:
        """Append text to the end of the document.

        Args:
            content: Text to append.
        """
        existing = self._read_doc()
        if existing and not existing.endswith("\n"):
            existing += "\n"
        new = existing + content + "\n"
        self._write_doc(new)
        await self._broadcast(new)
        return "Content appended."

    @function_tool()
    async def write_doc(self, context: RunContext, content: str) -> str:
        """Replace the entire document content.

        Args:
            content: The new full document content.
        """
        self._write_doc(content)
        await self._broadcast(content)
        return "Document updated."

    @function_tool()
    async def delete_section(self, context: RunContext, heading: str) -> str:
        """Delete an entire section including its heading.

        Args:
            heading: The heading text to search for.
        """
        file_content = self._read_doc()
        matches = markdown_ops.find_section(file_content, heading)
        if not matches:
            return f"No section matching '{heading}' found."
        if len(matches) > 1:
            names = [f"- {s.heading} (line {s.start_line})" for s in matches]
            return "Multiple matches, be more specific:\n" + "\n".join(names)
        section = matches[0]
        new = markdown_ops.delete_line_range(file_content, section.start_line, section.end_line)
        self._write_doc(new)
        await self._broadcast(new)
        return f"Deleted section '{section.heading}'."

    @function_tool()
    async def delete_lines(
        self, context: RunContext, start_line: int, end_line: int
    ) -> str:
        """Delete a range of lines from the document.

        Args:
            start_line: First line to delete (1-indexed).
            end_line: Last line to delete (1-indexed, inclusive).
        """
        file_content = self._read_doc()
        total = len(file_content.split("\n"))
        if start_line < 1 or end_line > total or start_line > end_line:
            return f"Invalid line range {start_line}-{end_line} (document has {total} lines)."
        new = markdown_ops.delete_line_range(file_content, start_line, end_line)
        self._write_doc(new)
        await self._broadcast(new)
        return f"Deleted lines {start_line}-{end_line}."

    # ── Utility tools ─────────────────────────────────────────────

    @function_tool()
    async def undo(self, context: RunContext) -> str:
        """Revert the last change (single-level undo)."""
        if self._backup is None:
            return "Nothing to undo."
        self._file_path.write_text(self._backup, encoding="utf-8")
        content = self._backup
        self._backup = None
        await self._broadcast(content)
        return "Reverted to previous version."

    @function_tool()
    async def yield_turn(self, context: RunContext, patience: float = 0) -> str:
        """Give the user extra time to speak without being interrupted.

        Call this BEFORE the user starts their response when you expect them to:
        - Tell a story or give a long explanation
        - Monologue or dictate content at length
        - Think through something complex with pauses between thoughts
        - Outline multiple items or details
        - Answer a question that requires reflection

        Do NOT call this for quick back-and-forth exchanges. Only use it when
        the user needs room to speak at length or think with pauses.

        Args:
            patience: 0 = wait as long as needed (default, best for most cases).
                1-3 = moderately more patient. Use when the user might pause
                briefly but you still want normal turn-taking to resume soon.
        """
        if self._session is None:
            return "Session not available."
        try:
            self._yield_active = True
            if patience == 0:
                self._session.update_options(max_endpointing_delay=300.0)
                return "Listening mode on. Will wait for the user to finish."
            else:
                self._session.update_options(
                    max_endpointing_delay=self._default_max_delay * (1 + patience)
                )
                return f"Extra patience set. Will reset after user speaks."
        except Exception as e:
            logger.warning("yield_turn failed: %s", e)
            return f"Failed to adjust patience: {e}"

    @function_tool()
    async def deep_think(self, context: RunContext, task: str) -> str:
        """Delegate a complex task to a more capable agent with full file access.

        Use for multi-step work: restructuring documents, batch edits, or
        tasks requiring planning and iteration.

        Args:
            task: Detailed description of what needs to be done.
        """
        return await run_deep_agent(task, self._workspace)
