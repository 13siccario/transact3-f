"""Diebold-Mariano test with the Harvey-Leybourne-Newbold small-sample correction."""
from __future__ import annotations

import numpy as np
from scipy import stats


def dm_test(e_bench: np.ndarray, e_model: np.ndarray, h: int = 1) -> tuple[float, float]:
    """Two-sided DM test on squared-error loss. Returns (statistic, p-value).

    Statistic > 0 means the model has lower loss than the benchmark.
    Returns (nan, nan) when the loss differential has no variance (e.g. identical forecasts).
    """
    d = np.asarray(e_bench) ** 2 - np.asarray(e_model) ** 2
    n = len(d)
    if n < 10:
        return np.nan, np.nan
    dbar = d.mean()
    dc = d - dbar
    lrv = dc @ dc / n
    for k in range(1, h):                       # rectangular kernel, lags up to h-1
        lrv += 2 * (dc[k:] @ dc[:-k]) / n
    if not np.isfinite(lrv) or lrv <= 1e-30:
        return np.nan, np.nan
    stat = dbar / np.sqrt(lrv / n)
    stat *= np.sqrt((n + 1 - 2 * h + h * (h - 1) / n) / n)
    p = 2 * stats.t.sf(abs(stat), df=n - 1)
    return float(stat), float(p)
