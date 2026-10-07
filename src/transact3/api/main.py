"""FastAPI layer over the processed datasets and cost engine (read-only)."""
from __future__ import annotations

import json
import os
from functools import lru_cache
from pathlib import Path

import pandas as pd
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from ..costs.paths import PATHS, TERMS, cost_table, load_params
from ..costs.regimes import label_regimes
from ..data.calendar import load_events

DISCLAIMER = "Research findings, not legal or financial advice."
PROCESSED = Path(os.environ.get("TRANSACT3_PROCESSED", "data/processed"))
COSTS_FILE = Path(os.environ.get("TRANSACT3_COSTS", "configs/costs.yaml"))

app = FastAPI(title="transact3 API", version="0.1.0")
app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"], allow_methods=["GET"], allow_headers=["*"])


@lru_cache(maxsize=1)
def _state() -> dict:
    manifest_file = PROCESSED / "manifest.json"
    if not manifest_file.exists():
        raise HTTPException(503, "No datasets built yet. Run `make data`.")
    manifest = json.loads(manifest_file.read_text())
    processed = {n: pd.read_parquet(PROCESSED / f"{n}.parquet") for n in manifest["datasets"]}
    params = load_params(COSTS_FILE)
    costs = cost_table(processed, params)
    kind = manifest["mode"]
    costs["regime"] = label_regimes(costs["ts"], kind)
    return {"manifest": manifest, "params": params, "costs": costs, "kind": kind}


def _envelope(data, st) -> dict:
    return {"source_kind": st["kind"], "config_hash": st["manifest"]["config_hash"],
            "cost_params": st["params"]["provenance"], "disclaimer": DISCLAIMER, "data": data}


def _breakdown(df: pd.DataFrame) -> dict:
    return {t: float(df[t].mean()) for t in TERMS} | {
        "total": float(df["total"].mean()), "total_ex_prem": float(df["total_ex_prem"].mean()),
        "total_bps": float(df["total_bps"].mean())}


@app.get("/api/meta")
def meta():
    st = _state()
    c = st["costs"]
    return _envelope({
        "paths": PATHS, "terms": TERMS, "sizes": st["params"]["transfer_sizes_usd"],
        "regimes": sorted(c["regime"].unique().tolist()),
        "start": c["ts"].min().isoformat(), "end": c["ts"].max().isoformat(),
        "datasets": st["manifest"]["datasets"],
    }, st)


@app.get("/api/costs/anatomy")
def anatomy(regime: str = Query("all")):
    """Mean cost breakdown per path and transfer size, optionally within one regime."""
    st = _state()
    c = st["costs"]
    if regime != "all":
        c = c[c["regime"] == regime]
        if c.empty:
            raise HTTPException(404, f"no rows for regime '{regime}'")
    rows = []
    for (path, amount), g in c.groupby(["path", "amount"]):
        rows.append({"path": path, "label": PATHS[path], "amount": amount, "n_hours": len(g), **_breakdown(g)})
    return _envelope(rows, st)


@app.get("/api/costs/timeline")
def timeline(path: str = "P1", amount: float = 1000):
    """Daily mean all-in cost (bps, excluding premium) with event markers."""
    st = _state()
    c = st["costs"]
    if path not in PATHS:
        raise HTTPException(404, f"unknown path '{path}'")
    g = c[(c["path"] == path) & (c["amount"] == amount)]
    if g.empty:
        raise HTTPException(404, "no rows for that path and amount")
    daily = (g.set_index("ts")[["total_bps", "total_ex_prem"]].resample("1D").mean().reset_index())
    prem = g.set_index("ts")["c_prem"].resample("1D").mean().reset_index(drop=True) / amount * 1e4
    series = [{"date": r.ts.date().isoformat(), "total_bps": float(r.total_bps), "premium_bps": float(p),
               "regime": str(g[g["ts"].dt.date == r.ts.date()]["regime"].iloc[0])}
              for r, p in zip(daily.itertuples(), prem)]
    ev = load_events()
    events = [{"id": e.id, "date": e.date.date().isoformat() if pd.notna(e.date) else None,
               "title": e.title, "status": e.status, "primary_source": e.primary_source}
              for e in ev.itertuples()]
    return _envelope({"series": series, "events": events}, st)


# ---- forecasts (Phase 3) -------------------------------------------------------------------------

FORECAST_DIR = Path(os.environ.get("TRANSACT3_FORECAST", "data/processed/forecast"))
TARGET_NAMES = {
    "fx_return": "USD/INR hourly return", "fx_vol": "USD/INR volatility", "fx_spread": "USD/INR spread",
    "gas_gwei": "Network fee (gas)", "peg_dev": "Stablecoin peg gap", "premium_pct": "Local price premium",
    "slip_bps": "Pool price impact",
}


@lru_cache(maxsize=1)
def _forecast() -> dict:
    meta_file = FORECAST_DIR / "meta.json"
    if not meta_file.exists():
        raise HTTPException(503, "No forecasts yet. Run `make forecast`.")
    return {"meta": json.loads(meta_file.read_text()),
            "metrics": pd.read_parquet(FORECAST_DIR / "metrics.parquet"),
            "preds": pd.read_parquet(FORECAST_DIR / "forecasts.parquet"),
            "z": pd.read_parquet(FORECAST_DIR / "z.parquet")}


def _fc_envelope(data, f) -> dict:
    return {"source_kind": f["meta"]["source_kind"], "config_hash": f["meta"]["config_hash"],
            "cost_params": "n/a", "disclaimer": DISCLAIMER, "data": data}


def _clean(df: pd.DataFrame) -> list[dict]:
    return json.loads(df.to_json(orient="records"))   # NaN -> null


@app.get("/api/forecast/summary")
def forecast_summary(regime: str = Query("all")):
    """Skill vs the benchmark and Diebold-Mariano p-values per target and model."""
    f = _forecast()
    m = f["metrics"]
    if regime not in set(m["regime"]):
        raise HTTPException(404, f"no results for regime '{regime}'")
    m = m[m["regime"] == regime].copy()
    m["target_name"] = m["target"].map(TARGET_NAMES)
    meta = f["meta"] | {"targets": TARGET_NAMES, "models": sorted(m["model"].unique().tolist()),
                        "regimes": sorted(f["metrics"]["regime"].unique().tolist())}
    return _fc_envelope({"meta": meta, "rows": _clean(m)}, f)


@app.get("/api/forecast/series")
def forecast_series(target: str, model: str = "lightgbm", days: int = 7):
    """Hourly actual, benchmark and chosen-model forecast for the last `days` days of the test period."""
    f = _forecast()
    p = f["preds"]
    if target not in TARGET_NAMES:
        raise HTTPException(404, f"unknown target '{target}'")
    bench = f["meta"]["benchmark"]
    sub = p[(p["target"] == target) & p["model"].isin([model, bench])]
    if sub.empty or model not in set(p["model"]):
        raise HTTPException(404, f"no forecasts for {target}/{model}")
    wide = sub.pivot_table(index=["target_ts", "y_true", "regime"], columns="model", values="y_pred").reset_index()
    wide = wide[wide["target_ts"] >= wide["target_ts"].max() - pd.Timedelta(days=days)]
    wide = wide.rename(columns={model: "model_pred", bench: "benchmark_pred"})
    wide["target_ts"] = wide["target_ts"].astype(str)
    return _fc_envelope({"target": target, "model": model, "benchmark": bench,
                         "points": _clean(wide[["target_ts", "y_true", "regime", "model_pred", "benchmark_pred"]])}, f)


@app.get("/api/forecast/z")
def forecast_z():
    """Latest forecast vector z(t): what the routers receive at the most recent test origin."""
    f = _forecast()
    last = f["z"].iloc[-1]
    items = [{"target": t, "name": TARGET_NAMES[t], "value": float(last[f"z_{t}"])} for t in TARGET_NAMES]
    return _fc_envelope({"origin_ts": str(last["origin_ts"]), "model": f["meta"]["z_model"], "items": items}, f)


# ---- results, replay and simulation (Phase 4) ------------------------------------------------------
import re  # noqa: E402

from ..config import load_config  # noqa: E402
from ..eval import replay as _rp  # noqa: E402
from ..eval import simulate as _sm  # noqa: E402
from ..routing.compliance import load_rules  # noqa: E402

RESULT_DIRS = {"paper1": Path("paper1"), "paper2": Path("paper2")}
REPLAY_CONFIG = Path(os.environ.get("TRANSACT3_REPLAY_CONFIG", "configs/replay.yaml"))


@lru_cache(maxsize=1)
def _replay():
    cfg = load_config(REPLAY_CONFIG)
    manifest_file = PROCESSED / "manifest.json"
    if not manifest_file.exists() or not (FORECAST_DIR / "z.parquet").exists():
        raise HTTPException(503, "Run `make data forecast` first.")
    manifest = json.loads(manifest_file.read_text())
    processed = {n: pd.read_parquet(PROCESSED / f"{n}.parquet") for n in manifest["datasets"]}
    data = _rp.build_replay_data(processed, load_params(COSTS_FILE), pd.read_parquet(FORECAST_DIR / "z.parquet"), manifest["mode"])
    return {"cfg": cfg, "data": data, "rules": load_rules(), "manifest": manifest}


def _sim_envelope(data, r) -> dict:
    return {"source_kind": r["data"].source_kind, "config_hash": r["manifest"]["config_hash"], "cost_params": "provisional",
            "disclaimer": DISCLAIMER, "data": data}


@app.get("/api/results")
def results_index():
    out = []
    for paper, d in RESULT_DIRS.items():
        for f in sorted((d / "tables").glob("*.md")) if (d / "tables").exists() else []:
            out.append({"paper": paper, "name": f.stem, "caption": f.read_text().split("\n")[0].strip("*")})
    return {"disclaimer": DISCLAIMER, "data": out}


@app.get("/api/results/{paper}/{name}")
def result_table(paper: str, name: str):
    if paper not in RESULT_DIRS or not re.fullmatch(r"[a-z0-9_]+", name):
        raise HTTPException(404, "unknown table")
    csv = RESULT_DIRS[paper] / "tables" / f"{name}.csv"
    if not csv.exists():
        raise HTTPException(404, "unknown table")
    df = pd.read_csv(csv)
    caption = (RESULT_DIRS[paper] / "tables" / f"{name}.md").read_text().split("\n")[0].strip("*")
    return {"disclaimer": DISCLAIMER, "data": {"caption": caption, "columns": list(df.columns), "rows": _clean(df)}}


@app.get("/api/simulate/meta")
def simulate_meta():
    r = _replay()
    d, rules = r["data"], r["rules"]
    return _sim_envelope({
        "start": d.ts[0].isoformat(), "end": d.ts[-1].isoformat(), "hours": len(d.ts),
        "policies": _sm.POLICIES, "default_scenario": rules.default_scenario,
        "scenarios": {s: rules.eligible_paths(s) for s in rules.scenarios}, "paths": PATHS,
        "latency_h": r["cfg"]["latency_h"], "rules_version": rules.version, "rules_reviewed": bool(rules.reviewed_by)}, r)


@app.get("/api/simulate")
def simulate(amount: float = Query(1000, ge=50, le=100_000), deadline_h: int = Query(24, ge=1, le=168),
             count: int = Query(5, ge=1, le=30), interval_h: int = Query(24, ge=1, le=168),
             start_ts: str | None = None, scenario: str | None = None,
             policies: str = ",".join(_sm.POLICIES)):
    r = _replay()
    d, rules = r["data"], r["rules"]
    pols = [p for p in policies.split(",") if p]
    if not pols or any(p not in _sm.POLICIES for p in pols):
        raise HTTPException(422, f"policies must be among {list(_sm.POLICIES)}")
    if scenario and scenario not in rules.scenarios:
        raise HTTPException(422, f"unknown scenario; options: {sorted(rules.scenarios)}")
    lo, hi = _sm.valid_range(d, deadline_h, count, interval_h)
    if hi < lo or (count - 1) * interval_h + deadline_h + 3 >= len(d.ts):
        raise HTTPException(422, "That schedule is longer than the observed period. Use fewer transfers or a shorter interval.")
    if start_ts:
        try:
            idx = int(d.ts.get_indexer([pd.Timestamp(start_ts, tz="UTC")], method="nearest")[0])
        except (ValueError, TypeError):
            raise HTTPException(422, "start_ts must be an ISO date-time")
    else:
        idx = (lo + hi) // 2
    idx = min(max(idx, lo), hi)
    out = _sm.simulate_schedule(d, r["cfg"].raw, rules, amount=amount, deadline_h=deadline_h, count=count,
                                interval_h=interval_h, start_idx=idx, scenario=scenario, policies=pols)
    out["start_range"] = [d.ts[lo].isoformat(), d.ts[hi].isoformat()]
    return _sim_envelope(out, r)


@lru_cache(maxsize=32)
def _playground(cbdc: str, liquidity: float, forecast: str, noise: float, episodes: int, seed: int) -> list[dict]:
    from ..eval.harness import summarise
    from ..eval.paper1 import _env, evaluate
    rules = load_rules()
    elig = rules.eligible_rails(cbdc)
    rows = []
    for name in ("fixed_LR", "greedy", "forecast", "linucb", "oracle"):
        if name == "forecast":
            from ..eval import ablations as ab
            from ..eval.harness import run_policy
            import pandas as _pd
            df = _pd.concat([run_policy(_env(cbdc, elig, liquidity), ab.planner_for(forecast, noise), episodes, seed=seed + s).assign(seed=s) for s in range(2)])
            df["policy"] = f"forecast_{forecast}"
        else:
            df = evaluate(name, lambda: _env(cbdc, elig, liquidity), 2, episodes, seed)
        rows.append(summarise(df).iloc[0].to_dict() | {"small_bps": float(df[df["segment"] == "small"]["total_bps"].mean())})
    return rows


@app.get("/api/playground")
def playground(cbdc: str = "none", liquidity: float = Query(1.0, ge=0.1, le=4.0), forecast: str = "model",
               noise: float = Query(0.3, ge=0.0, le=2.0), episodes: int = Query(500, ge=100, le=1500), seed: int = 1):
    if cbdc not in ("none", "pilot", "mature") or forecast not in ("none", "model", "noisy", "perfect"):
        raise HTTPException(422, "cbdc must be none|pilot|mature and forecast none|model|noisy|perfect")
    rows = _playground(cbdc, round(liquidity, 2), forecast, round(noise, 2), episodes, seed)
    return {"disclaimer": DISCLAIMER, "source_kind": "synthetic", "cost_params": "provisional",
            "data": {"rows": rows, "rails": load_rules().eligible_rails(cbdc)}}
