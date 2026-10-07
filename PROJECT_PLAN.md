# transact3: project plan (v2)

Builds on `PROJECT PLAN.pdf` (Draft v1). Paper 2's observed data feeds Paper 1's simulator, never the reverse.
Non-goals: live trading, legal or investment advice, any tool that helps route around exchange controls.

## Decisions
| Topic | Decision |
|---|---|
| Deliverable | Research pipeline (Python) + dashboard (FastAPI + Next.js) |
| Dashboard pages | Cost anatomy + regime timeline; forecast panel; router replay + simulator playground |
| Dropped | Fairness view, legal-status toggle, data-health page. The "research, not advice" disclaimer stays everywhere |
| Data | Collectors behind one interface; synthetic fixtures flagged `source_kind=synthetic` end to end until real sources get a go |
| Capacity | Solo; code generated with Claude |
| UI | Follows `references/` (see `DESIGN.md`) |
| Stretch | PPO and TFT only if LinUCB leaves E3 unanswered / time remains |

## Design rules (unchanged)
1. The compliance filter is a hard constraint on the action set; no model overrides it.
2. Every feature is measurable at the forecast origin (no lookahead).
3. Every experiment = config file + seed; results saved with the config hash.
4. Paper 1 = simulator; Paper 2 = observed data and replay. Keep distinct.
5. Facts from news/explainer sites are leads. Only primary documents are citations.

## Phases
| # | Phase | Exit criterion | Status |
|---|---|---|---|
| 1 | Foundation + data layer: skeleton, config/seed, collector interface, synthetic generators, cleaning, DuckDB/Parquet, feasibility probes, event calendar | Pipeline runs end to end on synthetic data; feasibility report exists | **Done** |
| 2 | Cost engine (C_gas, C_lp, C_slip, C_peg, C_prem, C_ramp, C_reg; P0/P1/P2) + unit tests; FastAPI skeleton; Next.js shell; cost-anatomy and regime-timeline pages | Cost anatomy page works against the API | **Done**: 8 cost terms (7 from the plan + C_fx), 3 paths, 21 tests, API (`make api`), UI (`make web`). Fee and tax parameters are provisional |
| 3 | Forecasting: baselines, LightGBM, multi-task LSTM, walk-forward, Diebold-Mariano, regime split, no-lookahead test; forecast panel | z(t) available to routers | **Done**: 7 targets, 6 models, 13 weekly refits, DM tests by regime, `make forecast`, Forecasts page. Scores are on synthetic data |
| 4 | Simulator + routing: rails, generator, Gymnasium env, fixed/greedy/oracle/LinUCB/PPO, compliance filter, ablations, sensitivity, Paper 2 replay; Replay page, Simulate page | Result tables regenerate from config | **Done**: `make sim`, `make replay`; PPO included (masked, 300k steps); user transaction simulation with playback |
| 5 | Hardening + release: wire real sources where Phase 1 gave a go, Docker, `make reproduce`, data-terms review, docs, manuscript skeletons, tagged release | One command reproduces tables and figures | **Partly done**: `make reproduce`, lockfile, Dockerfiles, data-terms template, release checklist, manuscript skeletons, `USER_JOURNEY.md`. **Blocked on you**: real-source go decisions, calibration from primary sources, rules review, journals, git repo and tag |

## Open items
- Phase 0 decisions are pending: see `docs/data_feasibility_report.md`. Dukascopy probe was rate-limited (HTTP 429), so hourly USD/INR is still unconfirmed.
- The June 2026 episode and the 2022 tax events are leads in `src/transact3/data/calendar/events.yaml` until traced to primary sources.
- Journals, transfer-size grid (default 200 / 1,000 / 10,000 USD), sample period.

## Notes from Phase 3
- Level targets that leave the training range (premium, slippage, peg, gas, spread) are forecast as change from the origin value (`delta_targets` in `configs/forecast.yaml`). Forecasting levels made LightGBM and the LSTM look 20x worse than a random walk purely because trees cannot extrapolate.
- LightGBM and torch both run single-threaded: their OpenMP runtimes clash and hang on macOS otherwise.
- Synthetic results are built in: returns are unforecastable and volatility clusters by construction, so GARCH winning on volatility is a pipeline check, not a finding.

## Notes from Phase 4
- Greedy, forecast-aware and oracle are one planner shown different forecasts, so the forecast ablation is exact.
- Policies are compared on identical worlds and transfers (separate random streams for market, arrivals and outcomes) with paired confidence intervals across worlds.
- The planner's lateness risk uses the exact lognormal expected penalty. An earlier 0/1 flag at the 90th percentile made planners wait to the deadline edge and lose to sending now.
- Forecasts are clipped to physical values (no negative fees); a negative predicted gas fee had produced a negative cost and NaN inputs to PPO.
- With scarce liquidity, a per-transfer planner, even with perfect foresight, can lose to sending now. With abundant liquidity the oracle beats sending now by about 12 bps in the empirical stablecoin world. Mechanism is a hypothesis, not tested.
- PPO needed far more training than first assumed (30k steps was 18 bps behind LinUCB; 300k steps is about 3 bps behind). Do not report E3 from an under-trained agent.
