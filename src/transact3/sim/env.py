"""Gymnasium environment: one episode is one transfer; actions are wait or send via a rail.

MDP:
  state    transfer (amount, deadline, ticks elapsed), hour of day, current cost per rail,
           liquidity buffer per rail, optional forecast signal
  actions  0 = wait one hour, 1..K = send now via rail k
  mask     eligibility (compliance filter) x liquidity (buffer >= amount) x timing (wait only while
           the fastest eligible rail can still make the deadline)
  reward   -(realised cost + failure and lateness penalties) / 100, paid when the transfer is sent
Liquidity buffers persist across episodes and refill with time, so today's choice constrains tomorrow's.
"""
from __future__ import annotations

import gymnasium as gym
import numpy as np
from gymnasium import spaces

from ..routing.compliance import guard
from .generator import GeneratorConfig, next_transfer
from .rails import ALL_RAILS, Rail
from .world import Empirical, World

K = len(ALL_RAILS)
H = 12                      # forecast horizon in hours
FAIL_PEN_BPS = 100.0
FAIL_EXTRA_LAT_H = 6.0
LATE_BASE_BPS = 50.0
LATE_PER_H_BPS = 10.0
OBS_DIM = 6 + 4 * K


class RoutingEnv(gym.Env):
    metadata = {"render_modes": []}

    def __init__(self, rails: dict[str, Rail], eligible: list[str], gen: GeneratorConfig | None = None,
                 world_len: int = 24 * 120, forecast_kind: str = "none", forecast_noise: float = 0.0,
                 seed: int = 0, empirical: Empirical | None = None):
        self.rails = rails
        self.eligible = list(eligible)
        self.gen = gen or GeneratorConfig()
        self.world_len = world_len
        self.forecast_kind = forecast_kind
        self.forecast_noise = forecast_noise
        self.empirical = empirical
        self._seed_streams(seed)
        self.action_space = spaces.Discrete(1 + K)
        self.observation_space = spaces.Box(-20.0, 20.0, shape=(OBS_DIM,), dtype=np.float32)
        self.world: World | None = None
        self.clock = 0
        self.buf_time = 0
        self.buffer: dict[str, float] = {}

    # ---- world and transfer lifecycle ---------------------------------------------------------
    def _seed_streams(self, seed: int):
        """Separate streams so every policy faces the same market, arrivals and outcome draws."""
        w, a, o = np.random.SeedSequence(seed).spawn(3)
        self.rng_world, self.rng_arrivals, self.rng_out = (np.random.default_rng(x) for x in (w, a, o))

    def _new_world(self):
        self.world = World(self.rails, self.world_len, self.rng_world, self.empirical)
        self.clock = 0                       # arrival clock: independent of when transfers are sent
        self.buf_time = 0
        self.buffer = {n: r.cap_usd for n, r in self.rails.items()}

    def level(self, name: str, t_abs: int) -> float:
        """Liquidity buffer of a rail at absolute hour t_abs (buffer is valid at buf_time and refills after)."""
        r = self.rails[name]
        if not np.isfinite(r.cap_usd):
            return float("inf")
        return min(r.cap_usd, self.buffer[name] + r.refill_per_h * max(0, t_abs - self.buf_time))

    def _advance_buffers(self, t: int):
        for n, r in self.rails.items():
            if np.isfinite(r.cap_usd):
                self.buffer[n] = self.level(n, t)
        self.buf_time = max(self.buf_time, t)

    def reset(self, *, seed=None, options=None):
        if seed is not None:
            self._seed_streams(seed)
            self.world = None
        if self.world is None:
            self._new_world()
        while True:
            tr = next_transfer(self.gen, self.rng_arrivals)
            t0 = self.clock + tr.gap_h
            if t0 + tr.deadline_h + H + 2 < self.world.T:
                break
            self._new_world()
        self.clock = t0
        self.transfer = tr
        self.A, self.D, self.t0, self.k = tr.amount, tr.deadline_h, t0, 0
        return self._obs(), {}

    # ---- derived quantities ----------------------------------------------------------------------
    @property
    def t(self) -> int:
        return self.t0 + self.k

    def send_mask(self, tau: int = 0) -> np.ndarray:
        """Rails that may be used `tau` ticks from now: eligible and liquid."""
        m = np.zeros(K, dtype=bool)
        for i, n in enumerate(ALL_RAILS):
            if n not in self.eligible:
                continue
            m[i] = self.level(n, self.t + tau) >= self.A
        if not m.any():                       # last resort so the mask is never empty
            m[ALL_RAILS.index("CB")] = "CB" in self.eligible
        return m

    def max_wait_ticks(self) -> int:
        m = self.send_mask()
        fastest = min((self.rails[n].lat_p90 for i, n in enumerate(ALL_RAILS) if m[i]), default=0.0)
        return max(0, int(np.floor(self.D - fastest)))

    def wait_allowed(self) -> bool:
        return self.k + 1 <= self.max_wait_ticks()

    def action_masks(self) -> np.ndarray:
        return np.concatenate([[self.wait_allowed()], self.send_mask()])

    def cost_now(self) -> np.ndarray:
        return np.array([float(self.world.cost_bps(n, self.t, self.A)) for n in ALL_RAILS])

    def forecast_matrix(self, kind: str | None = None, noise: float | None = None) -> np.ndarray:
        kind = self.forecast_kind if kind is None else kind
        noise = self.forecast_noise if noise is None else noise
        return np.stack([self.world.forecast_bps(kind, n, self.t, self.A, H, noise) for n in ALL_RAILS])

    def expected_penalty(self, rail_idx: int, tau: int) -> float:
        """Expected failure and lateness penalty (bps) for sending `tau` ticks from now.

        Lateness uses the exact lognormal latency: P(L > d) * base + per_hour * E[(L - d)+], where d is
        the time left after the wait. A 0/1 flag at the 90th percentile would let planners wait to the edge
        of the deadline for tiny savings while ignoring the risk they take on."""
        from math import erf, exp, log, sqrt
        r = self.rails[ALL_RAILS[rail_idx]]
        mu = r.lat_mu + (log(1.5) if self.world.stress[min(self.t, self.world.T - 1)] else 0.0)
        sg = r.lat_sigma
        d = self.D - (self.k + tau)
        cdf = lambda z: 0.5 * (1 + erf(z / sqrt(2)))
        mean = exp(mu + sg ** 2 / 2)
        if d <= 0:
            p_late, excess = 1.0, mean - d
        else:
            z = (log(d) - mu) / sg
            p_late = 1 - cdf(z)
            excess = mean * cdf(sg - z) - d * (1 - cdf(z))
        return r.p_fail * FAIL_PEN_BPS + p_late * LATE_BASE_BPS + LATE_PER_H_BPS * excess

    # ---- gym API ---------------------------------------------------------------------------------
    def _obs(self) -> np.ndarray:
        now = np.maximum(self.cost_now(), 1e-6)
        sm = self.send_mask()
        fc = np.maximum(self.forecast_matrix(), 1e-6)
        horizon = max(1, min(H, self.max_wait_ticks() - self.k + 1))
        best_future = fc[:, :horizon].min(axis=1)
        hr = (self.t % 24) / 24 * 2 * np.pi
        v = [np.log10(self.A) / 4, self.D / 72, self.k / self.D, np.sin(hr), np.cos(hr), float(self.wait_allowed())]
        for i, n in enumerate(ALL_RAILS):
            r = self.rails[n]
            v += [np.log(now[i] / 200), min(1.0, self.level(n, self.t) / r.cap_usd) if np.isfinite(r.cap_usd) else 1.0,
                  float(sm[i]), np.log(best_future[i] / now[i])]
        return np.clip(np.nan_to_num(np.array(v, dtype=np.float32)), -20, 20)

    def step(self, action: int):
        a = int(action)
        if a == 0:
            if not self.wait_allowed():
                raise ValueError("wait is not allowed now (deadline too close)")
            self.k += 1
            return self._obs(), 0.0, False, False, {"event": "wait"}
        i = a - 1
        name = ALL_RAILS[i]
        guard(name, self.eligible)            # hard constraint, raises ComplianceViolation
        if not self.send_mask()[i]:
            raise ValueError(f"rail {name} lacks liquidity for {self.A}")
        t = self.t
        cost = float(self.world.cost_bps(name, t, self.A))
        r = self.rails[name]
        p_fail = r.p_fail * (1.5 if self.world.stress[min(t, self.world.T - 1)] else 1.0)
        fail = bool(self.rng_out.random() < p_fail)
        lat = self.world.draw_latency(name, t, self.rng_out) + (FAIL_EXTRA_LAT_H if fail else 0.0)
        late_h = max(0.0, self.k + lat - self.D)
        penalty = (FAIL_PEN_BPS if fail else 0.0) + ((LATE_BASE_BPS + LATE_PER_H_BPS * late_h) if late_h > 0 else 0.0)
        total = cost + penalty
        self._advance_buffers(t)
        if np.isfinite(r.cap_usd):
            self.buffer[name] -= self.A
        info = {"event": "sent", "rail": name, "amount": self.A, "deadline_h": self.D, "wait_h": self.k,
                "t_send": t, "cost_bps": cost, "penalty_bps": penalty, "total_bps": total, "failed": fail,
                "late": late_h > 0, "latency_h": lat, "settle_t": t + lat,
                "regime": "stress" if self.world.stress[min(t, self.world.T - 1)] else "normal"}
        return self._obs(), -total / 100.0, True, False, info
