"""Monkey-patches for LiveKit's turn detection pipeline.

Extends LiveKit's dynamic endpointing with:
1. Continuous delay interpolation (replaces binary gate)
2. Third EMA for user response latency (anchors the midpoint)
3. Weighted Flux + ONNX EOU signal
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
from typing import Any

from livekit.agents import llm, utils
from livekit.agents.utils.exp_filter import ExpFilter
from livekit.agents.voice import audio_recognition
from livekit.agents.voice.endpointing import DynamicEndpointing

from .flux_stt import FluxSTT

logger = logging.getLogger(__name__)

# Weight for combining Flux EOT confidence with ONNX EOU probability
FLUX_WEIGHT = 0.9
ONNX_WEIGHT = 0.1

# Auto-monologue detection thresholds
MONOLOGUE_PAUSE_COUNT = 3  # after this many mid-turn pauses, extend patience
MONOLOGUE_WORD_COUNT = 40  # or after this many words without agent responding


def apply_turn_patches(flux_stt: FluxSTT | None = None) -> None:
    """Apply all turn detection patches. Call once at startup.

    Args:
        flux_stt: FluxSTT instance to read end_of_turn_confidence from.
                  If None, only ONNX EOU probability is used.
    """
    _patch_dynamic_endpointing()
    _patch_eou_gate(flux_stt)
    logger.info("turn_patches_applied")


def _patch_dynamic_endpointing() -> None:
    """Add response_latency EMA to DynamicEndpointing."""

    original_init = DynamicEndpointing.__init__

    def patched_init(self: Any, min_delay: float, max_delay: float, alpha: float = 0.9) -> None:
        original_init(self, min_delay=min_delay, max_delay=max_delay, alpha=alpha)
        # Third EMA: user's response latency to agent speech
        self._response_latency = ExpFilter(
            alpha=alpha,
            initial=1.0,  # reasonable default before data
            min_val=min_delay,
            max_val=max_delay,
        )

    DynamicEndpointing.__init__ = patched_init  # type: ignore[assignment]

    # Add response_latency property
    @property  # type: ignore[misc]
    def response_latency(self: Any) -> float:
        val = self._response_latency.value
        return val if val is not None else 1.0

    DynamicEndpointing.response_latency = response_latency  # type: ignore[attr-defined]

    # Patch on_start_of_speech to update response latency EMA
    original_on_start = DynamicEndpointing.on_start_of_speech

    def patched_on_start(self: Any, started_at: float, overlapping: bool = False) -> None:
        # If agent just finished speaking, capture user's response latency
        if (
            hasattr(self, "_agent_speech_ended_at")
            and self._agent_speech_ended_at is not None
            and not overlapping
            and hasattr(self, "_agent_speech_started_at")
            and self._agent_speech_started_at is not None
            and self._agent_speech_ended_at > self._agent_speech_started_at
        ):
            latency = started_at - self._agent_speech_ended_at
            if 0.05 < latency < 10.0:
                prev = self.response_latency
                self._response_latency.apply(1.0, latency)
                logger.debug(
                    "response_latency updated: %.3f -> %.3f (observed: %.3f)",
                    prev,
                    self.response_latency,
                    latency,
                )

        original_on_start(self, started_at, overlapping)

    DynamicEndpointing.on_start_of_speech = patched_on_start  # type: ignore[assignment]


def _patch_eou_gate(flux_stt: FluxSTT | None) -> None:
    """Replace the binary EOU gate with continuous interpolation."""

    original_run_eou = audio_recognition.AudioRecognition._run_eou_detection

    def patched_run_eou(
        self: Any, chat_ctx: llm.ChatContext, skip_reply: bool = False
    ) -> None:
        """Patched _run_eou_detection with continuous delay interpolation."""
        if self._stt and not self._audio_transcript and self._turn_detection_mode != "manual":
            return

        # Track pause count per turn for monologue detection
        if not hasattr(self, "_eou_pause_count"):
            self._eou_pause_count = 0
        self._eou_pause_count += 1

        chat_ctx = chat_ctx.copy()
        chat_ctx.add_message(role="user", content=self._audio_transcript)
        turn_detector = (
            self._turn_detector
            if self._audio_transcript and self._turn_detection_mode != "manual"
            else None
        )

        @utils.log_exceptions(logger=audio_recognition.logger)
        async def _bounce_eou_task(
            last_speaking_time: float | None = None,
            last_final_transcript_time: float | None = None,
            speech_start_time: float | None = None,
        ) -> None:
            # Get ONNX EOU probability
            onnx_eou: float = 0.5
            if turn_detector is not None:
                try:
                    if await turn_detector.supports_language(self._last_language):
                        onnx_eou = await turn_detector.predict_end_of_turn(chat_ctx)
                except Exception:
                    logger.debug("ONNX EOU prediction failed, using 0.5")

            # Get Flux EOT confidence
            flux_eot: float = onnx_eou  # fallback to ONNX if no Flux
            if flux_stt is not None:
                flux_eot = flux_stt.last_eot_confidence

            # Weighted combination
            combined_eou = FLUX_WEIGHT * flux_eot + ONNX_WEIGHT * onnx_eou

            # Continuous interpolation through 3 EMAs
            ep = self._endpointing
            min_d = ep.min_delay
            max_d = ep.max_delay
            mid_d = getattr(ep, "response_latency", (min_d + max_d) / 2)

            # Ensure ordering: min <= mid <= max
            mid_d = max(min_d, min(mid_d, max_d))

            if combined_eou >= 0.5:
                # Interpolate between response_latency and min_delay
                t = (combined_eou - 0.5) / 0.5
                endpointing_delay = mid_d + t * (min_d - mid_d)
            else:
                # Interpolate between max_delay and response_latency
                t = combined_eou / 0.5
                endpointing_delay = max_d + t * (mid_d - max_d)

            # Auto-monologue detection: if user has paused many times or
            # said many words, they're probably monologuing — use max_delay
            # to avoid interrupting their flow.
            word_count = len(self._audio_transcript.split()) if self._audio_transcript else 0
            is_monologue = (
                self._eou_pause_count >= MONOLOGUE_PAUSE_COUNT
                or word_count >= MONOLOGUE_WORD_COUNT
            )
            if is_monologue:
                endpointing_delay = max(endpointing_delay, max_d)

            logger.info(
                "turn_decision",
                extra={
                    "onnx_eou": round(onnx_eou, 3),
                    "flux_eot": round(flux_eot, 3),
                    "combined_eou": round(combined_eou, 3),
                    "delay": round(endpointing_delay, 3),
                    "min_delay": round(min_d, 3),
                    "mid_delay": round(mid_d, 3),
                    "max_delay": round(max_d, 3),
                    "pause_count": self._eou_pause_count,
                    "word_count": word_count,
                    "is_monologue": is_monologue,
                },
            )

            # Wait logic (same as original LiveKit code)
            extra_sleep = endpointing_delay
            if last_speaking_time:
                extra_sleep += last_speaking_time - time.time()

            if extra_sleep > 0:
                try:
                    await asyncio.wait_for(self._closing.wait(), timeout=extra_sleep)
                except asyncio.TimeoutError:
                    pass

            # Compute metrics
            confidence_avg = (
                sum(self._final_transcript_confidence) / len(self._final_transcript_confidence)
                if self._final_transcript_confidence
                else 0
            )

            started_speaking_at = None
            stopped_speaking_at = None
            transcription_delay = None
            end_of_turn_delay = None

            if (
                last_final_transcript_time is not None
                and last_speaking_time is not None
                and speech_start_time is not None
            ):
                started_speaking_at = speech_start_time
                stopped_speaking_at = last_speaking_time
                transcription_delay = max(last_final_transcript_time - last_speaking_time, 0)
                end_of_turn_delay = time.time() - last_speaking_time

            committed = self._hooks.on_end_of_turn(
                audio_recognition._EndOfTurnInfo(
                    skip_reply=skip_reply,
                    new_transcript=self._audio_transcript,
                    transcript_confidence=confidence_avg,
                    transcription_delay=transcription_delay or 0,
                    end_of_turn_delay=end_of_turn_delay or 0,
                    started_speaking_at=started_speaking_at,
                    stopped_speaking_at=stopped_speaking_at,
                )
            )

            if committed:
                self._eou_pause_count = 0  # reset for next turn
                if hasattr(self, "_end_of_turn_detected_count"):
                    self._end_of_turn_detected_count += 1

        # Cancel previous EOU task if running
        if self._end_of_turn_task is not None:
            if not self._end_of_turn_task.done():
                self._end_of_turn_task.cancel()

        self._end_of_turn_task = asyncio.create_task(
            _bounce_eou_task(
                last_speaking_time=self._last_speaking_time,
                last_final_transcript_time=self._last_final_transcript_time,
                speech_start_time=self._speech_start_time,
            )
        )

    audio_recognition.AudioRecognition._run_eou_detection = patched_run_eou  # type: ignore[assignment]
