"""Custom voice console: mic in with push-to-talk, text out to terminal."""

from __future__ import annotations

import logging
import signal
import threading
import time
from types import FrameType

from livekit.agents import AgentServer, llm
from livekit.agents.cli.cli import (
    AgentsConsole,
    _configure_logger,
    _ConsoleWorker,
    _ExitCli,
    HANDLED_SIGNALS,
)
from livekit.agents.cli.readchar import readkey
from rich.text import Text

logger = logging.getLogger(__name__)


def run_voice_console(
    server: AgentServer,
    *,
    input_device: str | None = None,
    log_level: int | str = logging.DEBUG,
) -> None:
    """Run the custom voice console: mic in with push-to-talk, text out."""
    c = AgentsConsole.get_instance()
    c.console_mode = "audio"
    c.enabled = True

    _configure_logger(c, log_level)
    c.print("Starting voice console (push-to-talk)", tag="Wrist")

    try:
        c._validate_device_or_raise(input_device=input_device, output_device=None)

        exit_triggered = False

        def _on_worker_shutdown() -> None:
            try:
                signal.raise_signal(signal.SIGTERM)
            except Exception:
                try:
                    signal.raise_signal(signal.SIGINT)
                except Exception:
                    pass

        def _handle_exit(sig: int, frame: FrameType | None) -> None:
            nonlocal exit_triggered
            if not exit_triggered:
                exit_triggered = True
                raise _ExitCli()
            worker.shutdown()

        for sig in HANDLED_SIGNALS:
            signal.signal(sig, _handle_exit)

        worker = _ConsoleWorker(server=server, shutdown_cb=_on_worker_shutdown)
        worker.start()

        try:
            c.wait_for_io_acquisition()
            session = c.io_session

            # Enable microphone and speaker hardware
            c.set_microphone_enabled(True, device=input_device)
            c.set_speaker_enabled(True)

            # Start muted (push-to-talk default)
            c.io_loop.call_soon_threadsafe(session.input.set_audio_enabled, False)

            # Register event handler to print conversation text to terminal
            _register_text_display(c, session)

            # Push-to-talk state
            mic_on = False

            _print_mic_status(c, mic_on)

            def _listen_for_keys() -> None:
                nonlocal mic_on
                last_toggle_time = 0.0
                while not exit_triggered:
                    try:
                        ch = readkey()
                    except KeyboardInterrupt:
                        return
                    if ch == "\t":
                        now = time.monotonic()
                        if now - last_toggle_time < 0.5:
                            continue  # suppress key-repeat from holding Tab
                        last_toggle_time = now
                        mic_on = not mic_on
                        c.io_loop.call_soon_threadsafe(
                            session.input.set_audio_enabled, mic_on
                        )
                        _print_mic_status(c, mic_on)

            listener = threading.Thread(target=_listen_for_keys, daemon=True)
            listener.start()

            # Block until exit
            while not exit_triggered:
                time.sleep(0.1)

        except _ExitCli:
            pass
        finally:
            c.set_microphone_enabled(False)
            c.set_speaker_enabled(False)
            worker.shutdown()
            worker.join()

    except (Exception, SystemExit) as e:
        if not isinstance(e, (_ExitCli, SystemExit)):
            c.print(f"[error]{e}")
        raise


def _print_mic_status(c: AgentsConsole, mic_on: bool) -> None:
    """Print current mic status to console."""
    if mic_on:
        c.console.print(Text.assemble(
            ("\n  LISTENING...", "bold green"),
        ))
    else:
        c.console.print(Text.assemble(
            ("\n  MUTED", "bold red"),
            ("  [press Tab to talk]", "dim"),
        ))


def _register_text_display(c: AgentsConsole, session: object) -> None:
    """Register event handlers to print conversation to terminal."""
    from livekit.agents.voice.events import ConversationItemAddedEvent

    @session.on("conversation_item_added")  # type: ignore[union-attr]
    def _on_item(event: ConversationItemAddedEvent) -> None:
        if not isinstance(event.item, llm.ChatMessage):
            return

        if event.item.role == "user" and event.item.text_content:
            c.console.print()
            c.console.print(Text.assemble(
                ("  \u25cf ", "#1FD5F9"),
                ("You", "bold #1FD5F9"),
            ))
            for line in event.item.text_content.split("\n"):
                c.console.print(Text(f"    {line}"))

        elif event.item.role == "assistant" and event.item.text_content:
            c.console.print()
            c.console.print(Text.assemble(
                ("  \u25cf ", "#6BCB77"),
                ("Agent", "bold #6BCB77"),
            ))
            for line in event.item.text_content.split("\n"):
                c.console.print(Text(f"    {line}"))
