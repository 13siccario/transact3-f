import copy
import json

import numpy as np
import pandas as pd
import pytest

from transact3.config import load_config
from transact3.data import pipeline
from transact3.eval import replay as rp
from transact3.forecast import validation as v
from transact3.routing.compliance import load_rules


@pytest.fixture(scope="module")
def setup(tmp_path_factory):
    tmp = tmp_path_factory.mktemp("rp")
    (tmp / "d.yaml").write_text(f"""
name: t
seed: 5
mode: synthetic
period: {{start: '2026-05-01', end: '2026-07-15'}}
outputs: {{raw_dir: {tmp}/raw, processed_dir: {tmp}/proc}}
cleaning: {{max_ffill_hours: 6, outlier_window_hours: 72, outlier_mad_k: 8.0}}
fx_pairs: [USDINR]
""")
    pipeline.build(load_config(tmp / "d.yaml"))
    processed = {n: pd.read_parquet(tmp / "proc" / f"{n}.parquet") for n in json.loads((tmp / "proc" / "manifest.json").read_text())["datasets"]}
    fc = open("configs/forecast.yaml").read().replace("data/processed/forecast", str(tmp / "fc"))
    fc = fc.replace("models: [random_walk, rolling_median, ar, garch, lightgbm, lstm]", "models: [random_walk, lightgbm]").replace("initial_train_frac: 0.5", "initial_train_frac: 0.5")
    (tmp / "f.yaml").write_text(fc)
    fcfg = load_config(tmp / "f.yaml")
    preds = v.run_forecasts(fcfg, processed, "synthetic")
    v.save(fcfg, preds, v.score(preds, "random_walk", 1), "synthetic", "x")
    z = pd.read_parquet(tmp / "fc" / "z.parquet")
    from transact3.costs.paths import load_params
    data = rp.build_replay_data(processed, load_params(), z, "synthetic")
    cfg = load_config("configs/replay.yaml").raw
    cfg["deadlines_h"] = [24]
    return data, cfg, load_rules()


def test_oracle_is_never_beaten(setup):
    data, cfg, rules = setup
    df = rp.run_replay(data, cfg, rules, "p2_included_with_cost", arrivals=np.arange(0, 400))
    assert (df["regret_bps"] >= -1e-9).all()
    assert df[df["policy"] == "oracle"]["regret_bps"].abs().max() < 1e-9


def test_no_policy_uses_an_ineligible_path(setup):
    data, cfg, rules = setup
    df = rp.run_replay(data, cfg, rules, "p2_excluded", arrivals=np.arange(0, 300))
    assert "P2" not in set(df["path"]) and "fixed_P2" not in set(df["policy"])


def test_extra_compliance_cost_is_applied(setup):
    data, cfg, rules = setup
    a = rp.run_replay(data, cfg, rules, "p2_included", ["fixed_P2"], arrivals=np.arange(0, 50))
    b = rp.run_replay(data, cfg, rules, "p2_included_with_cost", ["fixed_P2"], arrivals=np.arange(0, 50))
    assert (b["cost_bps"].to_numpy() - a["cost_bps"].to_numpy()) == pytest.approx(25.0)


def test_forecast_aware_cannot_see_the_future(setup):
    data, cfg, rules = setup
    su = rp._setup(rules, "p2_included", cfg)
    A, D = 1000, 24
    for a in range(100, 160):
        trace: list = []
        k, p = rp.decide("forecast_aware", data, su, A, a, D, trace)
        d2 = copy.copy(data)
        d2.cost = {A: data.cost[A].copy()}
        d2.pred_next = {A: data.pred_next[A].copy()}
        d2.cost[A][:, a + k + 1:] += 10_000          # corrupt everything after the send hour
        d2.pred_next[A][:, a + k + 1:] += 10_000
        assert rp.decide("forecast_aware", d2, su, A, a, D) == (k, p)


def test_block_bootstrap_detects_a_real_difference_and_not_noise(setup):
    rng = np.random.default_rng(0)
    noise = rng.normal(0, 1, 2000)
    m, lo, hi, p = rp.block_bootstrap(noise, 48, 500, rng)
    assert lo < 0 < hi and p > 0.05
    m, lo, hi, p = rp.block_bootstrap(noise - 1.0, 48, 500, rng)
    assert hi < 0 and p < 0.05


def test_empirical_stablecoin_process_matches_the_cost_engine(setup):
    data, cfg, rules = setup
    emp = rp.build_empirical(data)
    for A in data.sizes:
        assert np.allclose(emp.bps(A), data.cost[A][1], rtol=1e-9, atol=1e-6)
        assert np.allclose(emp.pred_bps(A), data.pred_next[A][1], rtol=1e-9, atol=1e-6)


def test_forecast_costs_are_never_negative(setup):
    data, cfg, rules = setup
    for A in data.sizes:
        assert (data.pred_next[A] > 0).all()
