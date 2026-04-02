# Turn-Taking System

Wrist extends LiveKit's built-in dynamic turn detection with continuous delay interpolation, a third EMA for user response latency, and Flux's `end_of_turn_confidence` as the primary semantic signal.

## Architecture

```
LiveKit pipeline (kept as-is):
  Silero VAD → Flux STT → ONNX EOU model → dynamic endpointing

Our extensions (monkey-patched):
  1. Binary gate → continuous interpolation across 3 EMAs
  2. New EMA: user response latency (anchors the midpoint)
  3. Flux end_of_turn_confidence extracted and weighted with ONNX EOU
  4. yield_turn tool for agent-controlled patience
```

## The Three EMAs

LiveKit's dynamic endpointing tracks two EMAs. We add a third:

```
min_delay ←──── response_latency ────→ max_delay
(mid-turn         (user's natural          (between-turn /
 pauses)           response time)           uncertain)

eou=1.0            eou=0.5                  eou=0.0
"definitely done"  "no idea"                "probably not done"
```

- **`_utterance_pause`** (min_delay): LiveKit's EMA tracking mid-turn pause durations. Updated when user pauses and resumes without agent speaking. Starts at 0.2s.
- **`_response_latency`** (midpoint): NEW. EMA tracking how long the user takes to respond after the agent stops speaking. Updated in `on_start_of_speech` when agent just finished. Starts at 1.0s.
- **`_turn_pause`** (max_delay): LiveKit's EMA tracking between-turn gaps. Updated when the agent spoke between user turns. Starts at 3.0s.

All three use alpha=0.9 (10% weight on new observation, 90% on history).

## Continuous Interpolation

LiveKit's binary gate: `eou < threshold → max_delay, else → min_delay`.

Our replacement: piecewise linear interpolation through all three EMAs:

```
if eou >= 0.5:
    t = (eou - 0.5) / 0.5
    delay = response_latency + t * (min_delay - response_latency)
else:
    t = eou / 0.5
    delay = max_delay + t * (response_latency - max_delay)
```

| eou_prob | Delay | Meaning |
|----------|-------|---------|
| 0.0 | max_delay (3.0s) | Probably not done — wait long |
| 0.25 | 2.0s | Leaning uncertain |
| 0.5 | response_latency (1.0s) | No signal — use user's natural rhythm |
| 0.75 | 0.6s | Leaning done |
| 1.0 | min_delay (0.2s) | Definitely done — respond fast |

## Flux `end_of_turn_confidence`

Deepgram's Flux model returns `end_of_turn_confidence` on every TurnInfo message — a continuous probability that the user is done speaking. LiveKit's plugin drops this value; our `FluxSTT` subclass captures it.

The combined EOU signal:
```
combined = 0.9 * flux_eot_confidence + 0.1 * onnx_eou_probability
```

Flux gets 90% weight because:
- It has access to audio features (prosody, intonation), not just text
- It runs server-side with no local setup issues
- The ONNX model's inference executor fails in some environments

## User Response Latency

When the agent finishes speaking and the user responds, the gap is the user's natural turn-taking rhythm:

```
response_latency = time_user_starts_speaking - time_agent_stops_speaking
```

This is tracked via an EMA and becomes the midpoint of the delay interpolation. If the user consistently responds in 0.4s, the midpoint drops to 0.4s — so with eou=0.5 (uncertain), the system waits 0.4s instead of the default 1.0s.

## The yield_turn Tool

The LLM can call `yield_turn` to adjust patience:
- `patience=0`: Set max_delay to 300s (effectively infinite wait)
- `patience=1-5`: Set max_delay to `3.0 * patience` seconds

Used after asking questions, presenting options, or giving complex explanations the user needs time to process.

## How LiveKit's Dynamic EMAs Update

The EMAs update based on what was happening when the user stopped speaking:

| Situation | Updates |
|-----------|---------|
| User paused, then resumed (no agent spoke) | `_utterance_pause` (min_delay) |
| User interrupted agent immediately | `_utterance_pause` (min_delay) |
| Normal turn boundary (agent spoke between) | `_turn_pause` (max_delay) |
| User responded to agent | `_response_latency` (midpoint) |

## Implementation

- `src/turn/flux_stt.py` — `FluxSTT` and `FluxSpeechStream` subclasses that capture `end_of_turn_confidence`
- `src/turn/patches.py` — Monkey-patches for `DynamicEndpointing` (response latency EMA) and `AudioRecognition._run_eou_detection` (continuous gate)
- `src/agent.py` — Applies patches at startup, uses FluxSTT
- `src/editor_agent.py` — `yield_turn` tool using `session.update_options()`
