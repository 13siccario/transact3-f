import numpy as np
import pytest

from transact3.eval import simulate as sm
from tests.test_replay import setup  # noqa: F401  (fixture reuse)


def test_schedule_trace_is_complete_and_consistent(setup):
    data, cfg, rules = setup
    r = sm.simulate_schedule(data, cfg, rules, amount=1000, deadline_h=24, count=4, interval_h=24, start_idx=500, scenario="p2_excluded")
    assert r["eligible_paths"] == ["P0", "P1"]
    for name, pol in r["policies"].items():
        assert len(pol["transfers"]) == 4
        for t in pol["transfers"]:
            assert t["arrive_i"] <= t["send_i"] <= t["arrive_i"] + 24 and t["path"] in ("P0", "P1")
            assert t["regret_bps"] >= -1e-9                       # nothing beats hindsight
        kinds = {e["type"] for e in pol["events"]}
        assert {"arrive", "send", "settle"} <= kinds
        assert pol["summary"]["total_usd"] == pytest.approx(sum(t["total_usd"] for t in pol["transfers"]))
    assert r["policies"]["greedy"]["summary"]["mean_wait_h"] == 0
    assert r["market"][0]["i"] == 0 and len(r["market"][0]["cost_bps"]) == 3


def test_oracle_has_zero_regret_and_greedy_saving_vs_quote_is_zero(setup):
    data, cfg, rules = setup
    r = sm.simulate_schedule(data, cfg, rules, amount=2500, deadline_h=48, count=3, interval_h=12, start_idx=300)
    assert all(abs(t["regret_bps"]) < 1e-9 for t in r["policies"]["oracle"]["transfers"])
    assert all(abs(t["saving_vs_quote_bps"]) < 1e-9 for t in r["policies"]["greedy"]["transfers"])


def test_start_outside_observed_period_is_rejected(setup):
    data, cfg, rules = setup
    with pytest.raises(ValueError):
        sm.simulate_schedule(data, cfg, rules, amount=1000, deadline_h=24, count=5, interval_h=24, start_idx=len(data.ts) - 5)


def test_custom_amount_matches_cost_engine(setup):
    data, cfg, rules = setup
    d2 = sm._with_amount(data, 777.0)
    assert d2.cost[777.0].shape == (3, len(data.ts)) and 777.0 not in data.cost    # original untouched
