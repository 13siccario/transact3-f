"""Walk-forward validation: expanding window, weekly refits, one-step-ahead forecasts.

Leakage rules enforced here:
- training origins end at a - horizon, so every training label is observed by the first test origin a;
- scaling, AR and GARCH parameters are fitted on data up to index a only;
- test forecasts at origin t use only features and series values up to t.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

from ..config import Config
from ..costs.regimes import label_regimes
from . import baselines as bl
from . import lightgbm_model, lstm_model
from .panel import build_features, build_panel, build_targets
from .tests import dm_test


def walk_forward_folds(valid: np.ndarray, initial_frac: float, block: int, horizon: int):
    """Yield (train_origins, test_origins). Train labels are all observed by the first test origin."""
    first_test = int(valid[0] + initial_frac * len(valid))
    last = int(valid[-1])
    for a in range(first_test, last + 1, block):
        test = valid[(valid >= a) & (valid < min(a + block, last + 1))]
        train = valid[valid + horizon <= a]
        if len(test) and len(train):
            yield train, test


def run_forecasts(cfg: Config, processed: dict[str, pd.DataFrame], source_kind: str) -> pd.DataFrame:
    h = cfg["horizon"]
    targets, exog = cfg["targets"], cfg["exog"]
    panel = build_panel(processed, cfg["pool_id"])
    feats = build_features(panel, targets + exog, cfg["lags"], cfg["windows"])
    Y = build_targets(panel, targets, h)
    N = len(panel)
    warm = max(max(cfg["lags"]), max(cfg["windows"]), cfg["lstm"]["seq_len"] - 1)
    valid = np.arange(warm, N - h)
    Z = panel[targets + exog].to_numpy()
    tcols = list(range(len(targets)))
    models = cfg["models"]
    delta_targets = set(cfg.get("delta_targets", []))
    out = []

    for fold, (train, test) in enumerate(walk_forward_folds(valid, cfg["initial_train_frac"], cfg["test_block_hours"], h)):
        a = int(test[0])
        preds: dict[tuple[str, str], np.ndarray] = {}
        for j, tgt in enumerate(targets):
            y = panel[tgt]
            if "random_walk" in models:
                preds[("random_walk", tgt)] = bl.random_walk(y, tgt, test)
            if "last_value" in models and tgt in bl.ZERO_RW | {"fx_vol"}:
                preds[("last_value", tgt)] = bl.last_value(y, test)
            if "rolling_median" in models:
                preds[("rolling_median", tgt)] = bl.rolling_median(y, test, cfg["rolling_median_window"])
            if "ar" in models:
                coef = bl.fit_ar(y.to_numpy()[: a + 1], cfg["ar_order"], h)
                preds[("ar", tgt)] = bl.ar_predict(y.to_numpy(), coef, test)
            if "garch" in models and tgt in ("fx_return", "fx_vol"):
                r = panel["fx_return"].to_numpy()
                g = bl.fit_garch(r[: a + 1])
                sig = bl.garch_sigma(r, g, test)
                preds[("garch", tgt)] = np.full(len(test), g["mu"]) if tgt == "fx_return" else sig * np.sqrt(2 / np.pi)
            if "lightgbm" in models:
                base = y.to_numpy() if tgt in delta_targets else np.zeros(N)
                p = lightgbm_model.fit_predict(
                    feats.iloc[train], Y[tgt].to_numpy()[train] - base[train], feats.iloc[test], cfg["lightgbm"], cfg["seed"])
                preds[("lightgbm", tgt)] = p + base[test]
        if "lstm" in models:
            P = lstm_model.fit_predict(Z, tcols, train, test, h, cfg["lstm"], cfg["seed"],
                                       delta=[t in delta_targets for t in targets])
            for j, tgt in enumerate(targets):
                preds[("lstm", tgt)] = P[:, j]

        for (model, tgt), p in preds.items():
            out.append(pd.DataFrame({
                "origin_ts": panel.index[test], "target_ts": panel.index[test + h], "fold": fold,
                "target": tgt, "model": model, "y_true": Y[tgt].to_numpy()[test], "y_pred": p}))
    df = pd.concat(out, ignore_index=True)
    df["regime"] = label_regimes(df["origin_ts"], source_kind).to_numpy()   # regime at the forecast origin
    return df


def score(preds: pd.DataFrame, benchmark: str, horizon: int) -> pd.DataFrame:
    """RMSE, MAE, skill vs benchmark (1 - MSE ratio) and DM test, overall and by regime."""
    preds = preds.assign(err=preds["y_true"] - preds["y_pred"])
    bench = preds[preds["model"] == benchmark][["origin_ts", "target", "err"]].rename(columns={"err": "err_b"})
    m = preds.merge(bench, on=["origin_ts", "target"])
    rows = []
    for regime in ["all", *sorted(preds["regime"].unique())]:
        sub = m if regime == "all" else m[m["regime"] == regime]
        for (tgt, model), g in sub.groupby(["target", "model"]):
            mse, mse_b = (g["err"] ** 2).mean(), (g["err_b"] ** 2).mean()
            stat, p = (np.nan, np.nan) if model == benchmark else dm_test(g["err_b"].to_numpy(), g["err"].to_numpy(), horizon)
            rows.append({"regime": regime, "target": tgt, "model": model, "n": len(g),
                         "rmse": float(np.sqrt(mse)), "mae": float(g["err"].abs().mean()),
                         "skill": float(1 - mse / mse_b) if mse_b > 0 else np.nan, "dm_stat": stat, "dm_p": p})
    return pd.DataFrame(rows)


def save(cfg: Config, preds: pd.DataFrame, metrics: pd.DataFrame, source_kind: str, data_hash: str) -> Path:
    out = Path(cfg["out_dir"])
    out.mkdir(parents=True, exist_ok=True)
    preds.to_parquet(out / "forecasts.parquet", index=False)
    metrics.to_parquet(out / "metrics.parquet", index=False)
    z = (preds[preds["model"] == cfg["z_model"]].pivot(index="origin_ts", columns="target", values="y_pred")
         .add_prefix("z_").reset_index())
    z.to_parquet(out / "z.parquet", index=False)
    (out / "meta.json").write_text(json.dumps({
        "config": cfg.path.name, "config_hash": cfg.hash, "data_config_hash": data_hash, "source_kind": source_kind,
        "seed": cfg.seed, "horizon": cfg["horizon"], "benchmark": cfg["benchmark"], "z_model": cfg["z_model"],
        "origins": [str(preds["origin_ts"].min()), str(preds["origin_ts"].max())],
        "folds": int(preds["fold"].nunique())}, indent=2))
    return out
