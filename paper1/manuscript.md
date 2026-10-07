# Paper 1 (draft skeleton): Forecast-aware routing across payment rails in a calibrated simulator

> Status: skeleton. Every number below must come from `paper1/tables/` after a run on **calibrated** parameters.
> Today's tables use synthetic data and placeholder parameters, so nothing here may be submitted as a finding.
> Hypotheses H1 to H4 must be written down by the authors **before** results are read. They are not in the project plan text, so they are left blank here on purpose.

## Abstract
_Write last, from actual numbers only._

## 1. Introduction
_Motivation: cross-border cost, rail choice, role of forecasts. Contribution: a method comparison in a simulator whose parameters are public-benchmark calibrated, with sensitivity analysis._

## 2. Background and related work
_To write with verified references only._

## 3. Hypotheses
| ID | Statement | Test |
|---|---|---|
| H1 | _authors to state before results_ | |
| H2 | _authors to state before results_ | |
| H3 | _authors to state before results_ | |
| H4 | _authors to state before results_ | |

## 4. Simulator
- Rails: correspondent banking (CB), linked instant rails (LR), stablecoin (SC), CBDC bridge (scenario-only). See `src/transact3/sim/rails.py`.
- Market: AR(1) log-cost shocks, a two-state stress regime, daily cycles on some rails. See `sim/world.py`.
- Transfers: Poisson arrivals, lognormal sizes, deadlines of 6, 24 or 72 hours. See `sim/generator.py`.
- MDP: one episode per transfer; actions are wait or send via a rail; liquidity buffers persist across episodes; reward is negative cost with failure and lateness penalties. See `sim/env.py`.
- Compliance: eligible rails come from a versioned rules file and are enforced before any policy acts. See `routing/compliance.py`.
- **Calibration table (to complete):** each parameter with its primary source (World Bank RPW, RBI remittance survey, BIS/CPMI speed statistics). Currently every value is a placeholder.

## 5. Methods compared
Fixed rail, greedy (send now), forecast-aware planner (one planner, forecast kind varies: none, model, noisy, perfect), disjoint LinUCB with delayed feedback, masked PPO (300,000 steps, trained once on a separate world), and perfect-foresight oracle (note: plans one transfer at a time, so it is not a global optimum under scarce liquidity).

## 6. Results
- Table 5 (`paper1/tables/table5_main.md`), 5b by size segment (`table5b_segments.md`)
- Table 6 forecast ablation (`table6_ablation.md`); Figure 2 and E4 noise sweep (`figures/fig2_forecast_value.png`, `table_e4_noise.md`)
- E3 PPO versus LinUCB across liquidity (`table_e3_liquidity.md`)
- E5 sensitivity: parameter draws and CBDC scenarios (`table_e5_draws.md`, `table_e5_cbdc.md`)
- Robustness with the empirical stablecoin cost process from Paper 2 (`*_empirical_sc.md`)

Report null results. Report cost and failure rates by size segment so small senders are visible.

## 7. Limitations
_Simulator realism; placeholder calibration; single-transfer planning; PPO budget; synthetic stablecoin process outside the robustness check._

## 8. Ethics, scope and declarations
- Research findings, not legal or financial advice. Not a tool for avoiding exchange controls; eligibility is a hard constraint.
- Data: public and aggregate only; no personal data.
- Code: repository and tagged release (to complete).
- Competing interests: _authors to complete._
- AI use: _authors to complete and confirm. Code in this repository was generated with the assistance of Claude (Anthropic) and reviewed by the authors._

## References
_To add. Verify each against the original source._
