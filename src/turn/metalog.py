"""4-term metalog distributions for Bayesian turn detection.

Two competing metalog distributions model mid-turn pauses vs between-turn
pauses. Their hazard ratio provides a time-varying signal that combines
with the EOU model's semantic probability via log-odds to produce a
continuous P(turn_over) estimate.

The metalog quantile function (4-term):
    Q(y) = a1 + a2*ln(y/(1-y)) + a3*(y-0.5)*ln(y/(1-y)) + a4*(y-0.5)

where y in (0,1) is the cumulative probability and a_i are OLS coefficients.
"""

from __future__ import annotations

import math
from collections import deque

import numpy as np

# Mid-turn pause prior: right-skewed with fat tail for thinking pauses.
# Quick breathing pauses (0.1-0.5s) AND long thinking pauses (2-10s+).
# Hazard peaks ~0.5s then decays — pauses surviving past the peak are
# increasingly likely to be thinking pauses.
MID_TURN_PRIOR: list[tuple[float, float]] = [
    (0.10, 0.15),
    (0.25, 0.35),
    (0.50, 0.65),
    (0.75, 1.80),
    (0.90, 4.00),
]

# Between-turn pause prior: peaked, lighter tail. Represents normal
# conversational turn gaps — user finishes, brief silence, agent responds.
BETWEEN_TURN_PRIOR: list[tuple[float, float]] = [
    (0.10, 0.15),
    (0.25, 0.25),
    (0.50, 0.40),
    (0.75, 0.70),
    (0.90, 1.20),
]


def logit(p: float) -> float:
    """Log-odds transform, clamped to avoid infinities."""
    p = max(1e-6, min(1 - 1e-6, p))
    return math.log(p / (1 - p))


def sigmoid(x: float) -> float:
    """Inverse logit."""
    if x > 500:
        return 1.0
    if x < -500:
        return 0.0
    return 1.0 / (1.0 + math.exp(-x))


def _design_row(y: float) -> list[float]:
    """Build one row of the 4-term metalog design matrix."""
    lg = logit(y)
    return [1.0, lg, (y - 0.5) * lg, y - 0.5]


def _design_matrix(ys: list[float]) -> np.ndarray:
    """Build the full design matrix from cumulative probabilities."""
    return np.array([_design_row(y) for y in ys])


class MetalogDistribution:
    """Immutable 4-term metalog distribution with hazard function support."""

    __slots__ = ("_a",)

    def __init__(self, coefficients: np.ndarray) -> None:
        assert coefficients.shape == (4,), f"Expected 4 coefficients, got {coefficients.shape}"
        self._a = coefficients.copy()

    @classmethod
    def from_quantiles(cls, quantiles: list[tuple[float, float]]) -> MetalogDistribution:
        """Fit from (cumulative_prob, value) pairs via OLS."""
        assert len(quantiles) >= 4, "Need at least 4 quantile pairs"
        ys = [q[0] for q in quantiles]
        xs = np.array([q[1] for q in quantiles])
        M = _design_matrix(ys)
        a, _, _, _ = np.linalg.lstsq(M, xs, rcond=None)
        return cls(a)

    @property
    def coefficients(self) -> np.ndarray:
        return self._a.copy()

    def ppf(self, y: float) -> float:
        """Quantile function: cumulative probability y -> value."""
        lg = logit(y)
        return float(
            self._a[0]
            + self._a[1] * lg
            + self._a[2] * (y - 0.5) * lg
            + self._a[3] * (y - 0.5)
        )

    def ppf_derivative(self, y: float) -> float:
        """dQ/dy — needed for PDF computation.

        PDF at Q(y) is f(Q(y)) = 1 / Q'(y).
        """
        y = max(1e-6, min(1 - 1e-6, y))
        lg = logit(y)
        dlg_dy = 1.0 / (y * (1.0 - y))
        return float(
            self._a[1] * dlg_dy
            + self._a[2] * ((y - 0.5) * dlg_dy + lg)
            + self._a[3]
        )

    def cdf_approx(self, x: float, tol: float = 1e-4, max_iter: int = 50) -> float:
        """Approximate CDF via bisection: find y such that Q(y) ~ x."""
        lo, hi = 1e-6, 1 - 1e-6
        # Handle out-of-range
        if x <= self.ppf(lo):
            return lo
        if x >= self.ppf(hi):
            return hi
        for _ in range(max_iter):
            mid = (lo + hi) / 2
            if self.ppf(mid) < x:
                lo = mid
            else:
                hi = mid
            if hi - lo < tol:
                break
        return (lo + hi) / 2

    def hazard(self, t: float) -> float:
        """Hazard function h(t) = f(t) / (1 - F(t)).

        The instantaneous probability the pause ends now, given it has
        already lasted t seconds.
        """
        y = self.cdf_approx(t)
        survival = 1.0 - y
        if survival < 1e-8:
            return 1e6  # effectively certain to end

        dQ_dy = self.ppf_derivative(y)
        if dQ_dy <= 1e-10:
            return 1e6  # degenerate

        pdf = 1.0 / dQ_dy
        return pdf / survival

    def is_feasible(self, n_points: int = 50) -> bool:
        """Check monotonicity: dQ/dy > 0 for all y in (0,1)."""
        for i in range(1, n_points):
            y = i / n_points
            if self.ppf_derivative(y) <= 0:
                return False
        return True


class AdaptiveMetalog:
    """Metalog with online updates from observed pause durations.

    Fitted from a decaying prior + rolling window of observations via
    weighted least squares. Used for both mid-turn and between-turn
    pause distributions.
    """

    def __init__(
        self,
        prior_quantiles: list[tuple[float, float]],
        window_size: int = 50,
        decay: float = 0.98,
    ) -> None:
        self._prior_quantiles = list(prior_quantiles)
        self._metalog = MetalogDistribution.from_quantiles(prior_quantiles)
        self._observations: deque[tuple[float, float, float]] = deque(
            maxlen=window_size
        )  # (y, x, weight)
        self._decay = decay
        self._observation_count = 0

    @property
    def metalog(self) -> MetalogDistribution:
        return self._metalog

    @property
    def observation_count(self) -> int:
        return self._observation_count

    def hazard(self, t: float) -> float:
        """Hazard function at time t."""
        return self._metalog.hazard(t)

    def add_observation(self, duration: float, weight: float = 1.0) -> None:
        """Add an observed pause duration and refit."""
        y_hat = self._metalog.cdf_approx(duration)
        self._observations.append((y_hat, duration, weight))
        self._observation_count += 1
        self._refit()

    def _refit(self) -> None:
        """Refit metalog from decayed prior + weighted observations."""
        points: list[tuple[float, float, float]] = []

        n_obs = len(self._observations)
        prior_weight = self._decay**n_obs
        for y, x in self._prior_quantiles:
            points.append((y, x, prior_weight))

        for i, (y, x, w) in enumerate(self._observations):
            age = n_obs - 1 - i
            decay_factor = self._decay**age
            points.append((y, x, w * decay_factor))

        if len(points) < 4:
            return

        ys = [p[0] for p in points]
        xs = np.array([p[1] for p in points])
        weights = np.array([p[2] for p in points])

        M = _design_matrix(ys)
        W = np.diag(weights)
        try:
            a = np.linalg.solve(M.T @ W @ M, M.T @ W @ xs)
        except np.linalg.LinAlgError:
            return

        candidate = MetalogDistribution(a)
        if candidate.is_feasible():
            self._metalog = candidate
        else:
            # Fall back to 3-term fit
            M3 = M[:, :3]
            try:
                a3 = np.linalg.solve(M3.T @ W @ M3, M3.T @ W @ xs)
                a_padded = np.array([a3[0], a3[1], a3[2], 0.0])
                fallback = MetalogDistribution(a_padded)
                if fallback.is_feasible():
                    self._metalog = fallback
            except np.linalg.LinAlgError:
                pass
