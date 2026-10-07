# Data terms and licence review

Status: **not started**. Nothing here is a legal conclusion. Before any dataset or derived series is
released with the code, a person must read each source's current terms and record the result.

| Source | Used for | Terms read? | Redistribution of raw data | Redistribution of derived series | Attribution required | Notes |
|---|---|---|---|---|---|---|
| Tick-data provider (hourly USD/INR and majors) | FX | no | _unknown_ | _unknown_ | _unknown_ | Hourly INR availability still unconfirmed (probe returned 404 for USDINR) |
| FBIL / RBI reference rates | Daily FX fallback | no | _unknown_ | _unknown_ | _unknown_ | |
| USDT/INR price history provider | Local premium | no | _unknown_ | _unknown_ | _unknown_ | Check free-tier limits and commercial-use terms |
| Pool / DEX analytics provider | Pool depth, fees | no | _unknown_ | _unknown_ | _unknown_ | |
| Gas data (block explorer or RPC) | Gas | no | _unknown_ | _unknown_ | _unknown_ | |
| Stablecoin price series | Peg | no | _unknown_ | _unknown_ | _unknown_ | |
| World Bank RPW, RBI survey, BIS/CPMI | Paper 1 calibration | no | _unknown_ | _unknown_ | _unknown_ | Pull numbers from the primary documents |

Until this table is complete the repository releases **code and synthetic data only**. Real raw data
stays in the git-ignored `data/` folders.
