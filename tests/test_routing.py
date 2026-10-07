import numpy as np
import pytest

from transact3.eval.harness import run_policy, summarise
from transact3.routing.compliance import ComplianceViolation
from transact3.routing.linucb import LinUCB
from transact3.routing.rules import Fixed, Planner, Policy
from transact3.sim.env import RoutingEnv
from transact3.sim.rails import rails_for


def env(eligible=("CB", "LR", "SC"), **kw):
    return RoutingEnv(rails_for("none"), list(eligible), seed=7, **kw)


def test_oracle_never_costs_more_than_greedy_on_same_world():
    out = {}
    for pol in (Planner("none"), Planner("perfect", margin=0)):
        out[pol.name] = summarise(run_policy(env(), pol, 400, seed=11)).total_bps.iloc[0]
    assert out["oracle"] <= out["greedy"] + 1.0


def test_policies_never_choose_ineligible_rails():
    for pol in (Fixed("SC"), Planner("none"), Planner("perfect", margin=0), LinUCB()):
        df = run_policy(env(eligible=("CB", "LR")), pol, 150, seed=3)
        assert set(df["rail"]) <= {"CB", "LR"}, pol.name


def test_adversarial_policy_is_stopped_by_the_filter():
    class Rogue(Policy):
        name = "rogue"
        def act(self, e, obs):
            return 1 + 2     # always tries SC
    with pytest.raises(ComplianceViolation):
        run_policy(env(eligible=("CB", "LR")), Rogue(), 5, seed=1)


def test_runs_are_reproducible_for_a_seed():
    a = run_policy(env(), Planner("none"), 100, seed=5)
    b = run_policy(RoutingEnv(rails_for("none"), ["CB", "LR", "SC"], seed=7), Planner("none"), 100, seed=5)
    assert np.allclose(a["total_bps"], b["total_bps"])


def test_linucb_learns_to_beat_a_bad_fixed_rail():
    e = env()
    lin = summarise(run_policy(e, LinUCB(), 1500, seed=2)).total_bps.iloc[0]
    cb = summarise(run_policy(env(), Fixed("CB"), 1500, seed=2)).total_bps.iloc[0]
    assert lin < cb
