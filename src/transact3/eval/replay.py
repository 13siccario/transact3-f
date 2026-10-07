"""Paper 2 historical replay: full-information replay of observed costs, compliant paths only.

Every hour a transfer arrives (for each size and deadline). A policy picks a path and a send time
inside the deadline. Costs are the cost engine's values at the send hour, so nothing is simulated
except the policies' choices. Forecast-aware uses only z(t), the one-hour-ahead forecast vector.
"""
from __future__ import annotations

import heapq
import json
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

from ..config import Config
from ..costs.paths import PATHS, load_params, market_state, path_costs
from ..costs.regimes import label_regimes
from ..routing.compliance import Rules, guard, load_rules, require_reviewed
from .tables import write_table

PATH_IDS = list(PATHS)           # P0, P1, P2


@dataclass
class ReplayData:
    ts: pd.DatetimeIndex
    sizes: list[float]
    cost: dict[float, np.ndarray]        # amount -> [P, T] observed all-in bps (premium excluded)
    pred_next: dict[float, np.ndarray]   # amount -> [P, T] forecast of next hour's cost made at hour t
    premium_bps: np.ndarray              # premium in percent at each hour (reported, never counted)
    regime: np.ndarray
    context: np.ndarray                  # [T, 2] log gas, stress flag proxy (for LinUCB features)
    source_kind: str
    params: dict
    state: pd.DataFrame
    pred_state: pd.DataFrame


def predicted_state(state: pd.DataFrame, z: pd.DataFrame) -> pd.DataFrame:
    """State at t+1 as the z(t) forecast sees it; known-at-origin fields are carried from t."""
    s = state.merge(z, left_on="ts", right_on="origin_ts", how="inner").copy()
    s["base_fee_gwei"] = s["z_gas_gwei"].clip(lower=0.0)            # a fee cannot be negative
    s["peg_price_usd"] = 1.0 + s["z_peg_dev"]
    s["premium_pct"] = s["z_premium_pct"]
    s["depth_1pct_usd"] = 50 * 10_000 / s["z_slip_bps"].clip(lower=1e-9)
    s["fx_spread_bps"] = s["z_fx_spread"].clip(lower=0.0)
    return s[state.columns].reset_index(drop=True)


def build_replay_data(processed: dict[str, pd.DataFrame], params: dict, z: pd.DataFrame, source_kind: str) -> ReplayData:
    state = market_state(processed, params["pool_id"])
    z = z.sort_values("origin_ts")
    state = state[state["ts"].isin(z["origin_ts"])].reset_index(drop=True)
    pstate = predicted_state(state, z)
    cost, pred = {}, {}
    for a in params["transfer_sizes_usd"]:
        cost[a] = np.stack([path_costs(p, a, state, params)["total_bps"].to_numpy() for p in PATH_IDS])
        pred[a] = np.stack([path_costs(p, a, pstate, params)["total_bps"].to_numpy() for p in PATH_IDS])
    ts = pd.DatetimeIndex(state["ts"])
    regime = label_regimes(pd.Series(ts), source_kind).to_numpy()
    ctx = np.column_stack([np.log(state["base_fee_gwei"] / 12), (regime == "stress").astype(float)])
    return ReplayData(ts, list(params["transfer_sizes_usd"]), cost, pred, state["premium_pct"].to_numpy(), regime,
                      ctx, source_kind, params, state, pstate)


# ---- single-episode decision logic ----------------------------------------------------------------
@dataclass
class Setup:
    elig: list[int]                  # indices into PATH_IDS allowed by the compliance filter
    extra: np.ndarray                # extra compliance cost (bps) per path under the legal scenario
    lat: np.ndarray                  # nominal latency (h) per path
    late_pen: float
    margin: float


def _pen(su: Setup, k: int, D: int) -> np.ndarray:
    return np.where(k + su.lat > D, su.late_pen, 0.0)


def _max_wait(su: Setup, D: int) -> int:
    return max(0, int(np.floor(D - min(su.lat[i] for i in su.elig))))


def _score(data, su, A, t, k, D, forecast=False):
    c = (data.pred_next[A][:, t] if forecast else data.cost[A][:, t]) + su.extra + _pen(su, k, D)
    return c


def decide(policy: str, data: ReplayData, su: Setup, A: float, a: int, D: int, trace: list | None = None):
    """Return (send_tick, path_index). `trace` collects the reasoning of forecast-aware for display."""
    e = su.elig
    mw = _max_wait(su, D)
    if policy.startswith("fixed_"):
        p = PATH_IDS.index(policy.split("_")[1])
        if p not in e:
            return None
        return 0, p
    if policy == "greedy":
        s = _score(data, su, A, a, 0, D)
        return 0, min(e, key=lambda i: s[i])
    if policy == "oracle":
        best = (np.inf, 0, e[0])
        for k in range(mw + 1):
            s = _score(data, su, A, a + k, k, D)
            for i in e:
                if s[i] < best[0] - 1e-12:
                    best = (s[i], k, i)
        return best[1], best[2]
    if policy == "forecast_aware":
        k = 0
        while True:
            now = _score(data, su, A, a + k, k, D)
            i_now = min(e, key=lambda i: now[i])
            if k + 1 <= mw:
                nxt = _score(data, su, A, a + k, k + 1, D, forecast=True)    # forecast made at hour a+k
                i_nxt = min(e, key=lambda i: nxt[i])
                wait = nxt[i_nxt] < now[i_now] - su.margin
                if trace is not None:
                    trace.append({"tick": k, "now_bps": float(now[i_now]), "forecast_next_bps": float(nxt[i_nxt]),
                                  "action": "wait" if wait else "send", "path": PATH_IDS[i_now]})
                if wait:
                    k += 1
                    continue
            elif trace is not None:
                trace.append({"tick": k, "now_bps": float(now[i_now]), "forecast_next_bps": None, "action": "send", "path": PATH_IDS[i_now]})
            return k, i_now
    raise ValueError(policy)


class LinUCBPaths:
    """Contextual bandit over eligible paths, delayed feedback through nominal settlement latency."""

    def __init__(self, n_arms: int, d: int, alpha: float = 0.4):
        self.alpha = alpha
        self.A = [np.eye(d) for _ in range(n_arms)]
        self.b = [np.zeros(d) for _ in range(n_arms)]
        self.pending: list = []

    def features(self, data, A, a, D):
        hr = (data.ts[a].hour / 24) * 2 * np.pi
        c = np.log(np.maximum(data.cost[A][:, a], 1e-6) / 200)
        return np.concatenate([[1.0, np.log10(A) / 4, D / 72, np.sin(hr), np.cos(hr)], c, data.context[a]])

    def choose(self, x, elig):
        best, arm = -np.inf, elig[0]
        for i in elig:
            inv = np.linalg.inv(self.A[i])
            u = (inv @ self.b[i]) @ x + self.alpha * np.sqrt(x @ inv @ x)
            if u > best:
                best, arm = u, i
        return arm

    def flush(self, now: float):
        while self.pending and self.pending[0][0] <= now:
            _, _, i, x, r = heapq.heappop(self.pending)
            self.A[i] += np.outer(x, x)
            self.b[i] += r * x

    def push(self, ready: float, tie: int, i: int, x: np.ndarray, reward: float):
        heapq.heappush(self.pending, (ready, tie, i, x, reward))


def _setup(rules: Rules, scenario: str, cfg: dict) -> Setup:
    elig = [PATH_IDS.index(p) for p in rules.eligible_paths(scenario)]
    extra = np.array([rules.extra_cost_bps(scenario, p) for p in PATH_IDS])
    lat = np.array([cfg["latency_h"][p] for p in PATH_IDS], dtype=float)
    return Setup(elig, extra, lat, cfg["late_penalty_bps"], cfg["margin_bps"])


def run_replay(data: ReplayData, cfg: dict, rules: Rules, scenario: str, policies: list[str] | None = None,
               arrivals: np.ndarray | None = None) -> pd.DataFrame:
    su = _setup(rules, scenario, cfg)
    elig_names = [PATH_IDS[i] for i in su.elig]
    rows = []
    T = len(data.ts)
    for A in data.sizes:
        for D in cfg["deadlines_h"]:
            idx = np.arange(T - D - 2) if arrivals is None else arrivals[arrivals < T - D - 2]
            for pol in (policies or cfg["policies"]):
                if pol.startswith("fixed_") and pol.split("_")[1] not in elig_names:
                    continue
                lin = LinUCBPaths(len(PATH_IDS), 5 + len(PATH_IDS) + data.context.shape[1]) if pol == "linucb" else None
                for n, a in enumerate(idx):
                    if lin:
                        lin.flush(a)
                        x = lin.features(data, A, a, D)
                        i = lin.choose(x, su.elig)
                        k, p = 0, i
                    else:
                        k, p = decide(pol, data, su, A, a, D)
                    guard(PATH_IDS[p], elig_names)                                   # hard constraint
                    cost = float(data.cost[A][p, a + k] + su.extra[p])
                    pen = float(_pen(su, k, D)[p])
                    if lin:
                        lin.push(a + su.lat[p], n, p, x, -(cost + pen) / 100)
                    rows.append({"policy": pol, "scenario": scenario, "amount": A, "deadline_h": D, "arrival": data.ts[a],
                                 "wait_h": k, "path": PATH_IDS[p], "cost_bps": cost, "penalty_bps": pen,
                                 "total_bps": cost + pen, "regime": data.regime[a], "t_idx": int(a)})
    df = pd.DataFrame(rows)
    key = ["scenario", "amount", "deadline_h", "t_idx"]
    orc = df[df["policy"] == "oracle"].set_index(key)["total_bps"].rename("oracle_bps")
    df = df.join(orc, on=key)
    df["regret_bps"] = df["total_bps"] - df["oracle_bps"]
    return df


def block_bootstrap(d: np.ndarray, block: int, n: int, rng: np.random.Generator) -> tuple[float, float, float, float]:
    """Mean, 95% CI and two-sided p of a serially correlated difference series (moving-block bootstrap)."""
    d = np.asarray(d, dtype=float)
    L = len(d)
    if L < 2 * block:
        block = max(1, L // 4)
    nb = int(np.ceil(L / block))
    means = np.empty(n)
    for b in range(n):
        starts = rng.integers(0, L - block + 1, nb)
        means[b] = np.concatenate([d[s:s + block] for s in starts])[:L].mean()
    lo, hi = np.percentile(means, [2.5, 97.5])
    centred = means - means.mean()
    p = float((np.abs(centred) >= abs(d.mean())).mean())
    return float(d.mean()), float(lo), float(hi), p


def pair_table(df: pd.DataFrame, a: str, b: str, cfg: dict, rng) -> pd.DataFrame:
    rows = []
    for (scn, A, D), g in df.groupby(["scenario", "amount", "deadline_h"]):
        pa = g[g["policy"] == a].sort_values("t_idx").set_index("t_idx")["total_bps"]
        pb = g[g["policy"] == b].sort_values("t_idx").set_index("t_idx")["total_bps"]
        d = (pa - pb).dropna().to_numpy()
        if len(d) == 0:
            continue
        m, lo, hi, p = block_bootstrap(d, cfg["bootstrap"]["block_h"], cfg["bootstrap"]["n"], rng)
        rows.append({"comparison": f"{a} - {b}", "scenario": scn, "amount": A, "deadline_h": D, "diff_bps": m, "ci_lo": lo, "ci_hi": hi, "p": p})
    return pd.DataFrame(rows)


def build_empirical(data: ReplayData):
    """Empirical stablecoin cost process for Paper 1: P1 cost as a function of amount over the observed hours."""
    from ..sim.world import Empirical
    s, ps, p = data.state, data.pred_state, data.params
    ramp = p["paths"]["P1"]["ramp"]
    extra = p["paths"]["P1"]["fx_extra_bps"] + p["paths"]["P1"]["reg_bps"]
    gas_units = sum(p["gas_units"].values())

    def make(frame):
        gas_usd = gas_units * (frame["base_fee_gwei"] + frame["priority_fee_gwei"]).to_numpy() * 1e-9 * frame["eth_usd"].to_numpy()
        fee = frame["fee_bps"].to_numpy()
        peg = np.abs(frame["peg_price_usd"].to_numpy() - 1) * 1e4
        fx = frame["fx_spread_bps"].to_numpy()
        depth = frame["depth_1pct_usd"].to_numpy()
        return lambda A: (gas_usd + ramp["fixed_usd"]) / A * 1e4 + fee + ramp["bps"] + peg + fx + extra + 50 * A / depth
    return Empirical(bps=make(s), pred_bps=make(ps), length=len(s))


def _plot_regret(df: pd.DataFrame, out: Path, scenario: str) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    g = df[(df["scenario"] == scenario) & (df["amount"] == 1000) & (df["deadline_h"] == 24)]
    fig, ax = plt.subplots(figsize=(6.4, 4))
    colors = {"greedy": "#201F1F", "forecast_aware": "#3E9E66", "linucb": "#6F58C9", "fixed_P1": "#1E9BD7", "fixed_P0": "#9a9d9f"}
    for pol, c in colors.items():
        s = g[g["policy"] == pol].sort_values("arrival")
        if len(s):
            ax.plot(s["arrival"], s["regret_bps"].cumsum() / 1000, label=pol, color=c, linewidth=1.4)
    ax.set_ylabel("Cumulative regret vs oracle (k bps)")
    ax.legend(frameon=False, fontsize=8)
    ax.spines[["top", "right"]].set_visible(False)
    fig.autofmt_xdate()
    fig.tight_layout()
    out.mkdir(parents=True, exist_ok=True)
    fig.savefig(out / "fig_cum_regret.png", dpi=200)
    plt.close(fig)


def load_data(cfg: Config) -> ReplayData:
    d, f = Path(cfg["data_dir"]), Path(cfg["forecast_dir"])
    manifest = json.loads((d / "manifest.json").read_text())
    processed = {n: pd.read_parquet(d / f"{n}.parquet") for n in manifest["datasets"]}
    z = pd.read_parquet(f / "z.parquet")
    return build_replay_data(processed, load_params(cfg["costs_config"]), z, manifest["mode"])


def run_paper2(cfg: Config, data: ReplayData | None = None) -> dict:
    rules = load_rules()
    require_reviewed(rules, "synthetic" if (data and data.source_kind == "synthetic") else "real")
    data = data or load_data(cfg)
    out = Path(cfg["out_dir"])
    rng = np.random.default_rng(cfg.seed)
    all_runs = pd.concat([run_replay(data, cfg.raw, rules, s) for s in cfg["scenarios"]], ignore_index=True)
    default = rules.default_scenario
    base = all_runs[all_runs["scenario"] == default]

    g = base.groupby(["amount", "policy"]).agg(total_bps=("total_bps", "mean"), regret_bps=("regret_bps", "mean"),
                                               wait_h=("wait_h", "mean"), late_pct=("penalty_bps", lambda x: 100 * (x > 0).mean())).reset_index()
    write_table(g, out, "table6_replay", f"Table 6. Replay of observed costs, compliant paths only (scenario {default}; mean over deadlines)")
    reg = base.groupby(["regime", "policy"]).agg(total_bps=("total_bps", "mean"), regret_bps=("regret_bps", "mean")).reset_index()
    write_table(reg, out, "table6b_regimes", "Table 6b. Replay cost by regime")
    pairs = pd.concat([pair_table(all_runs, "forecast_aware", "greedy", cfg.raw, rng),
                       pair_table(all_runs, "linucb", "greedy", cfg.raw, rng)], ignore_index=True)
    write_table(pairs, out, "table6c_paired", "Table 6c. Paired differences (negative = first policy cheaper), moving-block bootstrap, 1-week blocks")
    t7 = all_runs.groupby(["scenario", "policy"]).agg(total_bps=("total_bps", "mean"), regret_bps=("regret_bps", "mean"),
                                                      share_P2=("path", lambda x: (x == "P2").mean())).reset_index()
    write_table(t7, out, "table7_legal_status", "Table 7. Legal-status sensitivity: P2 excluded, included with extra cost, included without")
    _plot_regret(base, out / "figures", default)
    all_runs.to_parquet(out / "replay_runs.parquet", index=False)

    meta = {"config_hash": cfg.hash, "rules_version": rules.version, "rules_reviewed": bool(rules.reviewed_by),
            "default_scenario": default, "source_kind": data.source_kind, "episodes": int(len(all_runs))}
    (out / "results.json").write_text(json.dumps(meta, indent=2))
    return meta
