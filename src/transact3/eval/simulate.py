"""User-facing transaction simulation.

A user describes a schedule of transfers (amount, deadline, how many, how often) and a start hour in
the observed history. Each routing policy then handles the schedule hour by hour using only what it
could know at the time, and we return a full trace: market state per hour, every decision, settlement
and running cost. The front end plays this trace back at a speed the user controls.
"""
from __future__ import annotations

import dataclasses
from dataclasses import replace

import numpy as np
import pandas as pd

from ..costs.paths import PATHS, path_costs
from ..routing.compliance import Rules, guard
from .replay import PATH_IDS, LinUCBPaths, ReplayData, _pen, _setup, decide

POLICIES = {
    "greedy": "Send now on the cheapest path",
    "forecast_aware": "Wait an hour when the forecast says it will be cheaper",
    "linucb": "Learning router (bandit)",
    "oracle": "Perfect hindsight (not achievable)",
}


def _with_amount(data: ReplayData, A: float) -> ReplayData:
    """Cost arrays for an arbitrary amount (the grid sizes are precomputed; others are built on demand)."""
    if A in data.cost:
        return data
    cost = {**data.cost, A: np.stack([path_costs(p, A, data.state, data.params)["total_bps"].to_numpy() for p in PATH_IDS])}
    pred = {**data.pred_next, A: np.stack([path_costs(p, A, data.pred_state, data.params)["total_bps"].to_numpy() for p in PATH_IDS])}
    return replace(data, cost=cost, pred_next=pred)


def valid_range(data: ReplayData, deadline_h: int, count: int, interval_h: int) -> tuple[int, int]:
    """Smallest and largest start index that keep the whole schedule inside the observed period."""
    span = (count - 1) * interval_h + deadline_h + 2
    return 0, max(0, len(data.ts) - span - 1)


def simulate_schedule(data: ReplayData, cfg: dict, rules: Rules, *, amount: float, deadline_h: int, count: int,
                      interval_h: int, start_idx: int, scenario: str | None = None,
                      policies: list[str] | None = None, warmup_h: int = 400) -> dict:
    scenario = scenario or rules.default_scenario
    policies = policies or list(POLICIES)
    data = _with_amount(data, amount)
    lo, hi = valid_range(data, deadline_h, count, interval_h)
    if not lo <= start_idx <= hi:
        raise ValueError(f"start must leave room for the whole schedule: choose an index between {lo} and {hi}")
    su = _setup(rules, scenario, cfg)
    elig_names = [PATH_IDS[i] for i in su.elig]
    arrivals = [start_idx + j * interval_h for j in range(count)]
    end_idx = arrivals[-1] + deadline_h + int(su.lat[su.elig].max()) + 1
    end_idx = min(end_idx, len(data.ts) - 1)

    market = [{"i": int(i - start_idx), "ts": data.ts[i].isoformat(), "regime": str(data.regime[i]),
               "premium_pct": float(data.premium_bps[i]),
               "cost_bps": {PATH_IDS[p]: float(data.cost[amount][p, i] + su.extra[p]) for p in range(len(PATH_IDS))}}
              for i in range(start_idx, end_idx + 1)]

    result = {}
    for pol in policies:
        lin = None
        if pol == "linucb":
            lin = LinUCBPaths(len(PATH_IDS), 5 + len(PATH_IDS) + data.context.shape[1])
            for n, a in enumerate(range(max(0, start_idx - warmup_h), start_idx)):     # learn from the past only
                lin.flush(a)
                x = lin.features(data, amount, a, deadline_h)
                i = lin.choose(x, su.elig)
                c = float(data.cost[amount][i, a] + su.extra[i] + _pen(su, 0, deadline_h)[i])
                lin.push(a + su.lat[i], n, i, x, -c / 100)
        transfers, events = [], []
        for j, a in enumerate(arrivals):
            events.append({"i": a - start_idx, "type": "arrive", "transfer": j})
            quote = data.cost[amount][:, a] + su.extra + _pen(su, 0, deadline_h)
            quote_bps = float(min(quote[i] for i in su.elig))
            trace: list = []
            if lin:
                lin.flush(a)
                x = lin.features(data, amount, a, deadline_h)
                p, k = lin.choose(x, su.elig), 0
            else:
                k, p = decide(pol, data, su, amount, a, deadline_h, trace if pol == "forecast_aware" else None)
            guard(PATH_IDS[p], elig_names)
            cost = float(data.cost[amount][p, a + k] + su.extra[p])
            pen = float(_pen(su, k, deadline_h)[p])
            if lin:
                lin.push(a + su.lat[p], 10_000 + j, p, x, -(cost + pen) / 100)
            _, o_k, o_p = _oracle(data, su, amount, a, deadline_h)
            oracle_bps = float(data.cost[amount][o_p, a + o_k] + su.extra[o_p] + _pen(su, o_k, deadline_h)[o_p])
            for step in trace:
                if step["action"] == "wait":
                    events.append({"i": a + step["tick"] - start_idx, "type": "wait", "transfer": j,
                                   "now_bps": step["now_bps"], "forecast_next_bps": step["forecast_next_bps"]})
            send_i, settle_i = a + k, a + k + int(np.ceil(su.lat[p]))
            events.append({"i": send_i - start_idx, "type": "send", "transfer": j, "path": PATH_IDS[p], "bps": cost})
            events.append({"i": settle_i - start_idx, "type": "settle", "transfer": j, "path": PATH_IDS[p], "late": pen > 0})
            transfers.append({"transfer": j, "arrive_i": a - start_idx, "send_i": send_i - start_idx, "settle_i": settle_i - start_idx,
                              "wait_h": k, "path": PATH_IDS[p], "cost_bps": cost, "penalty_bps": pen, "total_bps": cost + pen,
                              "total_usd": (cost + pen) * amount / 1e4, "quote_bps": quote_bps,
                              "saving_vs_quote_bps": quote_bps - (cost + pen), "oracle_bps": oracle_bps,
                              "regret_bps": cost + pen - oracle_bps, "late": pen > 0})
        events.sort(key=lambda e: (e["i"], e["type"] != "arrive"))
        total_usd = sum(t["total_usd"] for t in transfers)
        result[pol] = {"label": POLICIES[pol], "transfers": transfers, "events": events,
                       "summary": {"total_usd": total_usd, "mean_bps": float(np.mean([t["total_bps"] for t in transfers])),
                                   "mean_regret_bps": float(np.mean([t["regret_bps"] for t in transfers])),
                                   "mean_wait_h": float(np.mean([t["wait_h"] for t in transfers])),
                                   "late": int(sum(t["late"] for t in transfers))}}
    return {"amount": amount, "deadline_h": deadline_h, "count": count, "interval_h": interval_h, "scenario": scenario,
            "eligible_paths": elig_names, "start_ts": data.ts[start_idx].isoformat(), "market": market, "policies": result,
            "source_kind": data.source_kind}


def _oracle(data, su, A, a, D):
    return (0.0, *decide("oracle", data, su, A, a, D))
