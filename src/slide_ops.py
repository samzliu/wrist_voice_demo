"""Pure HTML slide deck parsing and manipulation helpers."""

from __future__ import annotations

import re
from dataclasses import dataclass

# Regex to match <section class="slide" ...>...</section> blocks.
# Uses a non-greedy match on content between opening and closing tags.
_SLIDE_RE = re.compile(
    r'(<section\s+class="slide"[^>]*>[\s\S]*?</section>)',
    re.IGNORECASE,
)

# Extract title from first heading (h1-h3) inside a slide.
_TITLE_RE = re.compile(r"<h[1-3][^>]*>(.*?)</h[1-3]>", re.IGNORECASE | re.DOTALL)


@dataclass
class Slide:
    index: int  # 0-based position in the deck
    html: str  # full <section class="slide">...</section> string
    title: str  # extracted from first heading, or ""


def extract_title(section_html: str) -> str:
    """Extract the title text from the first h1-h3 in a slide section."""
    m = _TITLE_RE.search(section_html)
    if m:
        # Strip any inner HTML tags from the title text
        return re.sub(r"<[^>]+>", "", m.group(1)).strip()
    return ""


def parse_slides(deck_html: str) -> list[Slide]:
    """Parse all slides from a deck HTML string."""
    matches = _SLIDE_RE.findall(deck_html)
    return [
        Slide(index=i, html=html, title=extract_title(html))
        for i, html in enumerate(matches)
    ]


def get_slide(deck_html: str, index: int) -> Slide | None:
    """Get a single slide by 0-based index."""
    slides = parse_slides(deck_html)
    if 0 <= index < len(slides):
        return slides[index]
    return None


def get_slide_count(deck_html: str) -> int:
    """Count the number of slides in the deck."""
    return len(_SLIDE_RE.findall(deck_html))


def get_outline(deck_html: str) -> list[tuple[int, str]]:
    """Return a list of (1-indexed number, title) for all slides."""
    slides = parse_slides(deck_html)
    return [(s.index + 1, s.title) for s in slides]


def replace_slide(deck_html: str, index: int, new_section_html: str) -> str:
    """Replace the slide at the given 0-based index with new HTML."""
    matches = list(_SLIDE_RE.finditer(deck_html))
    if index < 0 or index >= len(matches):
        raise IndexError(f"Slide index {index} out of range (deck has {len(matches)} slides)")
    m = matches[index]
    return deck_html[: m.start()] + new_section_html + deck_html[m.end() :]


def insert_slide(deck_html: str, new_section_html: str, position: int | None = None) -> str:
    """Insert a new slide at the given position (0-based). None = append at end."""
    matches = list(_SLIDE_RE.finditer(deck_html))

    if position is None or position >= len(matches):
        # Append after the last slide
        if matches:
            last = matches[-1]
            insert_point = last.end()
        else:
            # No slides yet — insert before closing </div> of .deck
            deck_close = deck_html.rfind("</div>")
            insert_point = deck_close if deck_close != -1 else len(deck_html)
        return deck_html[:insert_point] + "\n\n    " + new_section_html + "\n" + deck_html[insert_point:]
    else:
        # Insert before the slide at `position`
        m = matches[position]
        return deck_html[: m.start()] + new_section_html + "\n\n    " + deck_html[m.start() :]


def delete_slide(deck_html: str, index: int) -> str:
    """Delete the slide at the given 0-based index."""
    matches = list(_SLIDE_RE.finditer(deck_html))
    if index < 0 or index >= len(matches):
        raise IndexError(f"Slide index {index} out of range (deck has {len(matches)} slides)")
    m = matches[index]
    # Also remove surrounding whitespace
    start = m.start()
    end = m.end()
    # Trim leading whitespace on the same line
    while start > 0 and deck_html[start - 1] in " \t":
        start -= 1
    # Trim one trailing newline
    while end < len(deck_html) and deck_html[end] in "\n\r":
        end += 1
    return deck_html[:start] + deck_html[end:]
