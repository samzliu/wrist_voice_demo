"""Bayesian turn detection manager with continuous monitoring.

Uses two competing metalog distributions (mid-turn vs between-turn pauses)
combined with the ONNX EOU model via log-odds to continuously estimate
P(turn_over) during silence. Commits the turn when this crosses a
cost-sensitive threshold.
"""

from __future__ import annotations

import asyncio
import enum
import logging
import math
import time

from livekit.agents import AgentSession
from livekit.plugins.turn_detector.multilingual import MultilingualModel

from .metalog import (
    BETWEEN_TURN_PRIOR,
    MID_TURN_PRIOR,
    AdaptiveMetalog,
    logit,
    sigmoid,
)

logger = logging.getLogger(__name__)

# Polling interval for the continuous monitoring loop
POLL_INTERVAL = 0.05  # 50ms


class TurnState(enum.Enum):
    IDLE = "idle"
    USER_SPEAKING = "user_speaking"
    WAITING = "waiting"
    COMMITTING = "committing"
    AGENT_RESPONDING = "agent_responding"
    MONITORING_FP = "monitoring_fp"
    YIELDED = "yielded"


class MetalogTurnManager:
    """Bayesian turn detection using competing metalog distributions.

    Maintains two distributions:
    - M_mid: mid-turn pause durations (user paused but resumed)
    - M_between: between-turn pause durations (actual turn boundaries)

    During silence, continuously computes P(turn_over) from:
    - Hazard ratio h_between(t) / h_mid(t)  (duration signal)
    - EOU model logit                         (semantic signal)
    - Learned bias term                       (base rate)

    Commits the turn when P(turn_over) > tau (cost-sensitive threshold).
    """

    def __init__(
        self,
        session: AgentSession,
        eou_model: MultilingualModel,
        *,
        # Log-odds weights (phase 1: fixed naive Bayes; phase 2: learned)
        w_duration: float = 1.0,
        w_eou: float = 1.0,
        bias: float = 0.0,
        # Cost-sensitive threshold: tau = c_interrupt / (c_interrupt + c_latency)
        c_interrupt: float = 5.0,
        c_latency: float = 1.0,
        # False positive detection
        fp_detection_window: float = 0.8,
        fp_imputation_multiple: float = 1.5,
        fp_imputation_weight: float = 0.5,
        # Safety
        max_silence: float = 30.0,
    ) -> None:
        self._session = session
        self._eou_model = eou_model

        # Two competing distributions
        self._metalog_mid = AdaptiveMetalog(MID_TURN_PRIOR)
        self._metalog_between = AdaptiveMetalog(BETWEEN_TURN_PRIOR)

        # Log-odds weights
        self._w_duration = w_duration
        self._w_eou = w_eou
        self._bias = bias

        # Threshold from cost ratio
        self._tau = c_interrupt / (c_interrupt + c_latency)
        self._c_interrupt = c_interrupt
        self._c_latency = c_latency

        # False positive config
        self._fp_detection_window = fp_detection_window
        self._fp_imputation_multiple = fp_imputation_multiple
        self._fp_imputation_weight = fp_imputation_weight

        self._max_silence = max_silence

        # State machine
        self._state = TurnState.IDLE

        # Timing bookkeeping
        self._speech_start_time: float | None = None
        self._vad_end_time: float | None = None
        self._agent_speak_start: float | None = None
        self._last_commit_silence_duration: float = 0.0

        # EOU probability (computed once per silence onset)
        self._eou_prob: float = 0.5

        # Transcript tracking
        self._current_transcript = ""
        self._current_word_count = 0
        self._mid_turn_pause_count = 0

        # Async tasks
        self._monitor_task: asyncio.Task[None] | None = None
        self._fp_task: asyncio.Task[None] | None = None

        # Patience modifiers (from agent tool calls)
        self._patience_bias: float = 0.0  # added to bias during monitoring
        self._patience_until_commit = False  # if True, resets after next commit

        # FP tracking for tau adaptation
        self._recent_outcomes: list[bool] = []  # True = TP, False = FP
        self._max_outcome_window = 20

        # Register event handlers
        session.on("user_state_changed", self._on_user_state_changed)
        session.on("agent_state_changed", self._on_agent_state_changed)
        session.on("user_input_transcribed", self._on_user_input_transcribed)

        logger.info(
            "metalog_turn_manager_init",
            extra={
                "tau": round(self._tau, 3),
                "w_duration": w_duration,
                "w_eou": w_eou,
                "bias": bias,
                "fp_detection_window": fp_detection_window,
            },
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def yield_turn(self, patience: float | None = None) -> None:
        """Adjust turn-taking patience.

        Args:
            patience: How much to shift the decision threshold.
                None = yield indefinitely (wait for user, no timeout).
                A float value adds a negative bias to log-odds, making
                it harder to cross tau. Reasonable range: 1.0 (a bit
                more patient) to 5.0 (very patient). The bias resets
                after the next committed turn.
        """
        if patience is None:
            # Full yield: disable monitoring entirely
            self._state = TurnState.YIELDED
            self._cancel_monitor_task()
            self._patience_bias = 0.0
            self._patience_until_commit = False
            logger.info("metalog_yield_turn", extra={"mode": "indefinite"})
        else:
            # Patience mode: shift bias to make crossing tau harder
            self._patience_bias = -abs(patience)
            self._patience_until_commit = True
            logger.info(
                "metalog_yield_turn",
                extra={"mode": "patient", "patience_bias": self._patience_bias},
            )

    # ------------------------------------------------------------------
    # Event handlers
    # ------------------------------------------------------------------

    async def _on_user_state_changed(self, ev: object) -> None:
        new_state = getattr(ev, "new_state", None)
        old_state = getattr(ev, "old_state", None)

        if new_state == "speaking":
            await self._on_user_started_speaking()
        elif old_state == "speaking" and new_state == "listening":
            await self._on_user_stopped_speaking()

    async def _on_agent_state_changed(self, ev: object) -> None:
        new_state = getattr(ev, "new_state", None)

        if new_state == "speaking":
            self._agent_speak_start = time.time()
            if self._state == TurnState.COMMITTING:
                self._state = TurnState.AGENT_RESPONDING
                self._start_fp_monitor()
        elif new_state in ("idle", "listening"):
            if self._state == TurnState.AGENT_RESPONDING:
                self._state = TurnState.IDLE
            elif self._state == TurnState.MONITORING_FP:
                # Agent finished speaking during FP window — let the FP task handle it
                pass

    async def _on_user_input_transcribed(self, ev: object) -> None:
        transcript = getattr(ev, "transcript", "")
        is_final = getattr(ev, "is_final", False)
        if is_final and transcript:
            self._current_transcript = transcript
            self._current_word_count = len(transcript.split())

    # ------------------------------------------------------------------
    # State machine transitions
    # ------------------------------------------------------------------

    async def _on_user_started_speaking(self) -> None:
        now = time.time()

        if self._state == TurnState.WAITING:
            # Mid-turn pause: user resumed before we committed
            pause_duration = now - (self._vad_end_time or now)
            self._cancel_monitor_task()
            self._mid_turn_pause_count += 1

            # This is a fully observed mid-turn pause — add to M_mid
            if pause_duration > 0.05:
                self._metalog_mid.add_observation(pause_duration)

            logger.info(
                "metalog_mid_turn_pause",
                extra={
                    "pause_duration": round(pause_duration, 3),
                    "pause_count": self._mid_turn_pause_count,
                    "mid_obs_count": self._metalog_mid.observation_count,
                },
            )

        elif self._state == TurnState.MONITORING_FP:
            # User re-entered while we're monitoring for false positive
            self._cancel_fp_task()
            gap = now - (self._agent_speak_start or now)
            if gap < self._fp_detection_window:
                self._handle_false_positive(gap)

        elif self._state == TurnState.YIELDED:
            self._yielded = False
            logger.info("metalog_yield_resumed")

        # Transition to speaking
        self._state = TurnState.USER_SPEAKING
        if self._speech_start_time is None:
            self._speech_start_time = now
            self._current_transcript = ""
            self._current_word_count = 0
            self._mid_turn_pause_count = 0

    async def _on_user_stopped_speaking(self) -> None:
        if self._state != TurnState.USER_SPEAKING:
            return

        self._vad_end_time = time.time()

        # Get EOU probability (computed once, used throughout silence)
        self._eou_prob = await self._get_eou_prob()

        logger.info(
            "metalog_silence_start",
            extra={
                "eou_prob": round(self._eou_prob, 3),
                "word_count": self._current_word_count,
                "transcript_preview": self._current_transcript[:80],
            },
        )

        # Start continuous monitoring loop
        self._state = TurnState.WAITING
        self._monitor_task = asyncio.create_task(self._silence_monitor_loop())

    # ------------------------------------------------------------------
    # Continuous monitoring loop
    # ------------------------------------------------------------------

    async def _silence_monitor_loop(self) -> None:
        """Poll every 50ms during silence, computing P(turn_over).

        Combines the hazard ratio from the two metalog distributions
        with the EOU model's probability via log-odds. Commits the
        turn when P(turn_over) crosses threshold tau.
        """
        assert self._vad_end_time is not None

        while self._state == TurnState.WAITING:
            t = time.time() - self._vad_end_time

            # Safety cap
            if t > self._max_silence:
                logger.info("metalog_max_silence_reached", extra={"t": round(t, 2)})
                await self._commit_turn(t)
                return

            # Duration signal: hazard ratio
            h_mid = self._metalog_mid.hazard(t)
            h_between = self._metalog_between.hazard(t)
            lr = h_between / max(h_mid, 1e-10)

            # Combine in log-odds
            log_lr = math.log(max(lr, 1e-10))
            log_odds = (
                self._w_duration * log_lr
                + self._w_eou * logit(self._eou_prob)
                + self._bias
                + self._patience_bias
            )

            p_turn_over = sigmoid(log_odds)
            threshold = self._tau

            if p_turn_over > threshold:
                logger.info(
                    "metalog_turn_decision",
                    extra={
                        "t": round(t, 3),
                        "p_turn_over": round(p_turn_over, 3),
                        "threshold": round(threshold, 3),
                        "hazard_ratio": round(lr, 3),
                        "log_lr": round(log_lr, 3),
                        "eou_prob": round(self._eou_prob, 3),
                        "log_odds": round(log_odds, 3),
                        "word_count": self._current_word_count,
                        "mid_turn_pauses": self._mid_turn_pause_count,
                        "mid_obs": self._metalog_mid.observation_count,
                        "between_obs": self._metalog_between.observation_count,
                    },
                )
                await self._commit_turn(t)
                return

            try:
                await asyncio.sleep(POLL_INTERVAL)
            except asyncio.CancelledError:
                return

    async def _commit_turn(self, silence_duration: float) -> None:
        """Commit the user's turn and transition state."""
        self._state = TurnState.COMMITTING
        self._last_commit_silence_duration = silence_duration

        # Reset patience modifier after commit
        if self._patience_until_commit:
            self._patience_bias = 0.0
            self._patience_until_commit = False

        try:
            self._session.commit_user_turn()
        except Exception:
            logger.exception("Failed to commit user turn")
            self._state = TurnState.IDLE
            return

        # Reset speech tracking
        self._speech_start_time = None

    # ------------------------------------------------------------------
    # False positive detection
    # ------------------------------------------------------------------

    def _start_fp_monitor(self) -> None:
        self._state = TurnState.MONITORING_FP
        self._fp_task = asyncio.create_task(self._fp_window_expired())

    async def _fp_window_expired(self) -> None:
        """FP window expired — true positive confirmed."""
        try:
            await asyncio.sleep(self._fp_detection_window)
        except asyncio.CancelledError:
            return

        if self._state == TurnState.MONITORING_FP:
            self._handle_true_positive()
            self._state = TurnState.AGENT_RESPONDING

    def _handle_true_positive(self) -> None:
        """Turn committed correctly — update M_between."""
        duration = self._last_commit_silence_duration
        if duration > 0.05:
            self._metalog_between.add_observation(duration)

        self._recent_outcomes.append(True)
        if len(self._recent_outcomes) > self._max_outcome_window:
            self._recent_outcomes.pop(0)

        logger.info(
            "metalog_true_positive",
            extra={
                "silence_duration": round(duration, 3),
                "between_obs": self._metalog_between.observation_count,
                "tau": round(self._tau, 3),
            },
        )

    def _handle_false_positive(self, gap: float) -> None:
        """User re-entered shortly after agent spoke — update M_mid."""
        duration = self._last_commit_silence_duration

        # Right-censored observation: true mid-turn pause was > duration.
        # Impute at 1.5x with reduced weight.
        imputed = duration * self._fp_imputation_multiple
        self._metalog_mid.add_observation(imputed, weight=self._fp_imputation_weight)

        self._recent_outcomes.append(False)
        if len(self._recent_outcomes) > self._max_outcome_window:
            self._recent_outcomes.pop(0)

        # Adapt tau based on recent FP rate
        self._adapt_tau()

        logger.warning(
            "metalog_false_positive",
            extra={
                "silence_duration": round(duration, 3),
                "user_reentry_gap": round(gap, 3),
                "imputed_mid_turn": round(imputed, 3),
                "mid_obs": self._metalog_mid.observation_count,
                "tau": round(self._tau, 3),
            },
        )

    def _adapt_tau(self) -> None:
        """Adjust threshold based on recent false positive rate."""
        if len(self._recent_outcomes) < 5:
            return
        fp_count = sum(1 for x in self._recent_outcomes if not x)
        fp_rate = fp_count / len(self._recent_outcomes)

        # If FP rate is high, increase tau (be more cautious)
        # Recalculate from effective cost ratio
        if fp_rate > 0.15:
            self._c_interrupt = min(20.0, self._c_interrupt * 1.1)
        elif fp_rate < 0.05 and self._c_interrupt > 3.0:
            self._c_interrupt = max(3.0, self._c_interrupt * 0.95)

        self._tau = self._c_interrupt / (self._c_interrupt + self._c_latency)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    async def _get_eou_prob(self) -> float:
        """Call the ONNX EOU model for end-of-utterance probability."""
        try:
            chat_ctx = self._session.chat_ctx.copy()
            chat_ctx.add_message(role="user", content=self._current_transcript)
            prob = await self._eou_model.predict_end_of_turn(chat_ctx, timeout=3.0)
            return float(prob)
        except Exception:
            logger.warning("EOU prediction failed, defaulting to 0.5")
            return 0.5

    def _cancel_monitor_task(self) -> None:
        if self._monitor_task and not self._monitor_task.done():
            self._monitor_task.cancel()
        self._monitor_task = None

    def _cancel_fp_task(self) -> None:
        if self._fp_task and not self._fp_task.done():
            self._fp_task.cancel()
        self._fp_task = None
