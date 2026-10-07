"""Cleaning rules: timestamp alignment, outlier flagging, missing-data policy.

Every rule flags rather than silently drops, so the cost engine and papers can
report how much data each rule touched.
"""
from __future__ import annotations

import numpy as np
import pandas as pd


def align_hourly(df: pd.DataFrame, keys: list[str], start: str, end: str) -> pd.DataFrame:
    """Reindex each key group onto a complete hourly UTC grid; new rows get `was_missing=True`."""
    grid = pd.date_range(start, end, freq="1h", tz="UTC", inclusive="left")
    df = df.copy()
    df["ts"] = pd.to_datetime(df["ts"], utc=True).dt.floor("1h")
    df = df.drop_duplicates(subset=["ts", *keys], keep="last")
    out = []
    for key, g in (df.groupby(keys) if keys else [((), df)]):
        key = key if isinstance(key, tuple) else (key,)
        g = g.set_index("ts").reindex(grid)
        g["was_missing"] = g.isna().all(axis=1)
        for k, v in zip(keys, key):
            g[k] = v
        out.append(g.rename_axis("ts").reset_index())
    res = pd.concat(out, ignore_index=True)
    if "source_kind" in res:
        res["source_kind"] = res["source_kind"].ffill().bfill()
    return res


def flag_outliers(s: pd.Series, window: int, k: float) -> pd.Series:
    """True where a point is > k scaled MADs from the trailing rolling median (no lookahead)."""
    med = s.rolling(window, min_periods=max(5, window // 4)).median().shift(1)
    mad = (s - med).abs().rolling(window, min_periods=max(5, window // 4)).median().shift(1)
    scaled = 1.4826 * mad.replace(0, np.nan)
    return ((s - med).abs() > k * scaled).fillna(False)


def fill_short_gaps(s: pd.Series, max_hours: int) -> pd.Series:
    """Forward-fill gaps up to max_hours; longer gaps stay NaN. Forward-only, so no lookahead."""
    return s.ffill(limit=max_hours)
