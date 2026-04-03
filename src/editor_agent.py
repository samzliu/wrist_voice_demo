"""MarkdownEditorAgent — voice-controlled workspace with file editing, slides, search, and web tools."""

from __future__ import annotations

import asyncio
import fnmatch
import json
import logging
import shutil
import tempfile
import time
from pathlib import Path

from livekit import rtc
from livekit.agents import function_tool, Agent, AgentSession, RunContext

from . import broadcast as bc
from . import markdown_ops
from . import slide_ops
from . import exa_tools
from . import web_tools
from .deep_agent import run_deep_agent, DeepAgentBridge

logger = logging.getLogger(__name__)

DEFAULT_FILENAME = "doc.md"
DEFAULT_MAX_DELAY = 3.0

SYSTEM_PROMPT_WORKSPACE = """\
You are a writing collaborator. The user sees your edits live on screen.

Be terse. Don't narrate actions — the user sees tool results live. Only speak \
what they need to hear. Don't repeat things back. Don't say "I'll now..." — \
just do it. Use shorthand. Act with agency, not permission.

One question at a time. Keep exchanges tight. No markdown formatting in speech. \
Summarize rather than read verbatim.

For complex multi-step tasks, use deep_think (blocking) or deep_think_background \
(continues conversation while working).
"""

SYSTEM_PROMPT_CHAT = """\
You are a voice conversation partner. Be natural, concise, and responsive.

Be terse. Short sentences. Don't repeat things back. Don't narrate what you're \
doing. Respond like a real person — with agency, opinions, and shorthand.

One question at a time. Keep exchanges tight. No markdown formatting in speech.

You can use web_search and visit_website if the conversation calls for research.
"""


def _resolve_path(workspace: Path, rel_path: str) -> Path:
    """Resolve a path relative to workspace, rejecting escapes."""
    resolved = (workspace / rel_path).resolve()
    if not str(resolved).startswith(str(workspace.resolve())):
        raise ValueError(f"Path escapes workspace: {rel_path}")
    return resolved


def _file_type(name: str) -> str:
    if name.endswith(".html") or name.endswith(".htm"):
        return "html"
    if name.endswith(".md") or name.endswith(".markdown") or name.endswith(".txt"):
        return "markdown"
    return "other"


class MarkdownEditorAgent(Agent):
    def __init__(self, workspace_dir: str) -> None:
        super().__init__(instructions=SYSTEM_PROMPT_WORKSPACE)
        self._workspace = Path(workspace_dir).resolve()
        self._file_path = self._workspace / DEFAULT_FILENAME
        self._backup: str | None = None
        self._room: rtc.Room | None = None
        self._session: AgentSession | None = None
        self._paused: bool = False
        self._persona_content: str = ""
        self._mode: str = "workspace"
        self._temp_workspace: str | None = None  # set if we created a temp dir
        self._background_tasks: dict[str, asyncio.Task] = {}

        # Ensure workspace exists
        self._workspace.mkdir(parents=True, exist_ok=True)
        if not self._file_path.exists():
            self._file_path.write_text("", encoding="utf-8")

    def set_session(self, session: AgentSession) -> None:
        self._session = session

    def set_room(self, room: rtc.Room) -> None:
        self._room = room
        room.on("data_received", self._on_data_received)
        # Broadcast file list once the session starts (agent joins room)
        asyncio.get_event_loop().call_later(2.0, lambda: asyncio.ensure_future(self._broadcast_file_list()))

    # ── Data channel handling ──────────────────────────────────

    def _on_data_received(self, data: rtc.DataPacket) -> None:
        try:
            msg = json.loads(data.data.decode("utf-8"))
            msg_type = msg.get("type")

            if msg_type == "config":
                asyncio.create_task(self._handle_config(msg))
            elif msg_type == "human_edit" and msg.get("content") is not None:
                file_name = msg.get("file", DEFAULT_FILENAME)
                path = _resolve_path(self._workspace, file_name)
                self._backup = path.read_text(encoding="utf-8") if path.exists() else ""
                path.write_text(msg["content"], encoding="utf-8")
                self._file_path = path
                logger.info("Received human edit on %s", file_name)
            elif msg_type == "pause":
                self._handle_pause()
            elif msg_type == "resume":
                self._handle_resume()
            elif msg_type == "monologue_on":
                if self._session:
                    self._session.update_options(max_endpointing_delay=300.0)
            elif msg_type == "monologue_off":
                if self._session:
                    self._session.update_options(max_endpointing_delay=DEFAULT_MAX_DELAY)
                    self._session.commit_user_turn()
            elif msg_type == "request_file_list":
                asyncio.create_task(self._broadcast_file_list())
            elif msg_type == "request_file_content":
                asyncio.create_task(self._send_file_content(msg.get("file", "")))
            elif msg_type == "file_create":
                asyncio.create_task(self._handle_file_create(msg))
            elif msg_type == "file_rename":
                asyncio.create_task(self._handle_file_rename(msg))
            elif msg_type == "file_delete":
                asyncio.create_task(self._handle_file_delete(msg))
            elif msg_type == "cancel_deep_think":
                self._cancel_background_tasks()
        except Exception as e:
            logger.warning("Error handling data message: %s", e)

    async def _handle_config(self, msg: dict) -> None:
        self._mode = msg.get("mode", "workspace")
        base_prompt = SYSTEM_PROMPT_CHAT if self._mode == "chat" else SYSTEM_PROMPT_WORKSPACE

        workspace_path = msg.get("workspace_path", "")
        if self._mode == "workspace":
            if workspace_path:
                new_ws = Path(workspace_path).resolve()
                new_ws.mkdir(parents=True, exist_ok=True)
                self._workspace = new_ws
                self._file_path = new_ws / DEFAULT_FILENAME
                if not self._file_path.exists():
                    self._file_path.write_text("", encoding="utf-8")
                logger.info("Workspace set to %s", new_ws)
            else:
                tmp = tempfile.mkdtemp(prefix="wrist-session-")
                self._temp_workspace = tmp
                self._workspace = Path(tmp)
                self._file_path = self._workspace / DEFAULT_FILENAME
                self._file_path.write_text("", encoding="utf-8")
                logger.info("Created temp workspace: %s", tmp)

        script_content = msg.get("script_content", "")
        if script_content:
            self._persona_content = script_content
            new_instructions = (
                base_prompt
                + "\n\n## Your Role / Persona\n\n"
                + "IMPORTANT: You MUST adopt the following role and personality for this "
                + "entire conversation. Stay in character at all times. This defines who "
                + "you are, how you speak, and how you behave:\n\n"
                + script_content
            )
        else:
            new_instructions = base_prompt

        await self.update_instructions(new_instructions)
        logger.info(
            "Config applied: mode=%s, persona=%s, persona_len=%d",
            self._mode, bool(script_content), len(script_content),
        )

        if self._mode == "workspace":
            await self._broadcast_file_list()

    def cleanup(self) -> None:
        """Clean up temp workspace on disconnect."""
        if self._temp_workspace and Path(self._temp_workspace).exists():
            shutil.rmtree(self._temp_workspace, ignore_errors=True)
            logger.info("Cleaned up temp workspace: %s", self._temp_workspace)

    def _handle_pause(self) -> None:
        self._paused = True
        if self._session:
            self._session.interrupt()
            self._session.update_options(max_endpointing_delay=300.0)
        asyncio.create_task(bc.broadcast_agent_state(self._room, "paused"))
        logger.info("Agent paused")

    def _handle_resume(self) -> None:
        self._paused = False
        if self._session:
            self._session.update_options(max_endpointing_delay=DEFAULT_MAX_DELAY)
        asyncio.create_task(bc.broadcast_agent_state(self._room, "active"))
        logger.info("Agent resumed")

    def _cancel_background_tasks(self) -> None:
        for name, task in list(self._background_tasks.items()):
            task.cancel()
            logger.info("Cancelled background task: %s", name)

    # ── File broadcast helpers ─────────────────────────────────

    async def _broadcast_file_list(self) -> None:
        files = []
        for f in sorted(self._workspace.rglob("*")):
            if f.is_file() and not f.name.startswith("."):
                rel = str(f.relative_to(self._workspace))
                files.append({"name": rel, "type": _file_type(rel)})
        await bc.broadcast_file_list(self._room, files)

    async def _send_file_content(self, file_name: str) -> None:
        try:
            path = _resolve_path(self._workspace, file_name)
            content = path.read_text(encoding="utf-8")
            ft = _file_type(file_name)
            await bc.broadcast_file_content(self._room, file_name, content, ft)
            self._file_path = path
        except Exception as e:
            logger.warning("Failed to send file content: %s", e)

    async def _handle_file_create(self, msg: dict) -> None:
        name = msg.get("name", "")
        if not name:
            return
        path = _resolve_path(self._workspace, name)
        path.parent.mkdir(parents=True, exist_ok=True)
        if not path.exists():
            path.write_text("", encoding="utf-8")
        await self._broadcast_file_list()

    async def _handle_file_rename(self, msg: dict) -> None:
        old = msg.get("old_name", "")
        new = msg.get("new_name", "")
        if not old or not new:
            return
        old_path = _resolve_path(self._workspace, old)
        new_path = _resolve_path(self._workspace, new)
        if old_path.exists():
            old_path.rename(new_path)
        await self._broadcast_file_list()

    async def _handle_file_delete(self, msg: dict) -> None:
        name = msg.get("name", "")
        if not name:
            return
        path = _resolve_path(self._workspace, name)
        if path.exists():
            path.unlink()
        await self._broadcast_file_list()

    # ── Tool tracing helpers ───────────────────────────────────

    async def _trace_start(self, name: str, args: dict) -> tuple[str, float]:
        call_id = await bc.broadcast_tool_call(self._room, name, args)
        return call_id, time.monotonic()

    async def _trace_end(self, call_id: str, result: str, start: float) -> None:
        await bc.broadcast_tool_result(self._room, call_id, result, start)

    # ── Internal file ops ──────────────────────────────────────

    def _read_doc(self) -> str:
        return self._file_path.read_text(encoding="utf-8")

    def _write_doc(self, content: str) -> None:
        self._backup = self._read_doc()
        self._file_path.write_text(content, encoding="utf-8")

    async def _broadcast_doc(self, content: str) -> None:
        name = str(self._file_path.relative_to(self._workspace))
        await bc.broadcast_doc_update(self._room, name, content)

    # ── Reading tools ──────────────────────────────────────────

    @function_tool()
    async def read_doc(self, context: RunContext) -> str:
        """Read the current document."""
        cid, t = await self._trace_start("read_doc", {})
        content = self._read_doc()
        await self._broadcast_doc(content)
        result = content or "(empty document)"
        await self._trace_end(cid, result[:200], t)
        return result

    @function_tool()
    async def read_section(self, context: RunContext, heading: str) -> str:
        """Read a specific section by heading.

        Args:
            heading: The heading text to search for (case-insensitive).
        """
        cid, t = await self._trace_start("read_section", {"heading": heading})
        content = self._read_doc()
        matches = markdown_ops.find_section(content, heading)
        if not matches:
            result = f"No section matching '{heading}' found."
        elif len(matches) > 1:
            names = [f"- {s.heading} (line {s.start_line})" for s in matches]
            result = "Multiple matches:\n" + "\n".join(names)
        else:
            s = matches[0]
            result = f"## {s.heading} (lines {s.start_line}-{s.end_line})\n{s.body}"
        await self._trace_end(cid, result[:200], t)
        return result

    @function_tool()
    async def get_outline(self, context: RunContext) -> str:
        """Return the heading structure of the document with line numbers."""
        cid, t = await self._trace_start("get_outline", {})
        content = self._read_doc()
        outline = markdown_ops.get_outline(content)
        if not outline:
            result = "No headings found."
        else:
            lines = []
            for line_num, level, text in outline:
                indent = "  " * (level - 1)
                lines.append(f"{indent}Line {line_num}: {'#' * level} {text}")
            result = "\n".join(lines)
        await self._trace_end(cid, result[:200], t)
        return result

    @function_tool()
    async def search(self, context: RunContext, query: str) -> str:
        """Search for text in the current document.

        Args:
            query: Text to search for (case-insensitive).
        """
        cid, t = await self._trace_start("search", {"query": query})
        content = self._read_doc()
        query_lower = query.lower()
        matches = []
        for i, line in enumerate(content.split("\n"), 1):
            if query_lower in line.lower():
                matches.append(f"Line {i}: {line}")
        result = "\n".join(matches) if matches else f"No matches for '{query}'."
        await self._trace_end(cid, result[:200], t)
        return result

    # ── Editing tools ──────────────────────────────────────────

    @function_tool()
    async def replace_section(
        self, context: RunContext, heading: str, new_content: str
    ) -> str:
        """Replace the body of a section.

        Args:
            heading: The heading text to search for.
            new_content: The new body text for the section.
        """
        cid, t = await self._trace_start("replace_section", {"heading": heading})
        content = self._read_doc()
        matches = markdown_ops.find_section(content, heading)
        if not matches:
            result = f"No section matching '{heading}' found."
        elif len(matches) > 1:
            names = [f"- {s.heading} (line {s.start_line})" for s in matches]
            result = "Multiple matches, be more specific:\n" + "\n".join(names)
        else:
            new = markdown_ops.replace_section_content(content, matches[0], new_content)
            self._write_doc(new)
            await self._broadcast_doc(new)
            result = f"Replaced section '{matches[0].heading}'."
        await self._trace_end(cid, result, t)
        return result

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
        cid, t = await self._trace_start("find_and_replace", {"find": find_text, "replace": replace_text})
        content = self._read_doc()
        count = content.count(find_text)
        if count == 0:
            result = f"'{find_text}' not found."
        elif occurrence == 0:
            new = content.replace(find_text, replace_text)
            self._write_doc(new)
            await self._broadcast_doc(new)
            result = f"Replaced all {count} occurrences."
        else:
            parts = content.split(find_text)
            if occurrence > count:
                result = f"Only {count} occurrences found, cannot replace #{occurrence}."
            else:
                new = (
                    find_text.join(parts[:occurrence])
                    + replace_text
                    + find_text.join(parts[occurrence:])
                )
                self._write_doc(new)
                await self._broadcast_doc(new)
                result = f"Replaced occurrence #{occurrence} of {count}."
        await self._trace_end(cid, result, t)
        return result

    @function_tool()
    async def insert_text(
        self, context: RunContext, after_text: str, new_text: str
    ) -> str:
        """Insert text after a specified anchor line.

        Args:
            after_text: Text to search for — new_text is inserted after the line containing this.
            new_text: The text to insert.
        """
        cid, t = await self._trace_start("insert_text", {"after": after_text})
        content = self._read_doc()
        lines = content.split("\n")
        after_lower = after_text.lower()
        found_line = None
        for i, line in enumerate(lines):
            if after_lower in line.lower():
                found_line = i + 1
                break
        if found_line is None:
            result = f"Anchor text '{after_text}' not found."
        else:
            new = markdown_ops.insert_after_line(content, found_line, new_text)
            self._write_doc(new)
            await self._broadcast_doc(new)
            result = f"Inserted text after line {found_line}."
        await self._trace_end(cid, result, t)
        return result

    @function_tool()
    async def append_to_section(
        self, context: RunContext, heading: str, content: str
    ) -> str:
        """Append text to the end of a section.

        Args:
            heading: The heading text to search for.
            content: Text to append at the end of the section.
        """
        cid, t = await self._trace_start("append_to_section", {"heading": heading})
        file_content = self._read_doc()
        matches = markdown_ops.find_section(file_content, heading)
        if not matches:
            result = f"No section matching '{heading}' found."
        elif len(matches) > 1:
            names = [f"- {s.heading} (line {s.start_line})" for s in matches]
            result = "Multiple matches, be more specific:\n" + "\n".join(names)
        else:
            section = matches[0]
            new = markdown_ops.insert_after_line(file_content, section.end_line, content)
            self._write_doc(new)
            await self._broadcast_doc(new)
            result = f"Appended to section '{section.heading}'."
        await self._trace_end(cid, result, t)
        return result

    @function_tool()
    async def append(self, context: RunContext, content: str) -> str:
        """Append text to the end of the document.

        Args:
            content: Text to append.
        """
        cid, t = await self._trace_start("append", {})
        existing = self._read_doc()
        if existing and not existing.endswith("\n"):
            existing += "\n"
        new = existing + content + "\n"
        self._write_doc(new)
        await self._broadcast_doc(new)
        result = "Content appended."
        await self._trace_end(cid, result, t)
        return result

    @function_tool()
    async def write_doc(self, context: RunContext, content: str) -> str:
        """Replace the entire document content.

        Args:
            content: The new full document content.
        """
        cid, t = await self._trace_start("write_doc", {})
        self._write_doc(content)
        await self._broadcast_doc(content)
        result = "Document updated."
        await self._trace_end(cid, result, t)
        return result

    @function_tool()
    async def delete_section(self, context: RunContext, heading: str) -> str:
        """Delete an entire section including its heading.

        Args:
            heading: The heading text to search for.
        """
        cid, t = await self._trace_start("delete_section", {"heading": heading})
        file_content = self._read_doc()
        matches = markdown_ops.find_section(file_content, heading)
        if not matches:
            result = f"No section matching '{heading}' found."
        elif len(matches) > 1:
            names = [f"- {s.heading} (line {s.start_line})" for s in matches]
            result = "Multiple matches, be more specific:\n" + "\n".join(names)
        else:
            section = matches[0]
            new = markdown_ops.delete_line_range(file_content, section.start_line, section.end_line)
            self._write_doc(new)
            await self._broadcast_doc(new)
            result = f"Deleted section '{section.heading}'."
        await self._trace_end(cid, result, t)
        return result

    @function_tool()
    async def delete_lines(
        self, context: RunContext, start_line: int, end_line: int
    ) -> str:
        """Delete a range of lines from the document.

        Args:
            start_line: First line to delete (1-indexed).
            end_line: Last line to delete (1-indexed, inclusive).
        """
        cid, t = await self._trace_start("delete_lines", {"start": start_line, "end": end_line})
        file_content = self._read_doc()
        total = len(file_content.split("\n"))
        if start_line < 1 or end_line > total or start_line > end_line:
            result = f"Invalid line range {start_line}-{end_line} (document has {total} lines)."
        else:
            new = markdown_ops.delete_line_range(file_content, start_line, end_line)
            self._write_doc(new)
            await self._broadcast_doc(new)
            result = f"Deleted lines {start_line}-{end_line}."
        await self._trace_end(cid, result, t)
        return result

    # ── Workspace file tools ───────────────────────────────────

    @function_tool()
    async def list_files(self, context: RunContext, glob_pattern: str = "*") -> str:
        """List files in the workspace.

        Args:
            glob_pattern: Glob pattern to filter files (e.g. '*.md'). Defaults to '*'.
        """
        cid, t = await self._trace_start("list_files", {"pattern": glob_pattern})
        files = sorted(
            str(f.relative_to(self._workspace))
            for f in self._workspace.rglob("*")
            if f.is_file()
            and not f.name.startswith(".")
            and fnmatch.fnmatch(f.name, glob_pattern)
        )
        result = "\n".join(files) if files else "No files found."
        await self._trace_end(cid, result[:200], t)
        await self._broadcast_file_list()
        return result

    @function_tool()
    async def create_file(self, context: RunContext, path: str, content: str = "") -> str:
        """Create a new file in the workspace.

        Args:
            path: File path relative to workspace.
            content: Initial content (default empty).
        """
        cid, t = await self._trace_start("create_file", {"path": path})
        resolved = _resolve_path(self._workspace, path)
        resolved.parent.mkdir(parents=True, exist_ok=True)
        resolved.write_text(content, encoding="utf-8")
        result = f"Created {path}"
        await self._trace_end(cid, result, t)
        await self._broadcast_file_list()
        ft = _file_type(path)
        await bc.broadcast_file_content(self._room, path, content, ft)
        return result

    @function_tool()
    async def read_file(self, context: RunContext, path: str) -> str:
        """Read a file from the workspace.

        Args:
            path: File path relative to workspace.
        """
        cid, t = await self._trace_start("read_file", {"path": path})
        resolved = _resolve_path(self._workspace, path)
        if not resolved.exists():
            result = f"File not found: {path}"
        else:
            content = resolved.read_text(encoding="utf-8")
            self._file_path = resolved
            ft = _file_type(path)
            await bc.broadcast_file_content(self._room, path, content, ft)
            result = content or "(empty file)"
        await self._trace_end(cid, result[:200], t)
        return result

    @function_tool()
    async def write_file(self, context: RunContext, path: str, content: str) -> str:
        """Write content to a workspace file, creating or overwriting it.

        Args:
            path: File path relative to workspace.
            content: The content to write.
        """
        cid, t = await self._trace_start("write_file", {"path": path})
        resolved = _resolve_path(self._workspace, path)
        resolved.parent.mkdir(parents=True, exist_ok=True)
        self._backup = resolved.read_text(encoding="utf-8") if resolved.exists() else None
        resolved.write_text(content, encoding="utf-8")
        self._file_path = resolved
        ft = _file_type(path)
        await bc.broadcast_file_content(self._room, path, content, ft)
        await self._broadcast_file_list()
        result = f"Wrote {len(content)} chars to {path}"
        await self._trace_end(cid, result, t)
        return result

    @function_tool()
    async def delete_file(self, context: RunContext, path: str) -> str:
        """Delete a file from the workspace.

        Args:
            path: File path relative to workspace.
        """
        cid, t = await self._trace_start("delete_file", {"path": path})
        resolved = _resolve_path(self._workspace, path)
        if resolved.exists():
            resolved.unlink()
            result = f"Deleted {path}"
        else:
            result = f"File not found: {path}"
        await self._trace_end(cid, result, t)
        await self._broadcast_file_list()
        return result

    @function_tool()
    async def rename_file(self, context: RunContext, old_path: str, new_path: str) -> str:
        """Rename/move a file within the workspace.

        Args:
            old_path: Current file path relative to workspace.
            new_path: New file path relative to workspace.
        """
        cid, t = await self._trace_start("rename_file", {"old": old_path, "new": new_path})
        old = _resolve_path(self._workspace, old_path)
        new = _resolve_path(self._workspace, new_path)
        if not old.exists():
            result = f"File not found: {old_path}"
        else:
            new.parent.mkdir(parents=True, exist_ok=True)
            old.rename(new)
            result = f"Renamed {old_path} → {new_path}"
        await self._trace_end(cid, result, t)
        await self._broadcast_file_list()
        return result

    @function_tool()
    async def search_workspace(self, context: RunContext, query: str, glob_pattern: str = "*") -> str:
        """Search for text across all workspace files.

        Args:
            query: Text to search for (case-insensitive).
            glob_pattern: Glob pattern to filter files. Defaults to '*'.
        """
        cid, t = await self._trace_start("search_workspace", {"query": query, "pattern": glob_pattern})
        query_lower = query.lower()
        matches: list[str] = []
        for f in sorted(self._workspace.rglob("*")):
            if not f.is_file() or f.name.startswith("."):
                continue
            if not fnmatch.fnmatch(f.name, glob_pattern):
                continue
            try:
                content = f.read_text(encoding="utf-8")
            except (UnicodeDecodeError, OSError):
                continue
            rel = str(f.relative_to(self._workspace))
            for i, line in enumerate(content.split("\n"), 1):
                if query_lower in line.lower():
                    matches.append(f"{rel}:{i}: {line}")
        result = "\n".join(matches[:100]) if matches else f"No matches for '{query}'."
        await self._trace_end(cid, result[:200], t)
        return result

    # ── Slide tools ────────────────────────────────────────────

    @function_tool()
    async def list_slides(self, context: RunContext, file: str) -> str:
        """List all slides in an HTML slide deck.

        Args:
            file: Path to the HTML slide deck relative to workspace.
        """
        cid, t = await self._trace_start("list_slides", {"file": file})
        resolved = _resolve_path(self._workspace, file)
        if not resolved.exists():
            result = f"File not found: {file}"
        else:
            html = resolved.read_text(encoding="utf-8")
            summary = slide_ops.slide_summary(html)
            if not summary:
                result = "No slides found."
            else:
                lines = [f"  {s['index']}: {s['title']}" for s in summary]
                result = f"{len(summary)} slides:\n" + "\n".join(lines)
        await self._trace_end(cid, result[:200], t)
        return result

    @function_tool()
    async def get_slide(self, context: RunContext, file: str, slide_index: int) -> str:
        """Get a single slide's HTML content.

        Args:
            file: Path to the HTML slide deck.
            slide_index: 0-based slide index.
        """
        cid, t = await self._trace_start("get_slide", {"file": file, "index": slide_index})
        resolved = _resolve_path(self._workspace, file)
        if not resolved.exists():
            result = f"File not found: {file}"
        else:
            html = resolved.read_text(encoding="utf-8")
            slide = slide_ops.get_slide(html, slide_index)
            result = slide if slide else f"Slide {slide_index} not found."
        await self._trace_end(cid, result[:200], t)
        return result

    @function_tool()
    async def create_slide(
        self, context: RunContext, file: str, html_content: str, position: int = -1
    ) -> str:
        """Add a new slide to an HTML deck.

        Args:
            file: Path to the HTML slide deck.
            html_content: The inner HTML content for the slide.
            position: Position to insert at (0-based). -1 appends.
        """
        cid, t = await self._trace_start("create_slide", {"file": file, "position": position})
        resolved = _resolve_path(self._workspace, file)
        resolved.parent.mkdir(parents=True, exist_ok=True)
        if not resolved.exists():
            resolved.write_text(slide_ops.EMPTY_DECK, encoding="utf-8")
        html = resolved.read_text(encoding="utf-8")
        new_html = slide_ops.insert_slide(html, html_content, position)
        resolved.write_text(new_html, encoding="utf-8")
        await bc.broadcast_file_content(self._room, file, new_html, "html")
        count = len(slide_ops.parse_slides(new_html))
        result = f"Slide added. Deck now has {count} slides."
        await self._trace_end(cid, result, t)
        return result

    @function_tool()
    async def edit_slide(
        self, context: RunContext, file: str, slide_index: int, html_content: str
    ) -> str:
        """Replace a slide's content in an HTML deck.

        Args:
            file: Path to the HTML slide deck.
            slide_index: 0-based slide index.
            html_content: New inner HTML content for the slide.
        """
        cid, t = await self._trace_start("edit_slide", {"file": file, "index": slide_index})
        resolved = _resolve_path(self._workspace, file)
        if not resolved.exists():
            result = f"File not found: {file}"
        else:
            html = resolved.read_text(encoding="utf-8")
            try:
                new_html = slide_ops.replace_slide(html, slide_index, html_content)
                resolved.write_text(new_html, encoding="utf-8")
                await bc.broadcast_file_content(self._room, file, new_html, "html")
                result = f"Slide {slide_index} updated."
            except IndexError as e:
                result = str(e)
        await self._trace_end(cid, result, t)
        return result

    @function_tool()
    async def delete_slide_tool(self, context: RunContext, file: str, slide_index: int) -> str:
        """Remove a slide from an HTML deck.

        Args:
            file: Path to the HTML slide deck.
            slide_index: 0-based slide index.
        """
        cid, t = await self._trace_start("delete_slide", {"file": file, "index": slide_index})
        resolved = _resolve_path(self._workspace, file)
        if not resolved.exists():
            result = f"File not found: {file}"
        else:
            html = resolved.read_text(encoding="utf-8")
            try:
                new_html = slide_ops.delete_slide(html, slide_index)
                resolved.write_text(new_html, encoding="utf-8")
                await bc.broadcast_file_content(self._room, file, new_html, "html")
                count = len(slide_ops.parse_slides(new_html))
                result = f"Slide {slide_index} deleted. {count} slides remaining."
            except IndexError as e:
                result = str(e)
        await self._trace_end(cid, result, t)
        return result

    @function_tool()
    async def present_slide(self, context: RunContext, file: str, slide_index: int) -> str:
        """Navigate the client's slide viewer to a specific slide.

        Args:
            file: Path to the HTML slide deck.
            slide_index: 0-based slide index.
        """
        cid, t = await self._trace_start("present_slide", {"file": file, "index": slide_index})
        await bc.broadcast_present_slide(self._room, file, slide_index)
        result = f"Presenting slide {slide_index}."
        await self._trace_end(cid, result, t)
        return result

    # ── Search tools ───────────────────────────────────────────

    @function_tool()
    async def web_search(self, context: RunContext, query: str) -> str:
        """Search the web using Exa.

        Args:
            query: Search query.
        """
        cid, t = await self._trace_start("web_search", {"query": query})
        results = await asyncio.to_thread(exa_tools.web_search, query)
        await bc.broadcast_search_results(self._room, query, results)
        summary = "\n".join(
            f"- {r['title']}: {r['snippet'][:100]}" for r in results[:5]
        )
        result = summary or "No results."
        await self._trace_end(cid, result[:200], t)
        return result

    @function_tool()
    async def deep_research(self, context: RunContext, query: str) -> str:
        """Deep web research with full content using Exa.

        Args:
            query: Research query.
        """
        cid, t = await self._trace_start("deep_research", {"query": query})
        results = await asyncio.to_thread(exa_tools.deep_research, query)
        await bc.broadcast_search_results(self._room, query, results)
        summary = "\n\n".join(
            f"## {r['title']}\n{r.get('content', r['snippet'])[:500]}"
            for r in results[:5]
        )
        result = summary or "No results."
        await self._trace_end(cid, result[:200], t)
        return result

    # ── Web tools ──────────────────────────────────────────────

    @function_tool()
    async def visit_website(self, context: RunContext, url: str) -> str:
        """Fetch and read a website's content.

        Args:
            url: The URL to visit.
        """
        cid, t = await self._trace_start("visit_website", {"url": url})
        data = await web_tools.fetch_url(url)
        await bc.broadcast_url_content(
            self._room, data["url"], data["content"], data.get("title", "")
        )
        result = data["content"][:2000]
        await self._trace_end(cid, result[:200], t)
        return result

    # ── Utility tools ──────────────────────────────────────────

    @function_tool()
    async def undo(self, context: RunContext) -> str:
        """Revert the last change (single-level undo)."""
        cid, t = await self._trace_start("undo", {})
        if self._backup is None:
            result = "Nothing to undo."
        else:
            self._file_path.write_text(self._backup, encoding="utf-8")
            content = self._backup
            self._backup = None
            await self._broadcast_doc(content)
            result = "Reverted to previous version."
        await self._trace_end(cid, result, t)
        return result

    @function_tool()
    async def deep_think(self, context: RunContext, task: str) -> str:
        """Delegate a complex task to a more capable agent. Blocks until done.

        Args:
            task: Detailed description of what needs to be done.
        """
        cid, t = await self._trace_start("deep_think", {"task": task[:100]})
        await bc.broadcast_agent_state(self._room, "thinking")
        result = await run_deep_agent(task, self._workspace)
        await bc.broadcast_agent_state(self._room, "active")
        await self._broadcast_file_list()
        await self._trace_end(cid, result[:200], t)
        return result

    @function_tool()
    async def deep_think_background(self, context: RunContext, task: str) -> str:
        """Launch deep analysis in the background while conversation continues.

        Args:
            task: Detailed description of what needs to be done.
        """
        cid, t = await self._trace_start("deep_think_background", {"task": task[:100]})
        bridge = DeepAgentBridge(self._room, asyncio.get_event_loop())
        task_handle = asyncio.create_task(self._run_deep_background(task, bridge))
        self._background_tasks[task[:50]] = task_handle
        result = "Background analysis started."
        await self._trace_end(cid, result, t)
        return result

    async def _run_deep_background(self, task: str, bridge: DeepAgentBridge) -> None:
        try:
            result = await run_deep_agent(task, self._workspace, bridge=bridge)
            await bc.broadcast(self._room, {
                "type": "deep_think_result",
                "task": task[:200],
                "result": result[:2000],
            })
            await self._broadcast_file_list()
            # Queue the result into the voice conversation
            if self._session:
                await self._session.generate_reply(
                    user_input=f"[System: background analysis complete]\nTask: {task}\nResult: {result}"
                )
        except asyncio.CancelledError:
            if self._session:
                await self._session.say("Background task cancelled.")
        except Exception as e:
            logger.error("Background deep think failed: %s", e)
            if self._session:
                await self._session.say(f"Background task failed: {e}")
        finally:
            key = task[:50]
            self._background_tasks.pop(key, None)
