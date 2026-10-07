"""Run a policy through a stream of simulated transfers, with delayed feedback to learning policies."""
from __future__ import annotations

import heapq

import numpy as np
import pandas as pd

from ..sim.generator import size_segment
from ..sim.env import RoutingEnv
from ..routing.rules import Policy


def run_policy(env: RoutingEnv, policy: Policy, n_episodes: int, seed: int) -> pd.DataFrame:
    """Episodes are sequential transfers in one world. Learning policies only see an outcome once the
    transfer has settled (send time + latency), so decisions in between use a stale model."""
    policy.reset()
    obs, _ = env.reset(seed=seed)
    pending: list[tuple[float, int, np.ndarray, int, float]] = []
    rows = []
    for ep in range(n_episodes):
        while pending and pending[0][0] <= env.t0:
            _, _, o, a, r = heapq.heappop(pending)
            policy.observe(o, a, r)
        while True:
            a = policy.act(env, obs)
            prev = obs
            obs, r, done, _, info = env.step(a)
            if done:
                heapq.heappush(pending, (info["settle_t"], ep, prev, a, r))
                rows.append({"policy": policy.name, "episode": ep, "segment": size_segment(info["amount"]), **info})
                obs, _ = env.reset()
                break
    return pd.DataFrame(rows)


def summarise(df: pd.DataFrame, by: list[str] | None = None) -> pd.DataFrame:
    g = df.groupby(by or ["policy"])
    return g.agg(n=("total_bps", "size"), total_bps=("total_bps", "mean"), cost_bps=("cost_bps", "mean"),
                 wait_h=("wait_h", "mean"), late_rate=("late", "mean"), fail_rate=("failed", "mean")).reset_index()
