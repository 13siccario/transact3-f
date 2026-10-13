"""Forecast ablations (E4): none / model / noisy / perfect, and the noise sweep."""
from __future__ import annotations

import pandas as pd

from ..routing.rules import Planner
from .stats import mean_ci, paired_diff


def planner_for(kind: str, sigma: float) -> Planner:
    if kind == "none":
        return Planner("none")
    if kind == "model":
        return Planner("model", name="forecast_model")
    if kind == "noisy":
        return Planner("noisy", noise=sigma, name=f"forecast_noisy_{sigma:g}")
    if kind == "perfect":
        return Planner("perfect", margin=0.0, name="oracle")
    raise ValueError(kind)


def ablation_table(runs: dict[str, pd.DataFrame], baseline: str = "none") -> pd.DataFrame:
    rows = []
    for kind, df in runs.items():
        m, lo, hi = mean_ci(df)
        d = paired_diff(df, runs[baseline]) if kind != baseline else {"diff": 0.0, "lo": float("nan"), "hi": float("nan"), "p": float("nan")}
        rows.append({"forecast": kind, "total_bps": m, "ci_lo": lo, "ci_hi": hi, "vs_none_diff": d["diff"],
                     "diff_lo": d["lo"], "diff_hi": d["hi"], "p": d["p"], "wait_h": df["wait_h"].mean()})
    return pd.DataFrame(rows)


def break_even_noise(sweep: pd.DataFrame, baseline_cost: pd.DataFrame = None) -> float | None:
    """Largest noise level up to which noisy foresight is significantly cheaper than greedy at EVERY
    smaller level too. Stops at the first level where the gain is no longer significant, so a lucky
    isolated result at higher noise cannot move it."""
    best = None
    for _, r in sweep.sort_values("sigma").iterrows():
        if r["vs_greedy_hi"] < 0:
            best = float(r["sigma"])
        else:
            break
    return best
