"""Market world: hourly rail-cost paths, regimes, and forecast providers.

Forecast kinds (the ablation axis):
  none     persistence: assume today's cost holds
  model    the conditional expectation under the world's own dynamics (an ideal model of the
           predictable part: mean reversion, daily cycle, regime persistence); future shocks unknown
  noisy    perfect foresight corrupted by multiplicative log-normal noise
  perfect  the realised future
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .rails import ALL_RAILS, Rail

P_ENTER_STRESS = 0.003    # per hour
P_EXIT_STRESS = 0.012


@dataclass
class Empirical:
    """Optional empirical stablecoin cost process (Paper 2 robustness check).

    `bps(amount)` returns realised SC cost in bps per hour; `pred_bps(amount)` the one-hour-ahead
    model forecast built from Phase 3's z(t)."""
    bps: callable
    pred_bps: callable
    length: int


class World:
    def __init__(self, rails: dict[str, Rail], length: int, rng: np.random.Generator, empirical: Empirical | None = None):
        self.rails = rails
        self.T = empirical.length if empirical else length
        self.emp = empirical
        self.rng = rng
        T = self.T
        # regime path (two-state Markov chain)
        s = np.zeros(T, dtype=bool)
        for t in range(1, T):
            s[t] = (rng.random() < 1 - P_EXIT_STRESS) if s[t - 1] else (rng.random() < P_ENTER_STRESS)
        self.stress = s
        # AR(1) log-cost shocks per rail, and the multiplier path
        self.x = {}
        self.mult = {}
        self.fe = {}
        hours = np.arange(T) % 24
        for n in ALL_RAILS:
            r = rails[n]
            x = np.zeros(T)
            for t in range(1, T):
                x[t] = r.phi * x[t - 1] + r.vol * rng.standard_normal()
            diurnal = 1 + r.diurnal_amp * np.sin(2 * np.pi * (hours - r.diurnal_phase - 6) / 24)
            self.x[n] = x
            self.fe[n] = rng.standard_normal(T)        # fixed forecast error per rail and hour
            self.mult[n] = np.exp(x) * diurnal * np.where(s, r.stress_mult, 1.0)

    # ---- realised costs -------------------------------------------------------------------
    def _cost(self, rail: Rail, mult, amount: float):
        fixed = rail.fixed_usd / amount * 1e4
        var = rail.bps + rail.fx_bps
        if rail.fixed_is_gas:
            return fixed * mult + var * (1 + 0.25 * (mult - 1))
        return (fixed + var) * mult

    def cost_bps(self, name: str, t, amount: float):
        if name == "SC" and self.emp is not None:
            return self.emp.bps(amount)[np.minimum(t, self.T - 1)]
        return self._cost(self.rails[name], self.mult[name][np.minimum(t, self.T - 1)], amount)

    # ---- forecasts ------------------------------------------------------------------------
    def _expected_mult(self, name: str, t0: int, h: np.ndarray) -> np.ndarray:
        r = self.rails[name]
        hours = (t0 + h) % 24
        diurnal = 1 + r.diurnal_amp * np.sin(2 * np.pi * (hours - r.diurnal_phase - 6) / 24)
        var = r.vol ** 2 * (1 - r.phi ** (2 * h)) / (1 - r.phi ** 2)
        shock = np.exp(r.phi ** h * self.x[name][t0] + 0.5 * var)
        pi_s = P_ENTER_STRESS / (P_ENTER_STRESS + P_EXIT_STRESS)
        p_s = pi_s + (float(self.stress[t0]) - pi_s) * (1 - P_ENTER_STRESS - P_EXIT_STRESS) ** h
        return shock * diurnal * (1 + (r.stress_mult - 1) * p_s)

    def forecast_bps(self, kind: str, name: str, t0: int, amount: float, H: int, noise: float = 0.0) -> np.ndarray:
        """Forecast cost (bps) for ticks t0..t0+H-1. Index 0 is the known current cost."""
        h = np.arange(H)
        now = float(self.cost_bps(name, t0, amount))
        if kind == "none":
            return np.full(H, now)
        real = np.asarray(self.cost_bps(name, t0 + h, amount), dtype=float)
        if kind == "perfect":
            return real
        if kind == "noisy":
            # The same future hour always carries the same error, so re-planning does not chase fresh noise.
            out = real * np.exp(noise * self.fe[name][np.minimum(t0 + h, self.T - 1)])
            out[0] = now
            return out
        if kind == "model":
            if name == "SC" and self.emp is not None:
                out = np.full(H, now)
                if H > 1:
                    out[1:] = self.emp.pred_bps(amount)[min(t0, self.T - 1)]
                return out
            m = self._expected_mult(name, t0, h)
            out = np.asarray(self._cost(self.rails[name], m, amount), dtype=float)
            out[0] = now
            return out
        raise ValueError(f"unknown forecast kind '{kind}'")

    # ---- latency and failure --------------------------------------------------------------
    def draw_latency(self, name: str, t: int, rng: np.random.Generator) -> float:
        r = self.rails[name]
        lat = float(rng.lognormal(r.lat_mu, r.lat_sigma))
        return lat * (1.5 if self.stress[min(t, self.T - 1)] else 1.0)
