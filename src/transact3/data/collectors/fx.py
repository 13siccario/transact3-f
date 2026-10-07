"""FX collector: hourly mid and spread for USD/INR and major pairs."""
from __future__ import annotations

import numpy as np
import pandas as pd

from ..base import REAL, SYNTHETIC, Collector, RealSourceUnavailable, hourly_index
from ..synthetic import garch_returns, stress_mask

START_LEVELS = {"USDINR": 83.5, "EURUSD": 1.08, "GBPUSD": 1.27, "USDAED": 3.6725}
BASE_VOL = {"USDINR": 0.0004, "EURUSD": 0.0006, "GBPUSD": 0.0007, "USDAED": 0.00002}
BASE_SPREAD_BPS = {"USDINR": 2.0, "EURUSD": 0.6, "GBPUSD": 0.9, "USDAED": 1.5}


class SyntheticFX(Collector):
    name, frequency = "fx", "1h"

    def __init__(self, pairs):
        self.pairs = list(pairs)

    def collect(self, start, end, rng):
        idx = hourly_index(start, end)
        stress = stress_mask(idx)
        frames = []
        for pair in self.pairs:
            r = garch_returns(len(idx), rng, BASE_VOL[pair], stress)
            mid = START_LEVELS[pair] * np.exp(np.cumsum(r))
            spread = BASE_SPREAD_BPS[pair] * (1 + 0.5 * np.abs(r) / BASE_VOL[pair]) * np.where(stress, 2.0, 1.0)
            frames.append(pd.DataFrame({"ts": idx, "pair": pair, "mid": mid,
                                        "spread_bps": spread, "source_kind": SYNTHETIC}))
        return pd.concat(frames, ignore_index=True)


class RealFX(Collector):
    name, frequency = "fx", "1h"

    def collect(self, start, end, rng):
        raise RealSourceUnavailable(
            "Real FX source not wired. Run `transact3 feasibility` and record a go for hourly "
            "tick data (or fall back to daily FBIL/RBI reference rates)."
        )
