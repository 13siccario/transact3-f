"""Payment paths P0 (conventional), P1 (compliant stablecoin), P2 (onshore exchange)."""
from __future__ import annotations

from pathlib import Path

import pandas as pd
import yaml

from . import decomposition as d

TERMS = ["c_gas", "c_lp", "c_slip", "c_peg", "c_prem", "c_ramp", "c_reg", "c_fx"]
PATHS = {"P0": "Conventional", "P1": "Compliant stablecoin", "P2": "Onshore exchange"}
COSTS_FILE = Path("configs/costs.yaml")


def load_params(path: str | Path = COSTS_FILE) -> dict:
    return yaml.safe_load(Path(path).read_text())


def path_costs(path: str, amount: float, s: pd.DataFrame, params: dict) -> pd.DataFrame:
    """Cost terms for one path and size over a market-state frame `s`.

    `s` columns: ts, base_fee_gwei, priority_fee_gwei, eth_usd, fee_bps, depth_1pct_usd,
    peg_price_usd, premium_pct, fx_spread_bps.
    """
    p = params["paths"][path]
    zero = pd.Series(0.0, index=s.index)
    out = pd.DataFrame({"ts": s["ts"], "path": path, "amount": float(amount)})
    on_chain = path == "P1"
    gas_units = sum(params["gas_units"].values())
    out["c_gas"] = d.c_gas(s["base_fee_gwei"], s["priority_fee_gwei"], s["eth_usd"], gas_units) if on_chain else zero
    out["c_lp"] = d.c_lp(amount, s["fee_bps"]) if on_chain else zero
    out["c_slip"] = d.c_slip(amount, s["depth_1pct_usd"]) if on_chain else zero
    out["c_peg"] = d.c_peg(amount, s["peg_price_usd"]) if on_chain else zero
    out["c_prem"] = d.c_prem(amount, s["premium_pct"]) if path in ("P1", "P2") else zero
    out["c_ramp"] = d.c_ramp(amount, p["ramp"]["fixed_usd"], p["ramp"]["bps"])
    out["c_reg"] = d.c_reg(amount, p["reg_bps"])
    out["c_fx"] = d.c_fx(amount, s["fx_spread_bps"], p["fx_extra_bps"])
    out["total_ex_prem"] = out[TERMS].sum(axis=1) - out["c_prem"]
    out["total"] = out[TERMS].sum(axis=1)
    out["total_bps"] = out["total_ex_prem"] / amount * 1e4
    return out


def market_state(processed: dict[str, pd.DataFrame], pool_id: str, peg_coin: str = "USDT") -> pd.DataFrame:
    """Join processed datasets into one row per hour (the information set at that hour)."""
    fx = processed["fx"]
    fx = fx[fx["pair"] == "USDINR"][["ts", "spread_bps"]].rename(columns={"spread_bps": "fx_spread_bps"})
    pools = processed["pools"]
    pools = pools[pools["pool_id"] == pool_id][["ts", "fee_bps", "depth_1pct_usd"]]
    peg = processed["peg"]
    peg = peg[peg["coin"] == peg_coin][["ts", "price_usd"]].rename(columns={"price_usd": "peg_price_usd"})
    s = processed["gas"][["ts", "base_fee_gwei", "priority_fee_gwei", "eth_usd"]]
    for other in (fx, pools, peg, processed["premium"][["ts", "premium_pct"]]):
        s = s.merge(other, on="ts", how="left")
    return s.dropna().reset_index(drop=True)


def cost_table(processed: dict[str, pd.DataFrame], params: dict) -> pd.DataFrame:
    s = market_state(processed, params["pool_id"])
    frames = [path_costs(p, a, s, params) for p in PATHS for a in params["transfer_sizes_usd"]]
    return pd.concat(frames, ignore_index=True)
