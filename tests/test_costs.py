import pandas as pd
import pytest

from transact3.costs import decomposition as d
from transact3.costs.paths import TERMS, path_costs, load_params


def test_gas_usd():
    # 215k gas * (10+2) gwei = 0.00258 ETH; at $3000 = $7.74
    assert d.c_gas(10, 2, 3000, 215_000) == pytest.approx(7.74)


def test_lp_fee():
    assert d.c_lp(10_000, 5) == pytest.approx(5.0)


def test_slippage_grows_with_size_squared():
    a, b = d.c_slip(1000, 1e6), d.c_slip(2000, 1e6)
    assert b == pytest.approx(4 * a)


def test_peg_is_absolute_deviation():
    assert d.c_peg(1000, 0.998) == pytest.approx(2.0)
    assert d.c_peg(1000, 1.002) == pytest.approx(2.0)


def test_premium_is_signed_negative_cost():
    assert d.c_prem(1000, 0.5) == pytest.approx(-5.0)
    assert d.c_prem(1000, -0.5) == pytest.approx(5.0)


def test_ramp_and_reg_and_fx():
    assert d.c_ramp(1000, 2.0, 50) == pytest.approx(7.0)
    assert d.c_reg(1000, 100) == pytest.approx(10.0)
    assert d.c_fx(1000, 2, 8) == pytest.approx(1.0)


@pytest.fixture
def state():
    return pd.DataFrame({"ts": pd.to_datetime(["2026-03-01"], utc=True), "base_fee_gwei": [10.0],
                         "priority_fee_gwei": [2.0], "eth_usd": [3000.0], "fee_bps": [1.0],
                         "depth_1pct_usd": [2e7], "peg_price_usd": [0.9995], "premium_pct": [0.4],
                         "fx_spread_bps": [2.0]})


def test_paths_use_only_their_terms(state):
    params = load_params()
    p0 = path_costs("P0", 1000, state, params).iloc[0]
    p1 = path_costs("P1", 1000, state, params).iloc[0]
    p2 = path_costs("P2", 1000, state, params).iloc[0]
    assert p0[["c_gas", "c_lp", "c_slip", "c_peg", "c_prem"]].abs().sum() == 0
    assert p2[["c_gas", "c_lp", "c_slip", "c_peg"]].abs().sum() == 0
    assert p1["c_gas"] > 0 and p1["c_lp"] > 0 and p1["c_prem"] < 0


def test_totals_are_consistent(state):
    r = path_costs("P1", 1000, state, load_params()).iloc[0]
    assert r["total"] == pytest.approx(sum(r[t] for t in TERMS))
    assert r["total_ex_prem"] == pytest.approx(r["total"] - r["c_prem"])
    assert r["total_bps"] == pytest.approx(r["total_ex_prem"] / 1000 * 1e4)


def test_fixed_fees_hurt_small_transfers(state):
    params = load_params()
    small = path_costs("P0", 200, state, params).iloc[0]["total_bps"]
    large = path_costs("P0", 10000, state, params).iloc[0]["total_bps"]
    assert small > large
