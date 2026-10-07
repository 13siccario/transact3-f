"""Paired comparison across independent worlds."""
from __future__ import annotations

import numpy as np
import pandas as pd
from scipy import stats


def paired_diff(a: pd.DataFrame, b: pd.DataFrame, col: str = "total_bps") -> dict:
    """Mean of (a - b) by world with a t-interval over worlds. Negative means `a` is cheaper."""
    da = a.groupby("seed")[col].mean()
    db = b.groupby("seed")[col].mean()
    d = (da - db).dropna().to_numpy()
    n = len(d)
    if n < 2:
        return {"diff": float(d.mean()) if n else np.nan, "lo": np.nan, "hi": np.nan, "p": np.nan, "n_worlds": n}
    se = d.std(ddof=1) / np.sqrt(n)
    t = stats.t.ppf(0.975, n - 1)
    p = stats.ttest_1samp(d, 0.0).pvalue if d.std(ddof=1) > 0 else np.nan
    return {"diff": float(d.mean()), "lo": float(d.mean() - t * se), "hi": float(d.mean() + t * se), "p": float(p), "n_worlds": n}


def mean_ci(df: pd.DataFrame, col: str = "total_bps") -> tuple[float, float, float]:
    m = df.groupby("seed")[col].mean().to_numpy()
    if len(m) < 2:
        return float(m.mean()), np.nan, np.nan
    se = m.std(ddof=1) / np.sqrt(len(m))
    t = stats.t.ppf(0.975, len(m) - 1)
    return float(m.mean()), float(m.mean() - t * se), float(m.mean() + t * se)
