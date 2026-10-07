"""Collect -> raw parquet -> clean -> processed parquet + DuckDB, with a manifest."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import duckdb
import numpy as np
import pandas as pd

from ..config import Config
from .cleaning import align_hourly, fill_short_gaps, flag_outliers
from .collectors.fx import RealFX, SyntheticFX
from .collectors.gas import RealGas, SyntheticGas, SyntheticPeg
from .collectors.pools import RealPools, SyntheticPools
from .collectors.usdt_inr import RealUsdtInr, SyntheticUsdtInr

KEYS = {"fx": ["pair"], "usdt_inr": [], "pools": ["pool_id"], "gas": [], "peg": ["coin"]}
VALUE_COL = {"fx": "mid", "usdt_inr": "price_inr", "pools": "mid_price", "gas": "base_fee_gwei", "peg": "price_usd"}


def _collectors(cfg: Config, rng: np.random.Generator):
    start, end = cfg["period"]["start"], cfg["period"]["end"]
    if cfg.mode == "synthetic":
        fx = SyntheticFX(cfg["fx_pairs"])
        fx_df = fx.collect(start, end, rng)
        yield fx, fx_df
        for c in (SyntheticUsdtInr(fx_df), SyntheticPools(), SyntheticGas(), SyntheticPeg()):
            yield c, c.collect(start, end, rng)
    else:
        for c in (RealFX(), RealUsdtInr(), RealPools(), RealGas()):
            yield c, c.collect(start, end, rng)  # raises RealSourceUnavailable until wired


def clean(name: str, df: pd.DataFrame, cfg: Config) -> pd.DataFrame:
    c = cfg["cleaning"]
    start, end = cfg["period"]["start"], cfg["period"]["end"]
    df = align_hourly(df, KEYS[name], start, end)
    col = VALUE_COL[name]
    keys = KEYS[name]
    grp = df.groupby(keys, group_keys=False) if keys else None
    flag = (grp[col].apply(lambda s: flag_outliers(s, c["outlier_window_hours"], c["outlier_mad_k"]))
            if grp is not None else flag_outliers(df[col], c["outlier_window_hours"], c["outlier_mad_k"]))
    df["is_outlier"] = flag
    value_cols = [x for x in df.select_dtypes("number").columns if x not in ("was_missing",)]
    for vc in value_cols:
        df[vc] = (df.groupby(keys, group_keys=False)[vc].apply(lambda s: fill_short_gaps(s, c["max_ffill_hours"]))
                  if keys else fill_short_gaps(df[vc], c["max_ffill_hours"]))
    return df


def derive_premium(processed: dict[str, pd.DataFrame]) -> pd.DataFrame:
    fx = processed["fx"]
    ref = fx[fx["pair"] == "USDINR"][["ts", "mid"]].rename(columns={"mid": "usd_inr_ref"})
    out = processed["usdt_inr"][["ts", "price_inr", "source_kind"]].merge(ref, on="ts", how="left")
    out["premium_pct"] = (out["price_inr"] / out["usd_inr_ref"] - 1) * 100
    return out


def build(cfg: Config) -> dict:
    rng = np.random.default_rng(cfg.seed)
    raw_dir, proc_dir = Path(cfg["outputs"]["raw_dir"]), Path(cfg["outputs"]["processed_dir"])
    raw_dir.mkdir(parents=True, exist_ok=True)
    proc_dir.mkdir(parents=True, exist_ok=True)

    processed: dict[str, pd.DataFrame] = {}
    manifest = {"config": cfg.path.name, "config_hash": cfg.hash, "seed": cfg.seed, "mode": cfg.mode,
                "built_at": datetime.now(timezone.utc).isoformat(), "datasets": {}}
    for collector, raw in _collectors(cfg, rng):
        raw.to_parquet(raw_dir / f"{collector.name}.parquet", index=False)
        cleaned = clean(collector.name, raw, cfg)
        processed[collector.name] = cleaned
        manifest["datasets"][collector.name] = {
            "rows": int(len(cleaned)), "source_kind": str(cleaned["source_kind"].iloc[0]),
            "missing_rows": int(cleaned["was_missing"].sum()), "outliers_flagged": int(cleaned["is_outlier"].sum()),
        }
    processed["premium"] = derive_premium(processed)
    manifest["datasets"]["premium"] = {"rows": int(len(processed["premium"])), "source_kind": cfg.mode}

    con = duckdb.connect(str(proc_dir / "transact3.duckdb"))
    for name, df in processed.items():
        df.to_parquet(proc_dir / f"{name}.parquet", index=False)
        con.execute(f"CREATE OR REPLACE TABLE {name} AS SELECT * FROM read_parquet('{proc_dir / f'{name}.parquet'}')")
    con.close()
    (proc_dir / "manifest.json").write_text(json.dumps(manifest, indent=2))
    return manifest
