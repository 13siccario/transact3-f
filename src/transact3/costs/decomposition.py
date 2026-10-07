"""Cost terms. Each takes transfer size `amount` (USD) and market state, returns USD cost.

Positive = cost to the sender/recipient. All terms accept scalars or pandas Series.
C_prem is signed: a positive local premium means the recipient sells USDT above the
reference rate, which shows up as a NEGATIVE cost. It is reported separately and
all-in totals are given with and without it. It is never a free gain: it reflects
frictions and rules that the compliance filter and legal notes must accompany.
"""
from __future__ import annotations

GWEI = 1e-9


def c_gas(base_fee_gwei, priority_fee_gwei, eth_usd, gas_units):
    return gas_units * (base_fee_gwei + priority_fee_gwei) * GWEI * eth_usd


def c_lp(amount, fee_bps):
    return amount * fee_bps / 1e4


def c_slip(amount, depth_1pct_usd):
    """Linear price impact: moving the pool 1% costs ~1% of depth; impact scales with size/depth."""
    return amount * 0.01 * amount / (2 * depth_1pct_usd)


def c_peg(amount, price_usd):
    """Cost of the stablecoin trading away from $1 at settlement."""
    return amount * abs(price_usd - 1.0)


def c_prem(amount, premium_pct):
    """Signed. Positive premium lowers cost to the recipient (negative cost). Report, don't chase."""
    return -amount * premium_pct / 100


def c_ramp(amount, fixed_usd, bps):
    return fixed_usd + amount * bps / 1e4


def c_reg(amount, reg_bps):
    return amount * reg_bps / 1e4


def c_fx(amount, spread_bps, extra_bps):
    """FX spread on the INR conversion leg, plus provider margin."""
    return amount * (spread_bps + extra_bps) / 1e4
