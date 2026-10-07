"""Transfer generator: arrivals, sizes and deadlines."""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class GeneratorConfig:
    rate_per_h: float = 0.5                 # mean arrivals per hour
    size_median_usd: float = 1_000.0
    size_sigma: float = 1.0                 # lognormal sigma of size
    size_min: float = 50.0
    size_max: float = 50_000.0
    deadlines_h: tuple = (6, 24, 72)
    deadline_probs: tuple = (0.3, 0.4, 0.3)


@dataclass(frozen=True)
class Transfer:
    gap_h: int          # whole hours since the previous transfer (0 allowed)
    amount: float
    deadline_h: int


def size_segment(amount: float) -> str:
    return "small" if amount < 500 else "medium" if amount < 5_000 else "large"


def next_transfer(cfg: GeneratorConfig, rng: np.random.Generator) -> Transfer:
    gap = int(rng.exponential(1.0 / cfg.rate_per_h))
    amount = float(np.clip(rng.lognormal(np.log(cfg.size_median_usd), cfg.size_sigma), cfg.size_min, cfg.size_max))
    deadline = int(rng.choice(cfg.deadlines_h, p=cfg.deadline_probs))
    return Transfer(gap, round(amount, 2), deadline)
