"""On-chain stablecoin FX pools: price, depth, fees, volume."""
from __future__ import annotations

import numpy as np
import pandas as pd

from ..base import SYNTHETIC, Collector, RealSourceUnavailable, hourly_index
from ..synthetic import ar1, stress_mask

# (pool_id, pair, fee_bps, base TVL in USD). Synthetic stand-ins; no INR-referenced pool is assumed.
POOLS = [
    ("syn-usdc-usdt-1", "USDC/USDT", 1, 120e6),
    ("syn-usdc-eurc-5", "USDC/EURC", 5, 25e6),
    ("syn-usdc-brz-30", "USDC/BRZ", 30, 3e6),   # non-INR EM proxy
]


class SyntheticPools(Collector):
    name, frequency = "pools", "1h"

    def collect(self, start, end, rng):
        idx = hourly_index(start, end)
        stress = stress_mask(idx)
        frames = []
        for pid, pair, fee, tvl0 in POOLS:
            tvl = tvl0 * np.exp(ar1(len(idx), rng, 0.995, 0.01)) * np.where(stress, 0.7, 1.0)
            dev = ar1(len(idx), rng, 0.9, 0.0002) * np.where(stress, 4.0, 1.0)
            frames.append(pd.DataFrame({
                "ts": idx, "pool_id": pid, "pair": pair, "fee_bps": fee,
                "tvl_usd": tvl, "mid_price": 1 + dev,
                "depth_1pct_usd": tvl * 0.2,
                "volume_usd": tvl * 0.03 * np.exp(rng.normal(0, 0.4, len(idx))),
                "source_kind": SYNTHETIC,
            }))
        return pd.concat(frames, ignore_index=True)


class RealPools(Collector):
    name, frequency = "pools", "1h"

    def collect(self, start, end, rng):
        raise RealSourceUnavailable("Real pool data not wired. See feasibility report (pool list).")
