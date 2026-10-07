import numpy as np
import pandas as pd
import pytest

from transact3.forecast import baselines as bl
from transact3.forecast.panel import build_features
from transact3.forecast.tests import dm_test
from transact3.forecast.validation import walk_forward_folds


def test_dm_identical_forecasts_are_undefined():
    e = np.random.default_rng(0).normal(size=200)
    stat, p = dm_test(e, e)
    assert np.isnan(stat) and np.isnan(p)


def test_dm_detects_better_model_and_sign_flips():
    rng = np.random.default_rng(1)
    e_bench = rng.normal(0, 1.0, 500)
    e_model = rng.normal(0, 0.6, 500)
    stat, p = dm_test(e_bench, e_model)
    assert stat > 0 and p < 0.01
    stat2, _ = dm_test(e_model, e_bench)
    assert stat2 == pytest.approx(-stat)


def test_dm_equal_accuracy_is_not_significant():
    rng = np.random.default_rng(2)
    stat, p = dm_test(rng.normal(size=500), rng.normal(size=500))
    assert p > 0.01


def test_ar_recovers_coefficient():
    rng = np.random.default_rng(3)
    y = np.zeros(5000)
    for t in range(1, 5000):
        y[t] = 0.7 * y[t - 1] + rng.normal()
    coef = bl.fit_ar(y, 1)
    assert coef[1] == pytest.approx(0.7, abs=0.05)


def test_garch_sigma_positive_and_uses_only_past():
    rng = np.random.default_rng(4)
    r = rng.normal(0, 0.001, 600)
    g = {"mu": 0.0, "omega": 1e-8, "alpha": 0.1, "beta": 0.85, "var0": 1e-6}
    idx = np.arange(300, 400)
    s1 = bl.garch_sigma(r, g, idx)
    r2 = r.copy()
    r2[450:] *= 100                                   # shock strictly after the test origins
    assert (s1 > 0).all() and np.allclose(s1, bl.garch_sigma(r2, g, idx))


def test_random_walk_return_is_zero_and_level_is_last_value():
    y = pd.Series([1.0, 2.0, 3.0])
    assert (bl.random_walk(y, "fx_return", np.array([0, 1])) == 0).all()
    assert bl.random_walk(y, "gas_gwei", np.array([0, 1])).tolist() == [1.0, 2.0]


def test_features_have_no_lookahead():
    idx = pd.date_range("2026-01-01", periods=400, freq="1h", tz="UTC")
    rng = np.random.default_rng(5)
    panel = pd.DataFrame({"a": rng.normal(size=400), "b": rng.normal(size=400)}, index=idx)
    f1 = build_features(panel, ["a", "b"], [0, 1, 6, 24], [6, 24])
    changed = panel.copy()
    changed.iloc[300:] += 1000                        # perturb everything after origin 299
    f2 = build_features(changed, ["a", "b"], [0, 1, 6, 24], [6, 24])
    pd.testing.assert_frame_equal(f1.iloc[:300], f2.iloc[:300])


def test_walk_forward_never_trains_on_unobserved_labels():
    valid = np.arange(72, 4000)
    folds = list(walk_forward_folds(valid, 0.5, 168, horizon=1))
    assert len(folds) > 5
    seen = []
    for train, test in folds:
        assert train.max() + 1 <= test.min()          # every training label observed by first test origin
        assert train.max() < test.min() and len(set(train) & set(test)) == 0
        seen.extend(test.tolist())
    assert seen == sorted(set(seen))                  # test blocks are disjoint and in time order
