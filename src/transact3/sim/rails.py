"""Payment rails for the Paper 1 simulator.

CB   correspondent banking (conventional cross-border)
LR   linked instant-payment rails between domestic systems
SC   stablecoin rail (on-chain, gas-driven fixed cost)
CBDC central-bank-digital-currency bridge, present only in CBDC scenarios

EVERY NUMBER HERE IS A PROVISIONAL PLACEHOLDER. Phase 1 calls for calibrating these from public
benchmarks (World Bank RPW, RBI remittance survey, BIS/CPMI speed statistics). Until that is done
from primary documents, results show how methods compare in a plausible world, not the real one.
"""
from __future__ import annotations

from dataclasses import dataclass, replace

import numpy as np

ALL_RAILS = ["CB", "LR", "SC", "CBDC"]


@dataclass(frozen=True)
class Rail:
    name: str
    fixed_usd: float        # per-transfer fixed cost
    bps: float              # proportional fee
    fx_bps: float           # FX spread and margin
    lat_mu: float           # lognormal latency (hours): mean of log
    lat_sigma: float
    p_fail: float           # chance a send fails and must be retried
    cap_usd: float          # liquidity buffer capacity (inf = unlimited)
    refill_per_h: float     # buffer refill rate, USD per hour
    vol: float              # sigma of the AR(1) log-cost shock
    phi: float = 0.97       # persistence of the shock
    stress_mult: float = 1.5
    diurnal_amp: float = 0.0
    diurnal_phase: float = 3.0   # hour (UTC) at which cost is lowest
    fixed_is_gas: bool = False   # fixed cost scales fully with the shock; variable part only partly

    @property
    def lat_p90(self) -> float:
        return float(np.exp(self.lat_mu + 1.2816 * self.lat_sigma))


DEFAULT_RAILS: dict[str, Rail] = {
    "CB": Rail("CB", fixed_usd=4.0, bps=80, fx_bps=120, lat_mu=np.log(24), lat_sigma=0.5, p_fail=0.02,
               cap_usd=float("inf"), refill_per_h=0, vol=0.03, stress_mult=1.15),
    "LR": Rail("LR", fixed_usd=1.5, bps=40, fx_bps=30, lat_mu=np.log(1.5), lat_sigma=0.4, p_fail=0.03,
               cap_usd=25_000, refill_per_h=500, vol=0.05, stress_mult=1.3, diurnal_amp=0.08),
    "SC": Rail("SC", fixed_usd=9.0, bps=45, fx_bps=15, lat_mu=np.log(0.5), lat_sigma=0.5, p_fail=0.01,
               cap_usd=60_000, refill_per_h=600, vol=0.10, stress_mult=1.8, diurnal_amp=0.30, fixed_is_gas=True),
    "CBDC": Rail("CBDC", fixed_usd=0.5, bps=10, fx_bps=20, lat_mu=np.log(0.2), lat_sigma=0.4, p_fail=0.005,
                 cap_usd=100_000, refill_per_h=3_000, vol=0.03, stress_mult=1.1),
}

# CBDC scenarios change the bridge's capacity. "none" removes it (the compliance filter also hides it).
CBDC_SCENARIOS = {
    "none": None,
    "pilot": {"cap_usd": 5_000, "refill_per_h": 100},
    "mature": {"cap_usd": 200_000, "refill_per_h": 5_000},
}


def rails_for(cbdc: str = "none", liquidity_scale: float = 1.0) -> dict[str, Rail]:
    rails = dict(DEFAULT_RAILS)
    over = CBDC_SCENARIOS[cbdc]
    if over:
        rails["CBDC"] = replace(rails["CBDC"], **over)
    out = {}
    for n, r in rails.items():
        if np.isfinite(r.cap_usd):
            r = replace(r, cap_usd=r.cap_usd * liquidity_scale, refill_per_h=r.refill_per_h * liquidity_scale)
        out[n] = r
    return out


def perturb(rails: dict[str, Rail], rng: np.random.Generator, spread: float = 0.25) -> dict[str, Rail]:
    """One parameter draw for sensitivity analysis: multiplicative lognormal jitter on costs, latency, failure."""
    f = lambda: float(np.exp(rng.normal(0, spread)))
    out = {}
    for n, r in rails.items():
        out[n] = replace(r, fixed_usd=r.fixed_usd * f(), bps=r.bps * f(), fx_bps=r.fx_bps * f(),
                         lat_mu=r.lat_mu + rng.normal(0, spread / 2), p_fail=min(0.2, r.p_fail * f()),
                         vol=r.vol * f())
    return out
