"""MarkdownEditorAgent with function tools for voice-controlled editing."""

from __future__ import annotations

from pathlib import Path

from livekit.agents import function_tool, Agent, RunContext

from . import markdown_ops
from .deep_agent import run_deep_agent


SYSTEM_PROMPT = """\
You are the OpenClaw Onboarding Agent — a conversational guide that helps users \
design their ideal OpenClaw setup. Your job is to understand what the user wants \
to accomplish, then collaboratively build a markdown spec document that captures \
the full configuration: agents, roles, team structure, workflows, and integrations.

## How the conversation works

Phase 1 — Discovery (start here):
- Ask about their use-case in plain language. What problems are they trying to solve? \
What does their current workflow look like? What's painful about it?
- Probe for specifics: How many people are involved? What tools do they already use? \
What does success look like?
- Keep questions conversational and one at a time. Don't overwhelm with a checklist.
- Listen for signals about whether they need a single OpenClaw agent or a swarm/team \
with distinct roles.

Phase 2 — Spec drafting (transition when you have enough context):
- Create a spec file (e.g. "openclaw-setup.md") and start populating it live as the \
conversation progresses. Don't wait until the end — draft early and revise often.
- The spec should include:
  - **Overview**: One-paragraph summary of what the setup accomplishes.
  - **Agents**: Each agent's name, role, capabilities, and the tools/APIs it accesses.
  - **Team structure** (if multi-agent): How agents collaborate, who delegates to whom, \
    what the communication flow looks like.
  - **Architecture diagram**: A Mermaid diagram showing agents, their relationships, \
    data flows, and external integrations.
  - **Workflows**: Step-by-step descriptions of key workflows (e.g. "when a new ticket \
    comes in, Agent A triages, Agent B researches, Agent C drafts a response").
  - **Integrations**: External tools, APIs, data sources each agent connects to.
  - **Guardrails**: Any constraints, approval gates, or human-in-the-loop checkpoints.
- After each edit, briefly tell the user what you changed and ask if it matches their \
  mental model.

Phase 3 — Refinement (iterate until the user is satisfied):
- Walk through the spec with the user. Ask if anything is missing or wrong.
- Offer to adjust scope, add/remove agents, change workflows, etc.
- When the user is happy, confirm the spec is ready to be used for setup.

## Rules
- Be concise and natural. Short sentences. No corporate jargon.
- Do not use markdown formatting in your speech — speak naturally since the user \
is interacting by voice.
- One question at a time. Let the user talk.
- Start editing the spec file as soon as you have enough context for an initial draft — \
don't wait for the full picture. It's easier to react to something concrete.
- When reading back spec content, summarize rather than reading verbatim. Only read \
the full text if the user asks.
- File paths are relative to the workspace directory. The user can refer to files \
by name without the .md extension.
- For complex multi-step tasks (restructuring the spec, generating detailed workflow \
breakdowns, or creating multiple related files), use the deep_think tool to delegate \
to a more capable agent.
"""


class MarkdownEditorAgent(Agent):
    def __init__(self, workspace_dir: str) -> None:
        super().__init__(
            instructions=SYSTEM_PROMPT,
        )
        self._workspace = Path(workspace_dir).resolve()
        self._backups: dict[str, str] = {}  # path -> previous content

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
        return path.read_text(encoding="utf-8")

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
        path.write_text(existing + content + "\n", encoding="utf-8")
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
