import numpy as np
import pytest

from transact3.routing.compliance import ComplianceViolation
from transact3.sim.env import K, RoutingEnv
from transact3.sim.rails import ALL_RAILS, rails_for


def make(eligible=("CB", "LR", "SC"), **kw):
    return RoutingEnv(rails_for("none"), list(eligible), seed=1, **kw)


def test_reset_and_obs_shape():
    env = make()
    obs, _ = env.reset(seed=3)
    assert obs.shape == env.observation_space.shape and np.isfinite(obs).all()


def test_mask_hides_ineligible_rails_and_never_empty():
    env = make(eligible=("CB", "LR"))
    for s in range(20):
        env.reset(seed=s)
        m = env.action_masks()
        assert not m[1 + ALL_RAILS.index("SC")] and not m[1 + ALL_RAILS.index("CBDC")]
        assert m.any()


def test_sending_on_ineligible_rail_is_a_violation():
    env = make(eligible=("CB", "LR"))
    env.reset(seed=0)
    with pytest.raises(ComplianceViolation):
        env.step(1 + ALL_RAILS.index("SC"))


def test_wait_forbidden_near_deadline_and_episode_ends_on_send():
    env = make()
    env.reset(seed=5)
    steps = 0
    while env.wait_allowed():
        env.step(0)
        steps += 1
        assert steps < 100
    with pytest.raises(ValueError):
        env.step(0)
    legal = np.flatnonzero(env.action_masks()[1:])[0]
    _, r, done, _, info = env.step(1 + legal)
    assert done and r == pytest.approx(-info["total_bps"] / 100)


def test_buffer_depletes_and_refills():
    env = make()
    env.reset(seed=2)
    i = ALL_RAILS.index("LR")
    before = env.buffer["LR"]
    if env.action_masks()[1 + i]:
        _, _, _, _, info = env.step(1 + i)
        assert env.buffer["LR"] == pytest.approx(before - info["amount"])
        assert env.level("LR", env.buf_time + 10) > before - info["amount"]


def test_forecast_kinds():
    env = make()
    env.reset(seed=4)
    now = env.cost_now()
    none = env.forecast_matrix("none")
    perfect = env.forecast_matrix("perfect")
    assert np.allclose(none[:, 0], now) and np.allclose(none, none[:, :1])
    assert np.allclose(perfect[:, 0], now)
    noisy0 = env.forecast_matrix("noisy", 0.0)
    assert np.allclose(noisy0, perfect)           # zero noise equals perfect foresight
    assert env.forecast_matrix("model").shape == (K, 12)


def test_all_policies_face_identical_transfers():
    from transact3.eval.harness import run_policy
    from transact3.routing.rules import Fixed, Planner
    a = run_policy(make(), Planner("none"), 120, seed=9)
    b = run_policy(make(), Planner("perfect", margin=0), 120, seed=9)
    c = run_policy(make(), Fixed("LR"), 120, seed=9)
    assert (a["amount"].to_numpy() == b["amount"].to_numpy()).all() and (a["amount"].to_numpy() == c["amount"].to_numpy()).all()
    assert (a["deadline_h"].to_numpy() == b["deadline_h"].to_numpy()).all()


def test_expected_penalty_matches_monte_carlo():
    from transact3.sim.env import FAIL_PEN_BPS, LATE_BASE_BPS, LATE_PER_H_BPS
    env = make()
    env.reset(seed=6)
    rng = np.random.default_rng(0)
    for name in ("CB", "LR", "SC"):
        i = ALL_RAILS.index(name)
        r = env.rails[name]
        mu = r.lat_mu + (np.log(1.5) if env.world.stress[min(env.t, env.world.T - 1)] else 0.0)
        for tau in (0, 2):
            d = env.D - (env.k + tau)
            L = rng.lognormal(mu, r.lat_sigma, 400_000)
            mc = LATE_BASE_BPS * (L > d).mean() + LATE_PER_H_BPS * np.maximum(L - d, 0).mean() + r.p_fail * FAIL_PEN_BPS
            assert env.expected_penalty(i, tau) == pytest.approx(mc, rel=0.03, abs=0.2)
