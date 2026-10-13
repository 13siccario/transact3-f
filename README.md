# transact3

Research code for cross-border FX, payment-rail routing and stablecoin costs into India. Results are research findings, not legal or financial advice. See `PROJECT_PLAN.md`.

```
make setup        # Python 3.12 venv + editable install
make test
make reproduce    # everything above plus the feasibility report (about 40 minutes)
make forecast     # walk-forward forecasts, DM tests, z(t)
make sim          # Paper 1 simulator experiments
make replay       # Paper 2 replay + Paper 1 empirical-stablecoin robustness
make api          # FastAPI on :8000
make web          # Next.js dashboard on :3000 (run `npm install` in web/ first)
```

## Run the app

The dashboard needs both servers, each in its own terminal, from the repo root:

```
make setup                 # once
(cd web && npm install)    # once
make api                   # backend: http://127.0.0.1:8000 (API docs at /docs)
make web                   # frontend: http://localhost:3000
```

**Synthetic data:** until Phase 0 confirms real sources, all datasets are generated (`source_kind=synthetic`, seeded by the config). They exercise the pipeline and UI only and must not be used for paper results.

Layout: `src/transact3/{data,costs,forecast,sim,routing,eval}`, `configs/` (one YAML per experiment), `docs/`, `api/`, `web/`, `paper1/`, `paper2/`.

See `USER_JOURNEY.md` for how the app is used, `PROJECT_PLAN.md` for status, and `docs/release_checklist.md` for what is left before release.
