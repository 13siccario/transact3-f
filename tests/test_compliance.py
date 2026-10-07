import pytest

from transact3.routing.compliance import ComplianceViolation, guard, load_rules, require_reviewed


def test_default_scenario_is_conservative():
    r = load_rules()
    assert r.eligible_paths() == ["P0", "P1"]


def test_scenarios_differ_only_by_p2_and_cost():
    r = load_rules()
    assert "P2" not in r.eligible_paths("p2_excluded")
    assert "P2" in r.eligible_paths("p2_included_with_cost")
    assert r.extra_cost_bps("p2_included_with_cost", "P2") > 0
    assert r.extra_cost_bps("p2_included", "P2") == 0


def test_unknown_scenario_raises():
    with pytest.raises(KeyError):
        load_rules().eligible_paths("nope")


def test_cbdc_rail_only_in_cbdc_scenarios():
    r = load_rules()
    assert "CBDC" not in r.eligible_rails("none")
    assert "CBDC" in r.eligible_rails("pilot") and "CBDC" in r.eligible_rails("mature")


def test_guard_blocks_ineligible_action():
    assert guard("P1", ["P0", "P1"]) == "P1"
    with pytest.raises(ComplianceViolation):
        guard("P2", ["P0", "P1"])


def test_real_runs_refused_until_rules_reviewed():
    r = load_rules()
    require_reviewed(r, "synthetic")
    with pytest.raises(ComplianceViolation):
        require_reviewed(r, "real")
