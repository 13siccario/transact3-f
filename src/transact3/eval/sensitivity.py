"""Sensitivity (E5): policy rankings across parameter draws and CBDC scenarios."""
from __future__ import annotations

import numpy as np
import pandas as pd
from scipy.stats import kendalltau

from ..routing.compliance import Rules
from ..routing.linucb import LinUCB
from ..routing.rules import Fixed, Planner
from ..sim.env import RoutingEnv
from ..sim.rails import perturb, rails_for
from .harness import run_policy

SENS_POLICIES = ["fixed_CB", "fixed_LR", "fixed_SC", "greedy", "forecast_model", "linucb", "oracle"]


def _make(name: str):
    return {"fixed_CB": lambda: Fixed("CB"), "fixed_LR": lambda: Fixed("LR"), "fixed_SC": lambda: Fixed("SC"),
            "greedy": lambda: Planner("none"), "forecast_model": lambda: Planner("model", name="forecast_model"),
            "linucb": lambda: LinUCB(), "oracle": lambda: Planner("perfect", margin=0.0)}[name]()


def score_policies(rails, eligible, seeds: int, episodes: int, base_seed: int) -> pd.Series:
    out = {}
    for name in SENS_POLICIES:
        vals = []
        for s in range(seeds):
            env = RoutingEnv(rails, eligible, forecast_kind="model")
            vals.append(run_policy(env, _make(name), episodes, seed=base_seed + s)["total_bps"].mean())
        out[name] = float(np.mean(vals))
    return pd.Series(out)


def run_sensitivity(cfg: dict, rules: Rules, seed: int) -> tuple[pd.DataFrame, pd.DataFrame]:
    sc = cfg["sensitivity"]
    rng = np.random.default_rng(seed + 77)
    base_rails = rails_for(cfg["cbdc"])
    elig = rules.eligible_rails(cfg["cbdc"])
    base = score_policies(base_rails, elig, sc["seeds"], sc["episodes"], seed)
    rows = []
    for d in range(sc["draws"]):
        s = score_policies(perturb(base_rails, rng, sc["spread"]), elig, sc["seeds"], sc["episodes"], seed + 100 * (d + 1))
        tau = kendalltau(base.rank(), s.rank()).statistic
        rows.append({"draw": d, "kendall_tau": tau, "best_policy": s.drop("oracle").idxmin(),
                     "model_beats_greedy": bool(s["forecast_model"] < s["greedy"]),
                     "linucb_beats_greedy": bool(s["linucb"] < s["greedy"]), **{f"bps_{k}": v for k, v in s.items()}})
    draws = pd.DataFrame(rows)
    cb = []
    for scen in sc["cbdc"]:
        s = score_policies(rails_for(scen), rules.eligible_rails(scen), sc["seeds"], sc["episodes"], seed)
        cb.append({"cbdc": scen, "kendall_tau_vs_none": kendalltau(base.rank(), s.rank()).statistic,
                   "best_policy": s.drop("oracle").idxmin(), **{f"bps_{k}": v for k, v in s.items()}})
    return draws, pd.DataFrame(cb)
