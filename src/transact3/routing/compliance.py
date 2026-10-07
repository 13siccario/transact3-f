"""Compliance filter: the eligible action set is a hard constraint, enforced in code.

Policies receive a mask built from `eligible_*`. `guard` raises if any chosen action is outside
the set, so a buggy or adversarial policy cannot act on an ineligible rail.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml

RULES_FILE = Path("configs/compliance_rules.yaml")


class ComplianceViolation(RuntimeError):
    pass


@dataclass(frozen=True)
class Rules:
    version: str
    reviewed_by: str | None
    default_scenario: str
    scenarios: dict
    sim_rails: dict

    def eligible_paths(self, scenario: str | None = None) -> list[str]:
        return list(self._scenario(scenario)["eligible_paths"])

    def extra_cost_bps(self, scenario: str | None, path: str) -> float:
        return float(self._scenario(scenario).get("extra_cost_bps", {}).get(path, 0.0))

    def eligible_rails(self, cbdc: str = "none") -> list[str]:
        rails = list(self.sim_rails["always"])
        if cbdc in self.sim_rails["cbdc_scenarios"]:
            rails.append("CBDC")
        return rails

    def _scenario(self, scenario: str | None) -> dict:
        name = scenario or self.default_scenario
        if name not in self.scenarios:
            raise KeyError(f"unknown legal scenario '{name}'; options: {sorted(self.scenarios)}")
        return self.scenarios[name]


def load_rules(path: str | Path = RULES_FILE) -> Rules:
    raw = yaml.safe_load(Path(path).read_text())
    return Rules(raw["version"], raw.get("reviewed_by"), raw["default_scenario"], raw["scenarios"], raw["sim_rails"])


def require_reviewed(rules: Rules, mode: str) -> None:
    """Real-data runs are refused until a person has reviewed the rules file."""
    if mode == "real" and not rules.reviewed_by:
        raise ComplianceViolation("compliance_rules.yaml has not been reviewed (reviewed_by is empty); refusing a real-data run")


def guard(action: str, eligible: list[str]) -> str:
    if action not in eligible:
        raise ComplianceViolation(f"action '{action}' is outside the eligible set {eligible}")
    return action
