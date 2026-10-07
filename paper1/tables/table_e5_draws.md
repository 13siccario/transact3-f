**E5. Policy ranking across parameter draws (Kendall tau against the baseline ranking)**

| draw | kendall_tau | best_policy | model_beats_greedy | linucb_beats_greedy | bps_fixed_CB | bps_fixed_LR | bps_fixed_SC | bps_greedy | bps_forecast_model | bps_linucb | bps_oracle |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 0 | 0.90 | greedy | False | False | 406.01 | 117.86 | 265.62 | 116.30 | 117.69 | 121.01 | 111.75 |
| 1 | 0.52 | greedy | False | False | 486.35 | 126.55 | 330.96 | 126.38 | 139.20 | 134.74 | 128.90 |
| 2 | 1.00 | forecast_model | True | False | 418.28 | 121.56 | 266.88 | 119.03 | 114.77 | 123.87 | 107.76 |
| 3 | 0.81 | greedy | False | False | 447.07 | 132.33 | 380.24 | 128.87 | 134.48 | 138.51 | 127.17 |
| 4 | 1.00 | forecast_model | True | False | 364.86 | 127.53 | 252.33 | 122.32 | 119.89 | 130.72 | 113.17 |
| 5 | 0.81 | greedy | False | False | 355.40 | 119.57 | 335.99 | 118.23 | 121.57 | 126.43 | 116.42 |
| 6 | 1.00 | forecast_model | True | False | 394.44 | 125.54 | 227.70 | 120.96 | 117.77 | 127.37 | 109.64 |
| 7 | 0.52 | greedy | False | False | 536.41 | 107.61 | 219.00 | 106.91 | 107.86 | 115.20 | 108.80 |
| 8 | 0.90 | forecast_model | True | False | 365.48 | 133.36 | 276.04 | 127.54 | 122.46 | 132.59 | 116.10 |
| 9 | 0.71 | greedy | False | False | 459.90 | 119.32 | 329.93 | 118.56 | 128.31 | 127.08 | 118.13 |
| 10 | 1.00 | forecast_model | True | False | 407.45 | 124.48 | 170.16 | 119.30 | 116.33 | 127.28 | 110.54 |
| 11 | 1.00 | forecast_model | True | False | 454.35 | 140.62 | 258.80 | 139.29 | 138.27 | 146.66 | 130.66 |
