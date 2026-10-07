"""Collector interface shared by synthetic generators and real sources.

Every frame a collector returns has a UTC `ts` column, a `source_kind`
column ('synthetic' or 'real') and series-specific value columns. The
`source_kind` flag travels with the data into the API and UI so synthetic
numbers can never be mistaken for observations.
"""
from __future__ import annotations

from abc import ABC, abstractmethod

import numpy as np
import pandas as pd

SYNTHETIC = "synthetic"
REAL = "real"


class Collector(ABC):
    name: str          # dataset name, e.g. "fx"
    frequency: str     # pandas offset alias, e.g. "1h"

    @abstractmethod
    def collect(self, start: str, end: str, rng: np.random.Generator) -> pd.DataFrame:
        """Return raw observations in [start, end] with `ts` (UTC) and `source_kind`."""


class RealSourceUnavailable(RuntimeError):
    """Raised by real collectors until Phase 0 confirms a source (go decision)."""


def hourly_index(start: str, end: str, freq: str = "1h") -> pd.DatetimeIndex:
    return pd.date_range(start, end, freq=freq, tz="UTC", inclusive="left")
