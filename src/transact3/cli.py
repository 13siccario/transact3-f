"""Command line: `transact3 build-data`, `transact3 forecast`, `transact3 feasibility`."""
from __future__ import annotations

import argparse
from pathlib import Path

from .config import load_config
from .data import pipeline
from .data.calendar import validate_events
from .data.probes import render_report, run_probes


def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="transact3")
    sub = p.add_subparsers(dest="cmd", required=True)
    b = sub.add_parser("build-data", help="collect, clean and store datasets for a config")
    b.add_argument("--config", required=True)
    f = sub.add_parser("feasibility", help="probe candidate data sources and write the report")
    f.add_argument("--out", default="docs/data_feasibility_report.md")
    fc = sub.add_parser("forecast", help="run walk-forward forecasts, DM tests and write z(t)")
    fc.add_argument("--config", default="configs/forecast.yaml")
    sm = sub.add_parser("run-sim", help="Paper 1: simulator experiments, ablations and sensitivity")
    sm.add_argument("--config", default="configs/sim.yaml")
    rp = sub.add_parser("run-replay", help="Paper 2: historical replay, legal-status sensitivity; Paper 1 empirical robustness")
    rp.add_argument("--config", default="configs/replay.yaml")
    rp.add_argument("--sim-config", default="configs/sim.yaml")
    args = p.parse_args(argv)

    if args.cmd == "build-data":
        problems = validate_events()
        if problems:
            raise SystemExit("event calendar invalid:\n" + "\n".join(problems))
        cfg = load_config(args.config)
        m = pipeline.build(cfg)
        print(f"built {len(m['datasets'])} datasets ({m['mode']}), config hash {m['config_hash']}")
    elif args.cmd == "forecast":
        import json
        import pandas as pd
        from .forecast import validation as v
        cfg = load_config(args.config)
        data = Path(cfg["data_dir"])
        manifest = json.loads((data / "manifest.json").read_text())
        processed = {n: pd.read_parquet(data / f"{n}.parquet") for n in manifest["datasets"]}
        preds = v.run_forecasts(cfg, processed, manifest["mode"])
        metrics = v.score(preds, cfg["benchmark"], cfg["horizon"])
        out = v.save(cfg, preds, metrics, manifest["mode"], manifest["config_hash"])
        print(f"wrote {len(preds)} forecasts and {len(metrics)} metric rows to {out}")
    elif args.cmd == "run-sim":
        from .eval.paper1 import run_paper1
        meta = run_paper1(load_config(args.config))
        print("paper1 done:", {k: meta[k] for k in ("config_hash", "break_even_noise", "sensitivity")})
    elif args.cmd == "run-replay":
        from .eval.paper1 import run_paper1
        from .eval.replay import build_empirical, load_data, run_paper2
        cfg = load_config(args.config)
        data = load_data(cfg)
        meta = run_paper2(cfg, data)
        print("paper2 done:", meta)
        m1 = run_paper1(load_config(args.sim_config), empirical=build_empirical(data), tag="_empirical_sc")
        print("paper1 empirical-SC robustness done:", {k: m1[k] for k in ("config_hash", "break_even_noise")})
    elif args.cmd == "feasibility":
        report = render_report(run_probes())
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out).write_text(report)
        print(f"wrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
