import pytest
from fastapi.testclient import TestClient

from transact3.api import main
from transact3.config import load_config
from transact3.data import pipeline


@pytest.fixture(scope="module")
def client(tmp_path_factory):
    tmp = tmp_path_factory.mktemp("d")
    cfg = tmp / "c.yaml"
    cfg.write_text(f"""
name: t
seed: 5
mode: synthetic
period: {{start: '2026-06-01', end: '2026-06-30'}}
outputs: {{raw_dir: {tmp}/raw, processed_dir: {tmp}/proc}}
cleaning: {{max_ffill_hours: 6, outlier_window_hours: 72, outlier_mad_k: 8.0}}
fx_pairs: [USDINR]
""")
    pipeline.build(load_config(cfg))
    main.PROCESSED = tmp / "proc"
    main._state.cache_clear()
    return TestClient(main.app)


def test_envelope_flags_synthetic_and_disclaimer(client):
    j = client.get("/api/meta").json()
    assert j["source_kind"] == "synthetic" and "not legal or financial advice" in j["disclaimer"]
    assert set(j["data"]["paths"]) == {"P0", "P1", "P2"}


def test_anatomy_covers_every_path_and_size(client):
    rows = client.get("/api/costs/anatomy").json()["data"]
    assert len(rows) == 9 and all("c_gas" in r for r in rows)


def test_stress_costs_more_than_normal_for_stablecoin_path(client):
    def total(regime):
        rows = client.get(f"/api/costs/anatomy?regime={regime}").json()["data"]
        return next(r["total_bps"] for r in rows if r["path"] == "P1" and r["amount"] == 1000)
    assert total("stress") > total("normal")


def test_timeline_and_errors(client):
    j = client.get("/api/costs/timeline?path=P1&amount=1000").json()["data"]
    assert len(j["series"]) == 29 and j["events"]
    assert client.get("/api/costs/timeline?path=PX").status_code == 404
    assert client.get("/api/costs/anatomy?regime=nope").status_code == 404


def test_forecast_endpoints(client, tmp_path_factory):
    import numpy as np
    import pandas as pd
    from transact3.config import load_config as lc
    from transact3.forecast import validation as v
    tmp = tmp_path_factory.mktemp("f")
    proc = main.PROCESSED
    manifest = __import__("json").loads((proc / "manifest.json").read_text())
    processed = {n: pd.read_parquet(proc / f"{n}.parquet") for n in manifest["datasets"]}
    cfgp = tmp / "f.yaml"
    cfgp.write_text(open("configs/forecast.yaml").read().replace("data/processed/forecast", str(tmp / "out"))
                    .replace("models: [random_walk, rolling_median, ar, garch, lightgbm, lstm]", "models: [random_walk, ar, lightgbm]")
                    .replace("initial_train_frac: 0.5", "initial_train_frac: 0.6"))
    cfg = lc(cfgp)
    preds = v.run_forecasts(cfg, processed, "synthetic")
    v.save(cfg, preds, v.score(preds, "random_walk", 1), "synthetic", manifest["config_hash"])
    main.FORECAST_DIR = tmp / "out"
    main._forecast.cache_clear()
    s = client.get("/api/forecast/summary").json()
    assert s["source_kind"] == "synthetic" and "not legal or financial advice" in s["disclaimer"]
    assert any(r["model"] == "lightgbm" and r["target"] == "fx_vol" for r in s["data"]["rows"])
    ser = client.get("/api/forecast/series?target=fx_vol&model=ar").json()["data"]
    assert ser["points"] and "model_pred" in ser["points"][0]
    z = client.get("/api/forecast/z").json()["data"]
    assert len(z["items"]) == 7
    assert client.get("/api/forecast/series?target=nope").status_code == 404
    assert client.get("/api/forecast/summary?regime=nope").status_code == 404


def test_results_simulate_and_playground_endpoints(client):
    import transact3.api.main as m
    assert client.get("/api/results/paper1/..%2Fx").status_code == 404
    assert client.get("/api/results/paper9/table5_main").status_code == 404
    assert client.get("/api/results").status_code == 200
    r = client.get("/api/playground?episodes=100&liquidity=1&forecast=model")
    assert r.status_code == 200 and {x["policy"] for x in r.json()["data"]["rows"]} >= {"greedy", "oracle", "linucb"}
    assert client.get("/api/playground?cbdc=bogus").status_code == 422
