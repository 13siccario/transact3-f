"""Regime labels. Synthetic data uses the synthetic stress window; real data uses the
verified event calendar only (nothing is verified yet, so real data is all 'normal')."""
from __future__ import annotations

import pandas as pd

from ..data.calendar import load_events
from ..data.synthetic import STRESS_END, STRESS_START


def label_regimes(ts: pd.Series, source_kind: str) -> pd.Series:
    ts = pd.to_datetime(ts, utc=True)
    out = pd.Series("normal", index=ts.index)
    if source_kind == "synthetic":
        out[(ts >= pd.Timestamp(STRESS_START, tz="UTC")) & (ts < pd.Timestamp(STRESS_END, tz="UTC"))] = "stress"
    else:
        for _, e in load_events(verified_only=True).iterrows():
            out[(ts >= e["date"]) & (ts < e["date"] + pd.Timedelta(days=14))] = "stress"
    return out
