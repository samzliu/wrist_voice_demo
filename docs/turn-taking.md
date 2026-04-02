# Turn-Taking System

Wrist uses a Bayesian turn detection system built on competing metalog distributions. Instead of a binary gate or fixed timeout, we continuously estimate P(turn_over) during silence and commit the turn when it crosses a cost-sensitive threshold.

## Why custom turn detection?

LiveKit's built-in pipeline uses a binary gate: if EOU probability < threshold, wait `max_delay`; otherwise wait `min_delay`. Problems:

1. **No gradient** — a probability of 0.39 and 0.01 get identical treatment
2. **No duration awareness** — a 0.2s pause and a 3s pause are treated the same once the gate fires
3. **No feedback loop** — false positives (agent interrupting the user) don't improve future decisions
4. **No competing hypotheses** — doesn't model the difference between mid-turn thinking pauses and actual turn boundaries

## Architecture

We run in LiveKit's `turn_detection="manual"` mode. The framework handles VAD and STT; we own the decision of when to call `session.commit_user_turn()`.

```
Silero VAD ──→ "user stopped speaking" ──┐
                                          │
Flux STT   ──→ transcript               ──┤
                                          │
ONNX EOU   ──→ p_eou (semantic signal)  ──┤
                                          ▼
                         ┌─────────────────────────────────┐
                         │    Continuous Monitoring Loop     │
                         │    (every 50ms during silence)   │
                         │                                  │
                         │    h_mid(t) ← M_mid.hazard(t)   │
                         │    h_bet(t) ← M_bet.hazard(t)   │
                         │    lr(t) = h_bet(t) / h_mid(t)  │
                         │                                  │
                         │    log_odds = w1·log(lr)         │
                         │              + w2·logit(p_eou)   │
                         │              + bias              │
                         │                                  │
                         │    P(turn_over) = σ(log_odds)    │
                         │                                  │
                         │    if P > τ: commit_user_turn()  │
                         └─────────────────────────────────┘
                                          │
                                    observe outcome
                                          │
                              ┌───────────┴───────────┐
                              │                       │
                       true positive            false positive
                       (update M_between)       (update M_mid)
```

## The two metalog distributions

### M_mid — mid-turn pause distribution

Learned from pauses where the user resumed speaking (timer cancelled). These include:
- Quick breathing pauses (0.1–0.5s)
- Thinking pauses (1–10s+)

The distribution is **right-skewed with a fat tail** — a user thinking mid-sentence can pause for many seconds.

Initial prior:

| Quantile | Duration |
|----------|----------|
| 10th | 0.15s |
| 25th | 0.35s |
| 50th | 0.65s |
| 75th | 1.80s |
| 90th | 4.00s |

### M_between — between-turn pause distribution

Learned from pauses at actual turn boundaries (successful commits). These are normal conversational turn gaps — the user finishes, brief silence, agent responds.

The distribution is **tighter** — most turn boundaries resolve within a second.

Initial prior:

| Quantile | Duration |
|----------|----------|
| 10th | 0.15s |
| 25th | 0.25s |
| 50th | 0.40s |
| 75th | 0.70s |
| 90th | 1.20s |

### Why two distributions?

They represent competing hypotheses about each silence: "is this a mid-turn pause or a turn boundary?" The hazard ratio between them provides a time-varying signal that most systems lack.

## Hazard functions

The hazard function `h(t) = f(t) / (1 - F(t))` gives the instantaneous probability the pause ends *right now*, given it has already lasted `t` seconds.

For the metalog, computed from the quantile function:

```
F(t) = Q^{-1}(t)                    # CDF via bisection
f(t) = 1 / Q'(F(t))                 # PDF from quantile derivative
h(t) = f(t) / (1 - F(t))            # hazard
```

### How the hazard ratio evolves during silence

```
t = 0.1s:  lr ≈ 0.5   (probably mid-turn, silence just started)
t = 0.3s:  lr ≈ 1.0   (ambiguous — could be either)
t = 0.6s:  lr ≈ 2.5   (mid-turn hazard dropping, evidence for turn-end)
t = 1.5s:  lr varies   (depends on this user's learned distributions)
t = 5.0s:  lr flattens (both hazards small — EOU model dominates)
```

At short durations, the hazard ratio does most of the work. At long durations (past the mid-turn mode), the EOU model's semantic signal becomes the dominant discriminator.

## The log-odds combination

At each 50ms polling step:

```
log_odds = w1·log(h_between(t) / h_mid(t)) + w2·logit(p_eou) + bias
P(turn_over) = sigmoid(log_odds)
```

- **w1, w2** — signal weights. Phase 1: fixed at 1.0 (naive Bayes). Phase 2: learned via logistic regression from labeled outcomes.
- **bias** — base rate prior (default 0.0).
- **VAD acts as a gate** — if VAD fires START_OF_SPEECH, P is clamped to 0 and the loop exits.

## Cost-sensitive threshold

The costs of errors are asymmetric:
- **False positive (interrupting)**: jarring, breaks flow, frustrating
- **False negative (too slow)**: laggy, but much less destructive

The threshold is derived from the cost ratio:

```
τ = c_interrupt / (c_interrupt + c_latency)
```

Default: `c_interrupt = 5, c_latency = 1` → `τ = 0.83`.

The system adapts τ online by tracking the recent false positive rate:
- FP rate > 15% → increase `c_interrupt` (become more cautious)
- FP rate < 5% → decrease `c_interrupt` (respond faster)

## Learning from outcomes

### Mid-turn pause (user resumes speaking)

The monitoring loop is cancelled. The fully observed pause duration is added to M_mid:

```
metalog_mid.add_observation(pause_duration)
```

This is the best training signal — real, uncensored mid-turn pause durations from this user.

### True positive (agent spoke, user didn't resume)

The silence duration at commit time is added to M_between:

```
metalog_between.add_observation(silence_duration)
```

### False positive (agent spoke, user resumed within 0.8s)

This was actually a mid-turn pause that we misclassified. The observation is **right-censored** — we know the true pause was longer than what we observed, but we don't know how much longer.

We impute at 1.5x the observed duration with reduced weight (0.5):

```
metalog_mid.add_observation(duration * 1.5, weight=0.5)
```

Why 1.5x: we know the pause was at least `duration` seconds. A conservative estimate avoids wildly overestimating the tail. The low weight ensures uncensored observations (from real mid-turn pauses) dominate the fit over time.

### Metalog refitting

After each observation, the metalog is refit via weighted least squares:

```
Points = decayed prior quantiles + recent observations
Weights = decay^age for each point (older observations fade)
Solve: (M^T W M) a = M^T W x
Check feasibility (dQ/dy > 0 everywhere)
If infeasible: fall back to 3-term fit
```

The decay (0.98 per observation) means the prior fades as real data accumulates, but always provides a safety anchor.

## The yield_turn tool

The LLM can call `yield_turn` to explicitly cede the floor — typically after asking a question or presenting options.

When yielded:
- State machine enters YIELDED
- The monitoring loop doesn't run — no timeout
- When the user eventually speaks, the threshold is boosted to 0.95 (extra patience)
- After the turn commits, threshold resets to normal

## State machine

```
IDLE ──(user speaks)──→ USER_SPEAKING
                              │
                        (user stops)
                              │
                        ┌─────▼──────┐
                        │  WAITING   │ ← continuous monitoring loop
                        │  (50ms     │   computes P(turn_over)
                        │   polling) │
                        └──┬─────┬───┘
                           │     │
                   (user speaks) (P > τ)
                           │     │
                    USER_SPEAKING │
                                 ▼
                           COMMITTING ──→ AGENT_RESPONDING
                                               │
                                         MONITORING_FP
                                          │          │
                                    (0.8s ok)  (user speaks)
                                         │          │
                                       IDLE    false positive
                                              update M_mid

Special: YIELDED ──(user speaks)──→ USER_SPEAKING (boosted threshold)
```

## Tuning guide

| Parameter | Default | Effect |
|-----------|---------|--------|
| `w_duration` | 1.0 | Weight on hazard ratio signal |
| `w_eou` | 1.0 | Weight on EOU model signal |
| `bias` | 0.0 | Base rate prior in log-odds |
| `c_interrupt` | 5.0 | Cost of false positive (interrupting) |
| `c_latency` | 1.0 | Cost of excess latency |
| `fp_detection_window` | 0.8s | How long after agent speaks to watch for re-entry |
| `fp_imputation_multiple` | 1.5 | Multiple for censored FP observations in M_mid |
| `max_silence` | 30.0s | Hard cap before forced commit |
| `decay` (metalog) | 0.98 | Prior weight decay per observation |

## Prior management

### Phase 1 (current)

Each session starts fresh from hardcoded priors. Both metalogs adapt within the session. All decisions are logged via `record=True` for LiveKit Cloud observability.

### Phase 2 (planned)

Persist final metalog coefficients + observation counts to `~/.wrist/turn_prior.json` at session end. On next session start, blend with hardcoded prior weighted by observation count. Also: fit w1, w2, bias via logistic regression from accumulated labeled outcomes across sessions.
