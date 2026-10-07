"""Gas fees and stablecoin peg deviation (both on-chain cost drivers)."""
from __future__ import annotations

import numpy as np
import pandas as pd

from ..base import SYNTHETIC, Collector, RealSourceUnavailable, hourly_index
from ..synthetic import ar1, stress_mask


class SyntheticGas(Collector):
    name, frequency = "gas", "1h"

    def collect(self, start, end, rng):
        idx = hourly_index(start, end)
        stress = stress_mask(idx)
        log_base = ar1(len(idx), rng, 0.98, 0.08, mu=np.log(12.0))
        spikes = (rng.random(len(idx)) < 0.01) * rng.exponential(1.0, len(idx))
        base = np.exp(log_base + spikes + np.where(stress, 0.4, 0.0))
        eth = 3000 * np.exp(np.cumsum(rng.normal(0, 0.004, len(idx))))
        return pd.DataFrame({"ts": idx, "base_fee_gwei": base,
                             "priority_fee_gwei": 1 + 0.1 * base, "eth_usd": eth,
                             "source_kind": SYNTHETIC})


class SyntheticPeg(Collector):
    name, frequency = "peg", "1h"

    def collect(self, start, end, rng):
        idx = hourly_index(start, end)
        stress = stress_mask(idx)
        frames = []
        for coin, sigma in (("USDT", 0.0003), ("USDC", 0.0002)):
            dev = ar1(len(idx), rng, 0.9, sigma) * np.where(stress, 3.0, 1.0)
            frames.append(pd.DataFrame({"ts": idx, "coin": coin, "price_usd": 1 + dev,
                                        "source_kind": SYNTHETIC}))
        return pd.concat(frames, ignore_index=True)


class RealGas(Collector):
    name, frequency = "gas", "1h"

    def collect(self, start, end, rng):
        raise RealSourceUnavailable("Real gas/peg data not wired. See feasibility report.")
