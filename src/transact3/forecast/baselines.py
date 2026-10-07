"""Baselines. Each returns one-step-ahead predictions at every origin index in `test_idx`,
fitted only on rows < `train_end` (exclusive) of the target series."""
from __future__ import annotations

import numpy as np
import pandas as pd

ZERO_RW = {"fx_return"}   # random walk in price = zero expected return


def random_walk(y: pd.Series, target: str, test_idx: np.ndarray) -> np.ndarray:
    return np.zeros(len(test_idx)) if target in ZERO_RW else y.to_numpy()[test_idx]


def last_value(y: pd.Series, test_idx: np.ndarray) -> np.ndarray:
    return y.to_numpy()[test_idx]


def rolling_median(y: pd.Series, test_idx: np.ndarray, window: int) -> np.ndarray:
    return y.rolling(window, min_periods=1).median().to_numpy()[test_idx]


def fit_ar(y: np.ndarray, p: int, horizon: int = 1):
    """OLS AR(p) with intercept: y[t+h] on y[t], ..., y[t-p+1]."""
    X = np.column_stack([y[p - 1 - j: len(y) - horizon - j] for j in range(p)])
    t = y[p - 1 + horizon:]
    A = np.column_stack([np.ones(len(X)), X])
    coef, *_ = np.linalg.lstsq(A, t, rcond=None)
    return coef


def ar_predict(y: np.ndarray, coef: np.ndarray, test_idx: np.ndarray) -> np.ndarray:
    p = len(coef) - 1
    return np.array([coef[0] + sum(coef[1 + j] * y[i - j] for j in range(p)) for i in test_idx])


def fit_garch(returns: np.ndarray):
    """GARCH(1,1) with constant mean on returns (scaled x100 for the optimiser)."""
    from arch import arch_model
    res = arch_model(returns * 100, mean="Constant", vol="GARCH", p=1, q=1, rescale=False).fit(disp="off")
    p = res.params
    return {"mu": p["mu"] / 100, "omega": p["omega"] / 1e4, "alpha": p["alpha[1]"], "beta": p["beta[1]"],
            "var0": float(np.var(returns))}


def garch_sigma(returns: np.ndarray, g: dict, test_idx: np.ndarray) -> np.ndarray:
    """One-step-ahead sigma at each origin via the variance recursion with FIXED parameters.
    sigma2[t+1] = omega + alpha*(r_t - mu)^2 + beta*sigma2[t]; uses returns up to t only."""
    n = len(returns)
    s2 = np.empty(n)
    prev = g["var0"]
    for t in range(n):
        s2[t] = g["omega"] + g["alpha"] * (returns[t] - g["mu"]) ** 2 + g["beta"] * prev   # forecast for t+1
        prev = s2[t]
    return np.sqrt(s2[test_idx])
