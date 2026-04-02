"""Exa search API wrapper."""

from __future__ import annotations

import logging
import os

logger = logging.getLogger(__name__)

_client = None


def _get_client():
    global _client
    if _client is None:
        from exa_py import Exa

        api_key = os.environ.get("EXA_API_KEY", "")
        if not api_key:
            raise RuntimeError("EXA_API_KEY not set")
        _client = Exa(api_key=api_key)
    return _client


def web_search(query: str, num_results: int = 5) -> list[dict]:
    """Search the web using Exa. Returns list of {title, url, snippet}."""
    try:
        client = _get_client()
        results = client.search(query, num_results=num_results, use_autoprompt=True)
        return [
            {
                "title": r.title or "",
                "url": r.url,
                "snippet": getattr(r, "text", "")[:300] if hasattr(r, "text") else "",
                "score": getattr(r, "score", None),
            }
            for r in results.results
        ]
    except Exception as e:
        logger.error("Exa search failed: %s", e)
        return [{"title": "Error", "url": "", "snippet": str(e)}]


def deep_research(query: str, num_results: int = 10) -> list[dict]:
    """Deep research using Exa with full content. Returns list of {title, url, snippet, content}."""
    try:
        client = _get_client()
        results = client.search_and_contents(
            query,
            num_results=num_results,
            text=True,
            use_autoprompt=True,
        )
        return [
            {
                "title": r.title or "",
                "url": r.url,
                "snippet": (r.text or "")[:300],
                "content": (r.text or "")[:5000],
            }
            for r in results.results
        ]
    except Exception as e:
        logger.error("Exa deep research failed: %s", e)
        return [{"title": "Error", "url": "", "snippet": str(e), "content": str(e)}]
