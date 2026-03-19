"""Pure markdown parsing and manipulation helpers."""

from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass
class Section:
    heading: str
    level: int
    start_line: int  # 1-indexed, line of the heading itself
    end_line: int  # 1-indexed, inclusive
    body: str  # text after the heading line, up to end_line


def _is_in_code_fence(lines: list[str], line_idx: int) -> bool:
    """Check if a line index is inside a fenced code block."""
    fence_open = False
    for i in range(line_idx):
        stripped = lines[i].lstrip()
        if stripped.startswith("```") or stripped.startswith("~~~"):
            fence_open = not fence_open
    return fence_open


def _heading_info(line: str) -> tuple[int, str] | None:
    """Return (level, text) if line is an ATX heading, else None."""
    m = re.match(r"^(#{1,6})\s+(.*?)(?:\s+#+\s*)?$", line)
    if m:
        return len(m.group(1)), m.group(2).strip()
    return None


def parse_sections(content: str) -> list[Section]:
    """Parse a markdown string into a list of Section dataclasses.

    A section runs from its heading until the next heading of equal or higher
    level. Sub-headings are included in the parent section's body.
    Headings inside fenced code blocks are ignored.
    """
    lines = content.split("\n")
    headings: list[tuple[int, int, str]] = []  # (line_idx, level, text)

    for idx, line in enumerate(lines):
        info = _heading_info(line)
        if info and not _is_in_code_fence(lines, idx):
            headings.append((idx, info[0], info[1]))

    if not headings:
        return []

    sections: list[Section] = []
    for i, (idx, level, text) in enumerate(headings):
        # Find end: next heading of equal or higher (lower number) level
        end_idx = len(lines) - 1
        for j in range(i + 1, len(headings)):
            if headings[j][1] <= level:
                end_idx = headings[j][0] - 1
                break

        # Body is everything after the heading line up to end
        body_lines = lines[idx + 1 : end_idx + 1]
        body = "\n".join(body_lines)

        sections.append(Section(
            heading=text,
            level=level,
            start_line=idx + 1,  # 1-indexed
            end_line=end_idx + 1,  # 1-indexed
            body=body,
        ))

    return sections


def find_section(content: str, heading: str) -> list[Section]:
    """Find sections matching heading (case-insensitive substring match)."""
    heading_lower = heading.lower()
    return [
        s for s in parse_sections(content)
        if heading_lower in s.heading.lower()
    ]


def replace_section_content(content: str, section: Section, new_body: str) -> str:
    """Replace a section's body, keeping the heading line intact."""
    lines = content.split("\n")
    heading_line = lines[section.start_line - 1]
    new_lines = (
        lines[: section.start_line - 1]
        + [heading_line]
        + new_body.split("\n")
        + lines[section.end_line:]
    )
    return "\n".join(new_lines)


def insert_after_line(content: str, line_number: int, new_text: str) -> str:
    """Insert new_text after the given 1-indexed line number."""
    lines = content.split("\n")
    new_lines = (
        lines[:line_number]
        + new_text.split("\n")
        + lines[line_number:]
    )
    return "\n".join(new_lines)


def delete_line_range(content: str, start: int, end: int) -> str:
    """Delete lines from start to end (1-indexed, inclusive)."""
    lines = content.split("\n")
    new_lines = lines[: start - 1] + lines[end:]
    return "\n".join(new_lines)


def get_outline(content: str) -> list[tuple[int, int, str]]:
    """Return list of (line_number_1indexed, level, heading_text)."""
    lines = content.split("\n")
    result: list[tuple[int, int, str]] = []
    for idx, line in enumerate(lines):
        info = _heading_info(line)
        if info and not _is_in_code_fence(lines, idx):
            result.append((idx + 1, info[0], info[1]))
    return result
