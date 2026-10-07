"""Paper 1 experiments: main comparison, forecast ablations, noise sweep, liquidity study, sensitivity."""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

from ..config import Config
from ..routing.compliance import load_rules, require_reviewed
from ..routing.linucb import LinUCB
from ..routing.ppo import PPOPolicy, train_ppo
from ..routing.rules import Fixed, Planner
from ..sim.env import RoutingEnv
from ..sim.rails import rails_for
from . import ablations as ab
from .harness import run_policy
from .sensitivity import run_sensitivity
from .stats import mean_ci, paired_diff
from .tables import write_table


def _env(cbdc: str, eligible, scale: float = 1.0, empirical=None, seed: int = 0) -> RoutingEnv:
    return RoutingEnv(rails_for(cbdc, scale), eligible, forecast_kind="model", empirical=empirical, seed=seed)


def make_policy(name: str, ppo_model=None, sigma: float = 0.3):
    if name.startswith("fixed_"):
        return Fixed(name.split("_")[1])
    return {"greedy": lambda: Planner("none"), "forecast_model": lambda: Planner("model", name="forecast_model"),
            "forecast_noisy": lambda: ab.planner_for("noisy", sigma), "oracle": lambda: Planner("perfect", margin=0.0),
            "linucb": lambda: LinUCB(), "ppo": lambda: PPOPolicy(ppo_model)}[name]()


def evaluate(name: str, make_env, seeds: int, episodes: int, base_seed: int, ppo_model=None, sigma=0.3) -> pd.DataFrame:
    frames = []
    for s in range(seeds):
        df = run_policy(make_env(), make_policy(name, ppo_model, sigma), episodes, seed=base_seed + s)
        frames.append(df.assign(seed=s))
    return pd.concat(frames, ignore_index=True)


def main_table(runs: dict[str, pd.DataFrame], ref: str = "greedy") -> pd.DataFrame:
    rows = []
    for name, df in runs.items():
        m, lo, hi = mean_ci(df)
        d = paired_diff(df, runs[ref]) if name != ref else {"diff": 0.0, "lo": np.nan, "hi": np.nan, "p": np.nan}
        rows.append({"policy": name, "total_bps": m, "ci_lo": lo, "ci_hi": hi, f"vs_{ref}": d["diff"],
                     "diff_lo": d["lo"], "diff_hi": d["hi"], "p": d["p"], "wait_h": df["wait_h"].mean(),
                     "late_pct": 100 * df["late"].mean(), "fail_pct": 100 * df["failed"].mean()})
    return pd.DataFrame(rows).sort_values("total_bps").reset_index(drop=True)


def segment_table(runs: dict[str, pd.DataFrame]) -> pd.DataFrame:
    df = pd.concat(runs.values())
    g = df.groupby(["policy", "segment"]).agg(n=("total_bps", "size"), total_bps=("total_bps", "mean"),
                                              late_pct=("late", lambda x: 100 * x.mean()),
                                              fail_pct=("failed", lambda x: 100 * x.mean())).reset_index()
    order = {"small": 0, "medium": 1, "large": 2}
    return g.sort_values(["segment", "total_bps"], key=lambda c: c.map(order) if c.name == "segment" else c).reset_index(drop=True)


def figure_noise(sweep: pd.DataFrame, refs: dict[str, float], out: Path) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    out.mkdir(parents=True, exist_ok=True)
    fig, ax = plt.subplots(figsize=(6.4, 4))
    ax.plot(sweep["sigma"], sweep["total_bps"], marker="o", color="#3E9E66", label="Forecast-aware (noisy foresight)")
    ax.fill_between(sweep["sigma"], sweep["ci_lo"], sweep["ci_hi"], color="#3E9E66", alpha=0.18)
    for label, v, style in (("Greedy (no forecast)", refs["greedy"], "--"), ("Model forecast", refs["model"], ":"),
                            ("Oracle (perfect foresight)", refs["oracle"], "-.")):
        ax.axhline(v, color="#201F1F", linestyle=style, linewidth=1, label=label)
    ax.set_xlabel("Forecast noise (log-cost sigma)")
    ax.set_ylabel("All-in cost (bps)")
    ax.legend(frameon=False, fontsize=8)
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    fig.savefig(out / "fig2_forecast_value.png", dpi=200)
    plt.close(fig)


def run_paper1(cfg: Config, empirical=None, tag: str = "") -> dict:
    rules = load_rules()
    require_reviewed(rules, cfg.get("mode", "synthetic"))
    out = Path(cfg["out_dir"])
    cbdc = cfg["cbdc"]
    elig = rules.eligible_rails(cbdc)
    seeds, eps, seed0 = cfg["n_seeds"], cfg["n_episodes"], cfg.seed
    mk = lambda scale=1.0: (lambda: _env(cbdc, elig, scale, empirical))
    meta = {"config_hash": cfg.hash, "rules_version": rules.version, "rules_reviewed": bool(rules.reviewed_by),
            "eligible_rails": elig, "empirical_sc": empirical is not None}

    # PPO is trained once on a separate world, then frozen for evaluation.
    ppo_model = None
    if "ppo" in cfg["policies"]:
        ppo_model = train_ppo(_env(cbdc, elig, 1.0, empirical, seed=seed0 + 9_000), cfg["ppo"]["timesteps"], seed0)

    # Table 5: main comparison, Table 5b: by transfer-size segment
    runs = {p: evaluate(p, mk(), seeds, eps, seed0, ppo_model) for p in cfg["policies"]}
    t5 = main_table(runs)
    write_table(t5, out, f"table5_main{tag}", "Table 5. All-in cost by routing policy (bps, mean over worlds, 95% CI; paired difference vs greedy)")
    write_table(segment_table(runs), out, f"table5b_segments{tag}", "Table 5b. Cost and failure rates by transfer-size segment")

    # Table 6: forecast ablation, and the noise sweep (E4)
    kinds = {k: (runs["greedy"] if k == "none" else runs["oracle"] if k == "perfect" else runs["forecast_model"]
                 if k == "model" else evaluate("forecast_noisy", mk(), seeds, eps, seed0, sigma=cfg["noisy_sigma"]))
             for k in cfg["ablation_kinds"]}
    write_table(ab.ablation_table(kinds), out, f"table6_ablation{tag}",
                f"Table 6. Forecast ablation (oracle = perfect foresight of the market path, planned one transfer at a time) (noisy foresight sigma={cfg['noisy_sigma']})")
    sweep = []
    for sg in cfg["noise_sweep"]:
        df = evaluate("forecast_noisy", mk(), seeds, eps, seed0, sigma=sg)
        m, lo, hi = mean_ci(df)
        d = paired_diff(df, runs["greedy"])
        sweep.append({"sigma": sg, "total_bps": m, "ci_lo": lo, "ci_hi": hi, "vs_greedy": d["diff"],
                      "vs_greedy_lo": d["lo"], "vs_greedy_hi": d["hi"], "wait_h": df["wait_h"].mean()})
    sweep = pd.DataFrame(sweep)
    write_table(sweep, out, f"table_e4_noise{tag}", "E4. How accurate must a forecast be? Cost by forecast noise level")
    refs = {"greedy": mean_ci(runs["greedy"])[0], "model": mean_ci(runs["forecast_model"])[0], "oracle": mean_ci(runs["oracle"])[0]}
    figure_noise(sweep, refs, out / "figures") if not tag else None
    meta["break_even_noise"] = ab.break_even_noise(sweep, runs["greedy"])

    if tag:        # robustness reruns stop here
        (out / f"results{tag}.json").write_text(json.dumps(meta, indent=2, default=str))
        return meta

    # E3: PPO vs LinUCB as liquidity tightens
    e3 = []
    for scale in cfg["liquidity_scales"]:
        env_f = mk(scale)
        model = train_ppo(_env(cbdc, elig, scale, None, seed=seed0 + 9_000), cfg["ppo"]["timesteps"], seed0) if ppo_model else None
        r = {p: evaluate(p, env_f, seeds, eps, seed0, model) for p in ("greedy", "linucb", "ppo", "oracle") if p != "ppo" or model}
        for p, df in r.items():
            m, lo, hi = mean_ci(df)
            e3.append({"liquidity_scale": scale, "policy": p, "total_bps": m, "ci_lo": lo, "ci_hi": hi})
        if "ppo" in r:
            d = paired_diff(r["ppo"], r["linucb"])
            e3.append({"liquidity_scale": scale, "policy": "ppo - linucb", "total_bps": d["diff"], "ci_lo": d["lo"], "ci_hi": d["hi"]})
    write_table(pd.DataFrame(e3), out, "table_e3_liquidity", "E3. PPO versus LinUCB as liquidity buffers tighten (scale 1 = baseline)")

    # E5: sensitivity
    draws, cb = run_sensitivity(cfg.raw, rules, seed0)
    write_table(draws, out, "table_e5_draws", "E5. Policy ranking across parameter draws (Kendall tau against the baseline ranking)")
    write_table(cb, out, "table_e5_cbdc", "E5. Policy cost under CBDC scenarios")
    meta["sensitivity"] = {"min_tau": float(draws["kendall_tau"].min()), "mean_tau": float(draws["kendall_tau"].mean()),
                           "model_beats_greedy_share": float(draws["model_beats_greedy"].mean())}
    (out / "results.json").write_text(json.dumps(meta, indent=2, default=str))
    return meta
