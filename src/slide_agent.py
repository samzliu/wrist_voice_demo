"""SlideAgent with function tools for voice-controlled slide presentation and building."""

from __future__ import annotations

import json
from pathlib import Path

from livekit.agents import function_tool, Agent, RunContext

from . import slide_ops
from .deep_agent import run_deep_agent


SYSTEM_PROMPT = """\
You are the OpenClaw Onboarding Agent — a conversational guide that presents \
OpenClaw to new users and then helps them design their ideal agent setup. \
You control an HTML slide deck that the user sees on screen.

## How the conversation works

### Phase 1 — Introduction Presentation (start here)
IMPORTANT: Go through ALL 9 slides in one continuous flow without stopping or \
waiting for the user. Do NOT ask the user questions like "ready?" or "shall I \
continue?" — just keep going slide by slide. The user will interrupt you if \
they have a question — only then should you pause, answer, and resume.

The pattern for each slide is:
1. Call go_to_slide(N) to navigate to the slide
2. Speak the script for that slide
3. Then move on to the next slide

Start by calling go_to_slide(1), speak the script for slide 1, then call \
go_to_slide(2), speak the script for slide 2, and so on through all 9 slides. \
Always navigate FIRST, then speak. Use go_to_slide(N) for each slide rather \
than next_slide to ensure the numbering stays in sync.

#### Presentation Script

Slide 1 (Title):
"Welcome to OpenClaw! I'm going to walk you through what we do and how it \
works. It'll take about three minutes, and then we'll design your setup \
together. Let's dive in."

Slide 2 (The Problem):
"So here's the thing — AI agents are powerful, but getting them to actually \
work for you is genuinely hard. You end up with a bunch of disconnected tools, \
spending hours on setup, and nothing coordinates. Sound familiar?"

Slide 3 (What is OpenClaw):
"That's what OpenClaw solves. We build and host a swarm of AI agents — \
a team that works together on your behalf. Three simple steps: tell us what \
you need, we design the team, and they run for you around the clock."

Slide 4 (How It Works):
"The process starts with a conversation — exactly like the one we're having \
right now. You describe your workflow, what's painful, what you wish was \
automated. Then we design the right agents with the right tools. And we host \
everything — you don't need to manage any infrastructure."

Slide 5 (Bug Fixer Agent):
"Here's a concrete example. Say you're a startup founder. Someone posts a \
bug screenshot in Slack. The Bug Fixer agent picks it up, debugs the code, \
runs tests, and opens a pull request. You just review and merge."

Slide 6 (Knowledge Base Agent):
"Or imagine you read a lot — papers, tweets, bookmarks. The Knowledge Base \
agent ingests all of that and lets you query it anytime. Like having a \
research assistant with perfect memory."

Slide 7 (Personal CRM Agent):
"And here's one people love — a Personal CRM. It syncs your contacts, \
tracks your relationships, and drafts messages for you. But nothing sends \
without your approval. You're always in control."

Slide 8 (The Swarm):
"The real power is when agents work together. Agent A monitors something, \
triggers Agent B to act, and Agent C reports the results. Shared context, \
coordinated handoffs — that's the swarm."

Slide 9 (Getting Started):
"Alright, that's the overview! Now comes the fun part — let's figure out \
what would be most useful for you. I'll ask you a few questions, and then \
we'll build your setup right here as slides."

### Phase 2 — Discovery (transition after slide 9)
Ask about the user's needs in plain language:
- What kind of work do they do?
- What's taking up too much of their time?
- What tools do they already use?
- What would they automate if they could?
Keep it conversational — one question at a time. Listen for signals about \
whether they need a single agent or a multi-agent swarm.

### Phase 3 — Live Slide Creation
When you have enough context, start creating custom slides:
- Create a title slide for their setup (e.g. "Your OpenClaw Setup")
- Create a slide for each agent you recommend (name, role, tools, workflow)
- Create a workflow/architecture slide showing how agents interact
- Create an integrations overview slide
Use create_slide to add slides to the deck. Navigate to each new slide as \
you create it so the user can see it in real time. Tell the user what you're \
building as you go.

When creating slides, follow the HTML format exactly:
- Wrap in <section class="slide" style="padding: 48px 56px; display: flex; flex-direction: column; background: #0f172a;">
- Use inline CSS only. No CSS classes on content elements.
- Font: Arial, sans-serif
- Colors: #ffffff for headings, #e2e8f0 for body text, #94a3b8 for muted text, #3b82f6 for accent
- Background: #0f172a (matches the intro deck)
- Use semantic HTML (h2, p, ul, div) — no bare text

### Phase 4 — Refinement
Walk through the custom slides with the user. Ask if anything is missing or wrong.
Edit slides based on feedback using edit_slide. Adjust agent definitions, \
workflows, and integrations until the user is satisfied.

## Rules
- Be concise and natural. Short sentences. No corporate jargon.
- Do not use markdown formatting in your speech — speak naturally since the user \
is interacting by voice.
- One question at a time. Let the user talk.
- Always navigate to a slide before talking about it.
- When creating slides, match the visual style of the intro deck.
"""


class SlideAgent(Agent):
    def __init__(self, deck_path: str) -> None:
        super().__init__(
            instructions=SYSTEM_PROMPT,
        )
        self._deck_path = Path(deck_path).resolve()
        self._current_slide: int = 0  # 0-based internally

    def _read_deck(self) -> str:
        return self._deck_path.read_text(encoding="utf-8")

    def _write_deck(self, html: str) -> None:
        self._deck_path.write_text(html, encoding="utf-8")

    async def _send_to_frontend(self, context: RunContext, msg_type: str, payload: dict) -> None:
        """Publish a JSON data message to the frontend via LiveKit."""
        data = json.dumps({"type": msg_type, **payload})
        try:
            room = context.session.room_io.room
            await room.local_participant.publish_data(
                data.encode("utf-8"),
                reliable=True,
            )
        except RuntimeError:
            pass  # No room available (e.g. console mode)

    # ── Navigation tools ──────────────────────────────────────────

    @function_tool()
    async def go_to_slide(self, context: RunContext, slide_number: int) -> str:
        """Navigate to a specific slide.

        Args:
            slide_number: The slide number to go to (1-indexed).
        """
        deck = self._read_deck()
        count = slide_ops.get_slide_count(deck)
        if slide_number < 1 or slide_number > count:
            return f"Invalid slide number. Deck has {count} slides (1-{count})."
        self._current_slide = slide_number - 1
        await self._send_to_frontend(context, "go_to_slide", {"slide": slide_number})
        slide = slide_ops.get_slide(deck, self._current_slide)
        title = slide.title if slide else ""
        return f"Now on slide {slide_number}: {title}" if title else f"Now on slide {slide_number}."

    @function_tool()
    async def next_slide(self, context: RunContext) -> str:
        """Go to the next slide."""
        deck = self._read_deck()
        count = slide_ops.get_slide_count(deck)
        if self._current_slide >= count - 1:
            return f"Already on the last slide ({count})."
        self._current_slide += 1
        slide_number = self._current_slide + 1
        await self._send_to_frontend(context, "go_to_slide", {"slide": slide_number})
        slide = slide_ops.get_slide(deck, self._current_slide)
        title = slide.title if slide else ""
        return f"Now on slide {slide_number}: {title}" if title else f"Now on slide {slide_number}."

    @function_tool()
    async def prev_slide(self, context: RunContext) -> str:
        """Go to the previous slide."""
        if self._current_slide <= 0:
            return "Already on the first slide."
        self._current_slide -= 1
        slide_number = self._current_slide + 1
        await self._send_to_frontend(context, "go_to_slide", {"slide": slide_number})
        deck = self._read_deck()
        slide = slide_ops.get_slide(deck, self._current_slide)
        title = slide.title if slide else ""
        return f"Now on slide {slide_number}: {title}" if title else f"Now on slide {slide_number}."

    # ── Reading tools ─────────────────────────────────────────────

    @function_tool()
    async def get_current_slide(self, context: RunContext) -> str:
        """Get the current slide number and its HTML content."""
        deck = self._read_deck()
        slide = slide_ops.get_slide(deck, self._current_slide)
        if not slide:
            return "No slide loaded."
        return f"Slide {self._current_slide + 1}:\n{slide.html}"

    @function_tool()
    async def get_slide_count(self, context: RunContext) -> str:
        """Get the total number of slides in the deck."""
        deck = self._read_deck()
        count = slide_ops.get_slide_count(deck)
        return f"The deck has {count} slides."

    @function_tool()
    async def read_slide(self, context: RunContext, slide_number: int) -> str:
        """Read the HTML content of a specific slide.

        Args:
            slide_number: The slide number to read (1-indexed).
        """
        deck = self._read_deck()
        slide = slide_ops.get_slide(deck, slide_number - 1)
        if not slide:
            count = slide_ops.get_slide_count(deck)
            return f"Slide {slide_number} not found. Deck has {count} slides."
        return f"Slide {slide_number} ({slide.title}):\n{slide.html}"

    @function_tool()
    async def get_deck_outline(self, context: RunContext) -> str:
        """Get a numbered list of all slide titles in the deck."""
        deck = self._read_deck()
        outline = slide_ops.get_outline(deck)
        if not outline:
            return "Deck is empty."
        lines = [f"  {num}. {title or '(untitled)'}" for num, title in outline]
        return f"Deck outline ({len(outline)} slides):\n" + "\n".join(lines)

    # ── Editing tools ─────────────────────────────────────────────

    @function_tool()
    async def edit_slide(self, context: RunContext, slide_number: int, new_html: str) -> str:
        """Replace a slide's content with new HTML.

        Args:
            slide_number: The slide number to edit (1-indexed).
            new_html: The complete new HTML for the slide, including the <section class="slide"> wrapper.
        """
        deck = self._read_deck()
        count = slide_ops.get_slide_count(deck)
        if slide_number < 1 or slide_number > count:
            return f"Invalid slide number. Deck has {count} slides."
        try:
            new_deck = slide_ops.replace_slide(deck, slide_number - 1, new_html)
        except IndexError as e:
            return str(e)
        self._write_deck(new_deck)
        await self._send_to_frontend(context, "slide_updated", {
            "slide": slide_number,
            "html": new_html,
        })
        return f"Updated slide {slide_number}."

    @function_tool()
    async def create_slide(self, context: RunContext, html: str, after_slide: int = 0) -> str:
        """Add a new slide to the deck.

        Args:
            html: The complete HTML for the new slide, including the <section class="slide"> wrapper.
            after_slide: Insert after this slide number (1-indexed). 0 means append at the end.
        """
        deck = self._read_deck()
        if after_slide == 0:
            position = None  # append
        else:
            position = after_slide  # insert at this 0-based position (after after_slide)

        new_deck = slide_ops.insert_slide(deck, html, position)
        self._write_deck(new_deck)

        new_count = slide_ops.get_slide_count(new_deck)
        new_slide_num = after_slide + 1 if after_slide > 0 else new_count
        self._current_slide = new_slide_num - 1

        await self._send_to_frontend(context, "slide_created", {
            "position": new_slide_num,
            "html": html,
        })
        await self._send_to_frontend(context, "go_to_slide", {"slide": new_slide_num})
        return f"Created slide {new_slide_num}. Deck now has {new_count} slides."

    @function_tool()
    async def delete_slide(self, context: RunContext, slide_number: int) -> str:
        """Delete a slide from the deck.

        Args:
            slide_number: The slide number to delete (1-indexed).
        """
        deck = self._read_deck()
        count = slide_ops.get_slide_count(deck)
        if slide_number < 1 or slide_number > count:
            return f"Invalid slide number. Deck has {count} slides."
        try:
            new_deck = slide_ops.delete_slide(deck, slide_number - 1)
        except IndexError as e:
            return str(e)
        self._write_deck(new_deck)
        new_count = slide_ops.get_slide_count(new_deck)
        # Adjust current slide if needed
        if self._current_slide >= new_count:
            self._current_slide = max(0, new_count - 1)
        await self._send_to_frontend(context, "slide_deleted", {"slide": slide_number})
        return f"Deleted slide {slide_number}. Deck now has {new_count} slides."

    # ── Deep thinking ─────────────────────────────────────────────

    @function_tool()
    async def deep_think(self, context: RunContext, task: str) -> str:
        """Delegate a complex task to a more capable agent with full file access.

        Use for multi-step work: creating multiple slides at once, restructuring
        the deck, or tasks requiring planning and iteration.

        Args:
            task: Detailed description of what needs to be done.
        """
        return await run_deep_agent(task, self._deck_path.parent)
