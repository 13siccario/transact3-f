"""Write result tables as CSV (machine) and Markdown (manuscript), with a caption."""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd


def _fmt(v, nd):
    if isinstance(v, (float, np.floating)):
        return "" if np.isnan(v) else f"{v:.{nd}f}"
    return str(v)


def to_markdown(df: pd.DataFrame, nd: int = 2) -> str:
    cols = list(df.columns)
    lines = ["| " + " | ".join(cols) + " |", "|" + "|".join("---" for _ in cols) + "|"]
    for _, r in df.iterrows():
        lines.append("| " + " | ".join(_fmt(r[c], nd) for c in cols) + " |")
    return "\n".join(lines)


def write_table(df: pd.DataFrame, out_dir: str | Path, name: str, caption: str, nd: int = 2) -> None:
    out = Path(out_dir) / "tables"
    out.mkdir(parents=True, exist_ok=True)
    df.to_csv(out / f"{name}.csv", index=False)
    (out / f"{name}.md").write_text(f"**{caption}**\n\n{to_markdown(df, nd)}\n")
