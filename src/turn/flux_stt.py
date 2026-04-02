"""FluxSTT: captures Deepgram's end_of_turn_confidence that LiveKit drops."""

from __future__ import annotations

import logging
from typing import Any

from livekit.agents import APIConnectOptions, DEFAULT_API_CONNECT_OPTIONS
from livekit.agents.types import NOT_GIVEN, NotGivenOr
from livekit.plugins.deepgram import STTv2
from livekit.plugins.deepgram.stt_v2 import SpeechStreamv2

logger = logging.getLogger(__name__)


class FluxSTT(STTv2):
    """STTv2 wrapper that captures Flux's end_of_turn_confidence."""

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.last_eot_confidence: float = 0.0

    def stream(
        self,
        *,
        language: NotGivenOr[str] = NOT_GIVEN,
        conn_options: APIConnectOptions = DEFAULT_API_CONNECT_OPTIONS,
    ) -> FluxSpeechStream:
        stream = FluxSpeechStream(
            stt=self,
            conn_options=conn_options,
            opts=self._opts,
            api_key=self._api_key,
            http_session=self._ensure_session(),
            base_url=self._opts.endpoint_url,
        )
        self._streams.add(stream)
        return stream


class FluxSpeechStream(SpeechStreamv2):
    """SpeechStreamv2 that extracts end_of_turn_confidence from raw Deepgram data."""

    def _process_stream_event(self, data: dict) -> None:  # type: ignore[override]
        # Capture end_of_turn_confidence before parent processes the event
        if data.get("type") == "TurnInfo":
            eot_conf = data.get("end_of_turn_confidence")
            if eot_conf is not None:
                stt_instance = self._stt
                if isinstance(stt_instance, FluxSTT):
                    stt_instance.last_eot_confidence = float(eot_conf)

        # Let parent handle all the normal event processing
        super()._process_stream_event(data)
