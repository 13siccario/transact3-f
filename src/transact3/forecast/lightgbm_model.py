"""LightGBM: one model per target, features from all series at the origin."""
from __future__ import annotations

import numpy as np


def fit_predict(X_train, y_train, X_test, params: dict, seed: int) -> np.ndarray:
    import lightgbm as lgb
    # n_jobs=1: avoids an OpenMP clash with torch that hangs on macOS
    m = lgb.LGBMRegressor(random_state=seed, verbose=-1, n_jobs=1, deterministic=True, force_row_wise=True, **params)
    m.fit(X_train, y_train)
    return m.predict(X_test)
