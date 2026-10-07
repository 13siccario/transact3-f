"""Rule-based routers: fixed, greedy, forecast-aware and oracle.

Greedy, forecast-aware and oracle are ONE planner that differs only in the forecast it is shown:
  greedy          forecast kind 'none'      (persistence, so sending now always wins)
  forecast-aware  'model' or 'noisy'
  oracle          'perfect'
That makes the forecast ablation exact: change the kind, nothing else.
"""
from __future__ import annotations

import numpy as np

from ..sim.env import H, RoutingEnv
from ..sim.rails import ALL_RAILS


class Policy:
    name = "policy"
    learns = False

    def reset(self) -> None: ...

    def act(self, env: RoutingEnv, obs: np.ndarray) -> int:
        raise NotImplementedError

    def observe(self, obs: np.ndarray, action: int, reward: float) -> None: ...


def _cheapest_now(env: RoutingEnv) -> int:
    cost = env.cost_now() + np.array([env.expected_penalty(i, 0) for i in range(len(ALL_RAILS))])
    cost = np.where(env.send_mask(), cost, np.inf)
    return int(np.argmin(cost))


class Fixed(Policy):
    """Always use one rail immediately; fall back to the cheapest usable rail if it is unavailable."""

    def __init__(self, rail: str):
        self.rail = rail
        self.name = f"fixed_{rail}"

    def act(self, env, obs):
        i = ALL_RAILS.index(self.rail)
        return 1 + (i if env.send_mask()[i] else _cheapest_now(env))


class Planner(Policy):
    def __init__(self, kind: str, noise: float = 0.0, margin: float = 3.0, name: str | None = None):
        self.kind, self.noise, self.margin = kind, noise, margin
        self.name = name or {"none": "greedy", "perfect": "oracle"}.get(kind, f"forecast_{kind}")

    def act(self, env, obs):
        now_best = _cheapest_now(env)
        if self.kind == "none" or not env.wait_allowed():
            return 1 + now_best
        fc = env.forecast_matrix(self.kind, self.noise)
        tau_max = min(H - 1, env.max_wait_ticks() - env.k)
        pen = lambda i, tau: env.expected_penalty(i, tau)
        score_now = fc[now_best, 0] + pen(now_best, 0)
        best, best_tau = score_now, 0
        for tau in range(1, tau_max + 1):
            sm = env.send_mask(tau)
            for i in np.flatnonzero(sm):
                s = fc[i, tau] + pen(i, tau)
                if s < best:
                    best, best_tau = s, tau
        # The router knows its forecast error level, so the gain needed to justify waiting grows with it.
        needed = self.margin + self.noise * score_now
        if best_tau > 0 and best < score_now - needed:
            return 0
        return 1 + now_best
