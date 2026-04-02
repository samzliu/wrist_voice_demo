"""URL fetching and text extraction."""

from __future__ import annotations

import html.parser
import logging
import re

import httpx

logger = logging.getLogger(__name__)

_TIMEOUT = 15.0
_MAX_CONTENT_LENGTH = 10_000


class _TextExtractor(html.parser.HTMLParser):
    """Simple HTML to text extractor."""

    def __init__(self):
        super().__init__()
        self._text: list[str] = []
        self._skip = False
        self._skip_tags = {"script", "style", "noscript", "svg"}

    def handle_starttag(self, tag, attrs):
        if tag in self._skip_tags:
            self._skip = True

    def handle_endtag(self, tag):
        if tag in self._skip_tags:
            self._skip = False

    def handle_data(self, data):
        if not self._skip:
            text = data.strip()
            if text:
                self._text.append(text)

    def get_text(self) -> str:
        return "\n".join(self._text)


def _extract_title(html_content: str) -> str:
    """Extract <title> from HTML."""
    m = re.search(r"<title[^>]*>(.*?)</title>", html_content, re.IGNORECASE | re.DOTALL)
    return m.group(1).strip() if m else ""


def _html_to_text(html_content: str) -> str:
    """Convert HTML to plain text."""
    extractor = _TextExtractor()
    try:
        extractor.feed(html_content)
    except Exception:
        pass
    return extractor.get_text()


async def fetch_url(url: str) -> dict:
    """Fetch a URL and return {url, title, content}.

    Content is plain text extracted from HTML, truncated to ~10k chars.
    """
    try:
        async with httpx.AsyncClient(
            follow_redirects=True, timeout=_TIMEOUT
        ) as client:
            resp = await client.get(url, headers={"User-Agent": "Wrist/1.0"})
            resp.raise_for_status()

            content_type = resp.headers.get("content-type", "")
            raw = resp.text

            if "text/html" in content_type:
                title = _extract_title(raw)
                text = _html_to_text(raw)
            else:
                title = ""
                text = raw

            return {
                "url": url,
                "title": title,
                "content": text[:_MAX_CONTENT_LENGTH],
            }
    except Exception as e:
        logger.error("Failed to fetch %s: %s", url, e)
        return {
            "url": url,
            "title": "Error",
            "content": f"Failed to fetch: {e}",
        }
