"""HTML slide deck parsing and manipulation."""

from __future__ import annotations

import re

SLIDE_PATTERN = re.compile(
    r"(<section\s+class=\"slide\"[^>]*>)([\s\S]*?)(</section>)",
    re.IGNORECASE,
)

HEADING_PATTERN = re.compile(r"<h[12][^>]*>(.*?)</h[12]>", re.IGNORECASE)
TAG_STRIP = re.compile(r"<[^>]+>")

EMPTY_DECK = """\
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>Presentation</title>
  <style>
    .deck { width: 960px; margin: 0 auto; }
    .slide { width: 960px; height: 540px; padding: 40px; box-sizing: border-box; display: flex; flex-direction: column; }
  </style>
</head>
<body>
  <div class="deck">
  </div>
</body>
</html>
"""


def parse_slides(html: str) -> list[str]:
    """Extract individual slide HTML blocks from a deck."""
    return [m.group(0) for m in SLIDE_PATTERN.finditer(html)]


def get_slide_title(slide_html: str) -> str:
    """Extract the first h1/h2 text from a slide."""
    m = HEADING_PATTERN.search(slide_html)
    if m:
        return TAG_STRIP.sub("", m.group(1)).strip()
    return "Untitled"


def get_slide(html: str, index: int) -> str | None:
    """Get a single slide by 0-based index."""
    slides = parse_slides(html)
    if 0 <= index < len(slides):
        return slides[index]
    return None


def replace_slide(html: str, index: int, new_content: str) -> str:
    """Replace a slide's inner content (between <section> tags) at the given index."""
    matches = list(SLIDE_PATTERN.finditer(html))
    if index < 0 or index >= len(matches):
        raise IndexError(f"Slide index {index} out of range (have {len(matches)})")
    m = matches[index]
    new_slide = f'{m.group(1)}{new_content}{m.group(3)}'
    return html[: m.start()] + new_slide + html[m.end() :]


def insert_slide(html: str, content: str, position: int = -1) -> str:
    """Insert a new slide at position (-1 = append)."""
    new_section = f'<section class="slide" style="padding: 40px; display: flex; flex-direction: column;">{content}</section>'
    matches = list(SLIDE_PATTERN.finditer(html))

    if not matches:
        # No slides yet — insert before </div> of deck
        insert_at = html.rfind("</div>")
        if insert_at == -1:
            return html + "\n" + new_section
        return html[:insert_at] + "  " + new_section + "\n" + html[insert_at:]

    if position < 0 or position >= len(matches):
        # Append after last slide
        last = matches[-1]
        return html[: last.end()] + "\n" + new_section + html[last.end() :]
    else:
        target = matches[position]
        return html[: target.start()] + new_section + "\n" + html[target.start() :]


def delete_slide(html: str, index: int) -> str:
    """Remove a slide at the given index."""
    matches = list(SLIDE_PATTERN.finditer(html))
    if index < 0 or index >= len(matches):
        raise IndexError(f"Slide index {index} out of range (have {len(matches)})")
    m = matches[index]
    # Also remove trailing whitespace/newline
    end = m.end()
    if end < len(html) and html[end] == "\n":
        end += 1
    return html[: m.start()] + html[end:]


def slide_summary(html: str) -> list[dict]:
    """Return a list of {index, title} for all slides."""
    slides = parse_slides(html)
    return [{"index": i, "title": get_slide_title(s)} for i, s in enumerate(slides)]
