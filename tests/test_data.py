import numpy as np
import pandas as pd
import pytest

from transact3.config import load_config
from transact3.data import pipeline
from transact3.data.base import RealSourceUnavailable
from transact3.data.calendar import load_events, validate_events
from transact3.data.cleaning import align_hourly, fill_short_gaps, flag_outliers
from transact3.data.collectors.fx import RealFX, SyntheticFX


def test_config_hash_and_validation(tmp_path):
    p = tmp_path / "c.yaml"
    p.write_text("name: x\nseed: 1\nmode: synthetic\nperiod: {start: '2026-01-01', end: '2026-01-02'}\n")
    cfg = load_config(p)
    assert cfg.seed == 1 and len(cfg.hash) == 12
    p.write_text("name: x\nseed: 1\nmode: bogus\nperiod: {}\n")
    with pytest.raises(ValueError):
        load_config(p)


def test_synthetic_is_deterministic_and_flagged():
    a = SyntheticFX(["USDINR"]).collect("2026-01-01", "2026-01-05", np.random.default_rng(7))
    b = SyntheticFX(["USDINR"]).collect("2026-01-01", "2026-01-05", np.random.default_rng(7))
    pd.testing.assert_frame_equal(a, b)
    assert (a["source_kind"] == "synthetic").all()


def test_real_collector_refuses_until_wired():
    with pytest.raises(RealSourceUnavailable):
        RealFX().collect("2026-01-01", "2026-01-02", np.random.default_rng(0))


def test_align_fills_grid_and_marks_missing():
    ts = pd.to_datetime(["2026-01-01 00:00", "2026-01-01 03:00"], utc=True)
    df = pd.DataFrame({"ts": ts, "mid": [1.0, 2.0], "source_kind": "synthetic"})
    out = align_hourly(df.assign(pair="X"), ["pair"], "2026-01-01", "2026-01-01 05:00")
    assert len(out) == 5
    assert out["was_missing"].tolist() == [False, True, True, False, True]


def test_fill_short_gaps_is_forward_only_and_capped():
    s = pd.Series([1.0] + [np.nan] * 4)
    out = fill_short_gaps(s, 2)
    assert out.tolist()[:3] == [1.0, 1.0, 1.0] and out.isna().sum() == 2


def test_outlier_flag_has_no_lookahead():
    rng = np.random.default_rng(0)
    s = pd.Series(rng.normal(0, 1, 300))
    s2 = s.copy()
    s2.iloc[250] = 100.0                       # future shock
    f1, f2 = flag_outliers(s, 72, 8), flag_outliers(s2, 72, 8)
    assert (f1.iloc[:250] == f2.iloc[:250]).all()   # earlier flags unaffected by later data
    assert f2.iloc[250]


def test_event_calendar_rules():
    assert validate_events() == []
    assert load_events(verified_only=True).empty     # nothing verified yet


def test_pipeline_end_to_end(tmp_path):
    cfg_text = f"""
name: t
seed: 3
mode: synthetic
period: {{start: '2026-06-01', end: '2026-06-08'}}
outputs: {{raw_dir: {tmp_path}/raw, processed_dir: {tmp_path}/proc}}
cleaning: {{max_ffill_hours: 6, outlier_window_hours: 72, outlier_mad_k: 8.0}}
fx_pairs: [USDINR, EURUSD]
"""
    p = tmp_path / "c.yaml"
    p.write_text(cfg_text)
    m = pipeline.build(load_config(p))
    assert {"fx", "usdt_inr", "pools", "gas", "peg", "premium"} <= set(m["datasets"])
    prem = pd.read_parquet(tmp_path / "proc" / "premium.parquet")
    assert prem["premium_pct"].notna().all()
    assert (tmp_path / "proc" / "transact3.duckdb").exists()
