"""Entry point for the Wrist voice-controlled markdown editor."""

from __future__ import annotations

import os
import sys

from dotenv import load_dotenv
from livekit.agents import AgentServer, AgentSession, JobContext, cli
from livekit.agents.inference.tts import TTS, ElevenlabsOptions
from livekit.plugins.anthropic import LLM
from livekit.plugins.turn_detector.multilingual import MultilingualModel

from .editor_agent import MarkdownEditorAgent

load_dotenv(".env.local")

WORKSPACE_DIR = os.environ.get("WRIST_WORKSPACE_DIR", os.path.expanduser("~/markdown"))

server = AgentServer()


@server.rtc_session()
async def entrypoint(ctx: JobContext):
    editor = MarkdownEditorAgent(workspace_dir=WORKSPACE_DIR)

    session = AgentSession(
        stt="deepgram/nova-3:en",
        llm=LLM(model="claude-haiku-4-5-20251001"),
        tts=TTS(
            "elevenlabs/eleven_flash_v2_5",
            voice="cgSgspJ2msm6clMCkdW9",  # Jessica
            extra_kwargs=ElevenlabsOptions(speed=1.0),
        ),
        turn_detection=MultilingualModel(unlikely_threshold=0.4),
    )

    editor.set_room(ctx.room)
    await session.start(agent=editor, room=ctx.room)


if __name__ == "__main__":
    # Check for --text flag to fall back to built-in text console
    if "--text" in sys.argv:
        sys.argv.remove("--text")
        # Ensure we route through the built-in console in text mode
        if "console" not in sys.argv:
            sys.argv.insert(1, "console")
        sys.argv.append("--text")
        cli.run_app(server)
    elif len(sys.argv) > 1 and sys.argv[1] == "console":
        # Custom voice console with push-to-talk
        from .console import run_voice_console

        input_device = None
        if "--input-device" in sys.argv:
            idx = sys.argv.index("--input-device")
            if idx + 1 < len(sys.argv):
                input_device = sys.argv[idx + 1]

        run_voice_console(server, input_device=input_device)
    else:
        # Non-console commands (start, dev, etc.) use built-in CLI
        cli.run_app(server)
