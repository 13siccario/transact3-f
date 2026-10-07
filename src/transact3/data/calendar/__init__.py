"""Regulatory event calendar loader."""
from __future__ import annotations

from pathlib import Path

import pandas as pd
import yaml

EVENTS_FILE = Path(__file__).with_name("events.yaml")


def load_events(verified_only: bool = False) -> pd.DataFrame:
    rows = yaml.safe_load(EVENTS_FILE.read_text())["events"]
    df = pd.DataFrame(rows)
    df["date"] = pd.to_datetime(df["date"], utc=True)
    if verified_only:
        df = df[(df["status"] == "verified") & df["primary_source"].notna() & df["date"].notna()]
    return df.reset_index(drop=True)


def validate_events() -> list[str]:
    """Return problems: a 'verified' event must have a date and a primary source."""
    problems = []
    for _, e in load_events().iterrows():
        if e["status"] == "verified" and (pd.isna(e["date"]) or not e["primary_source"]):
            problems.append(f"{e['id']}: verified without date or primary_source")
    return problems
