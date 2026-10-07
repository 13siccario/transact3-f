"""Hourly target panel and origin-time features.

Every feature at row t uses data up to and including t only (the forecast origin).
The target for origin t is the value at t + horizon.
"""
from __future__ import annotations

import numpy as np
import pandas as pd


def build_panel(processed: dict[str, pd.DataFrame], pool_id: str) -> pd.DataFrame:
    fx = processed["fx"]
    usd = fx[fx["pair"] == "USDINR"].set_index("ts")
    pools = processed["pools"]
    pool = pools[pools["pool_id"] == pool_id].set_index("ts")
    peg = processed["peg"]
    peg = peg[peg["coin"] == "USDT"].set_index("ts")
    gas = processed["gas"].set_index("ts")
    prem = processed["premium"].set_index("ts")

    panel = pd.DataFrame(index=usd.index)
    panel["fx_return"] = np.log(usd["mid"]).diff()
    panel["fx_vol"] = panel["fx_return"].abs()
    panel["fx_spread"] = usd["spread_bps"]
    panel["gas_gwei"] = gas["base_fee_gwei"]
    panel["peg_dev"] = peg["price_usd"] - 1.0
    panel["premium_pct"] = prem["premium_pct"]
    # slippage in bps for a $10,000 transfer under the linear-impact model in costs.decomposition
    panel["slip_bps"] = 50 * 10_000 / pool["depth_1pct_usd"]
    panel["eth_ret"] = np.log(gas["eth_usd"]).diff()
    return panel.dropna()


def build_features(panel: pd.DataFrame, cols: list[str], lags: list[int], windows: list[int]) -> pd.DataFrame:
    """Features at origin t from `cols` of the panel. No row uses data after t."""
    parts = {}
    for c in cols:
        s = panel[c]
        for k in lags:
            parts[f"{c}_lag{k}"] = s.shift(k)
        for w in windows:
            r = s.rolling(w)
            parts[f"{c}_mean{w}"] = r.mean()
            parts[f"{c}_std{w}"] = r.std()
    hour = panel.index.hour
    parts["hour_sin"] = np.sin(2 * np.pi * hour / 24)
    parts["hour_cos"] = np.cos(2 * np.pi * hour / 24)
    parts["dow"] = panel.index.dayofweek
    return pd.DataFrame(parts, index=panel.index)


def build_targets(panel: pd.DataFrame, targets: list[str], horizon: int) -> pd.DataFrame:
    return panel[targets].shift(-horizon)
