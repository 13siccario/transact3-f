# Data feasibility report

Generated 2026-10-06 18:22 UTC by `transact3 feasibility`. Phase 0 of the project plan.

A reachable endpoint is **not** a go decision. A go needs: confirmed history covering the sample period,
the right frequency, and acceptable source terms. Decisions below are left blank until a person records them.

| Component | Candidate endpoint | Probe result | Detail | Decision (go / no-go) | Notes |
|---|---|---|---|---|---|
| USD/INR hourly (tick provider) | Dukascopy datafeed, USDINR | unreachable | ReadTimeout: The read operation timed out | _pending_ | |
| USD/INR hourly (control: EURUSD) | Dukascopy datafeed, EURUSD | reachable | HTTP 200, 20757 bytes | _pending_ | |
| USD/INR daily reference | FBIL site (reachability only) | reachable | HTTP 200, 1519 bytes | _pending_ | |
| Local USDT/INR history | CoinGecko market_chart (tether, inr, 30d) | reachable | HTTP 200, 73973 bytes | _pending_ | |
| On-chain pools | DefiLlama yields pools | reachable | HTTP 200, 11577951 bytes | _pending_ | |
| Peg deviation | DefiLlama stablecoins | reachable | HTTP 200, 558291 bytes | _pending_ | |
| Gas fees | Public Ethereum JSON-RPC eth_feeHistory | reachable | HTTP 200 | _pending_ | |

## Still manual

- INR-referenced on-chain token: is there any liquid pool? If not, use non-INR EM proxies (decision gate).
- Regulatory event calendar: every event needs a primary source (see `src/transact3/data/calendar/events.yaml`).
- Sample period must include the June 2026 episode once it is traced to a primary document.
