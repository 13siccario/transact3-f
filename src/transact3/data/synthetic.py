"""Synthetic generators. Shapes only; they are NOT calibrated to observations.

Used so the pipeline, cost engine, API and UI run end to end before real
sources are confirmed. Results from synthetic data must never go in a paper.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

# Stress window used only inside the synthetic world. It is not a claim about real dates.
STRESS_START = "2026-06-10"
STRESS_END = "2026-06-24"


def stress_mask(idx: pd.DatetimeIndex) -> np.ndarray:
    return np.asarray((idx >= pd.Timestamp(STRESS_START, tz="UTC")) & (idx < pd.Timestamp(STRESS_END, tz="UTC")))


def garch_returns(n: int, rng: np.random.Generator, base_vol: float, stress: np.ndarray,
                  stress_mult: float = 3.0, omega=0.05, alpha=0.08, beta=0.9) -> np.ndarray:
    """Hourly log returns with GARCH(1,1)-style volatility clustering and a stress multiplier."""
    r = np.zeros(n)
    var = 1.0
    for t in range(n):
        eps = rng.standard_normal()
        r[t] = np.sqrt(var) * eps
        var = omega + alpha * r[t] ** 2 + beta * var
    r = r / r.std() * base_vol
    return r * np.where(stress, stress_mult, 1.0)


def ar1(n: int, rng: np.random.Generator, phi: float, sigma: float, mu: float = 0.0) -> np.ndarray:
    x = np.zeros(n)
    x[0] = mu
    for t in range(1, n):
        x[t] = mu + phi * (x[t - 1] - mu) + sigma * rng.standard_normal()
    return x
