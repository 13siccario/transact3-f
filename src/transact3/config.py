"""Experiment config loading. Every run is defined by a YAML file and a seed."""
from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path

import yaml


@dataclass(frozen=True)
class Config:
    raw: dict
    path: Path
    hash: str

    def __getitem__(self, key):
        return self.raw[key]

    def get(self, key, default=None):
        return self.raw.get(key, default)

    @property
    def seed(self) -> int:
        return int(self.raw["seed"])

    @property
    def mode(self) -> str:
        return self.raw["mode"]


def load_config(path: str | Path) -> Config:
    path = Path(path)
    text = path.read_text()
    raw = yaml.safe_load(text)
    for key in ("name", "seed"):
        if key not in raw:
            raise ValueError(f"config {path} is missing required key '{key}'")
    if "mode" in raw and raw["mode"] not in ("synthetic", "real"):
        raise ValueError("mode must be 'synthetic' or 'real'")
    digest = hashlib.sha256(text.encode()).hexdigest()[:12]
    return Config(raw=raw, path=path, hash=digest)
