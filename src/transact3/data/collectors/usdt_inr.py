"""Local USDT/INR price. Premium is derived later against the USD/INR reference."""
from __future__ import annotations

import numpy as np
import pandas as pd

from ..base import SYNTHETIC, Collector, RealSourceUnavailable, hourly_index
from ..synthetic import ar1, stress_mask


class SyntheticUsdtInr(Collector):
    name, frequency = "usdt_inr", "1h"

    def __init__(self, fx: pd.DataFrame):
        self.ref = fx[fx["pair"] == "USDINR"].set_index("ts")["mid"]

    def collect(self, start, end, rng):
        idx = hourly_index(start, end)
        stress = stress_mask(idx)
        # Premium in percent: mean-reverting around a small positive level, wider under stress.
        prem = ar1(len(idx), rng, phi=0.97, sigma=0.04, mu=0.4) + np.where(stress, 1.5, 0.0)
        price = self.ref.reindex(idx).to_numpy() * (1 + prem / 100)
        return pd.DataFrame({"ts": idx, "price_inr": price, "source_kind": SYNTHETIC})


class RealUsdtInr(Collector):
    name, frequency = "usdt_inr", "1d"

    def collect(self, start, end, rng):
        raise RealSourceUnavailable(
            "Real USDT/INR source not wired. Check history length, frequency and source terms "
            "in the feasibility report first."
        )
