# Paper 2 (draft skeleton): The cost anatomy of compliant stablecoin transfers into India

> Status: skeleton. Every number must come from `paper2/tables/` after a run on **observed** data.
> Today's tables use synthetic data, so nothing here may be submitted as a finding.
> Hypotheses H1 to H7 must be written before results are read; they are not in the plan text and are left blank.

## Abstract
_Write last, from actual numbers only._

## 1. Introduction
_Question: what does the stablecoin path into India cost, which parts are forecastable, and does forecast-aware venue selection help?_

## 2. Institutional background
_Every regulatory or tax fact must trace to a primary document. The event calendar (`src/transact3/data/calendar/events.yaml`) lists leads only; none is verified yet, including the June 2026 episode._

## 3. Hypotheses
| ID | Statement |
|---|---|
| H1 to H7 | _authors to state before results_ |

## 4. Data
Hourly FX, local USDT/INR, on-chain pool depth and fees, gas, and peg series (see `docs/data_feasibility_report.md`). **Open:** hourly USD/INR availability (probe returned 404), intraday USDT/INR, and an INR-referenced liquid pool. State the scope that results if a non-INR proxy is used. Data terms review: `docs/data_terms_review.md` (not started).

## 5. Cost decomposition
C_gas, C_lp, C_slip, C_peg, C_prem, C_ramp, C_reg and C_fx for paths P0 (conventional), P1 (compliant stablecoin), P2 (onshore exchange). The premium is reported separately and never counted as a gain. All fee and tax parameters are provisional. See `src/transact3/costs/`.

## 6. Results
- Cost anatomy by size and regime (Tables 2 and 3, from the cost engine; Costs page)
- Forecastability and stress (Table 5; `data/processed/forecast/metrics.parquet`)
- Replay of venue selection, compliant paths only (`paper2/tables/table6_replay.md`, `table6b_regimes.md`, `table6c_paired.md`; `figures/fig_cum_regret.png`)
- Legal-status sensitivity: P2 excluded, included with cost, included (`table7_legal_status.md`)

Note the overlap with Paper 1 and cite it: distinct data, questions and evaluation.

## 7. Limitations
_Few stress episodes (low regime power); hourly replay windows overlap, hence block-bootstrap intervals; one-hour forecast horizon; nominal settlement times._

## 8. Ethics, scope and declarations
- Research findings, not legal or financial advice. The compliance filter is a hard constraint on the action set; the rules file is versioned and must be reviewed by a person before real-data runs.
- Data, code, competing interests and AI-use declarations: _authors to complete._

## References
_To add and verify._
