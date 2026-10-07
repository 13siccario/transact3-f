# transact3: user journey

This guide shows how a person uses transact3, from opening it for the first time to trusting (or not trusting) what it tells them. It follows the order the app is built for. Each step says what you do, what you see, and what it means.

> **Read this first.** transact3 is research software. Every number you see today comes from **synthetic data and placeholder fees**, and the app says so on every page. Results are research findings, not legal or financial advice, and the app is not a tool for moving money or for getting around exchange controls.

---

## Who this is for

| You are | You want to | Start at |
|---|---|---|
| An analyst or researcher studying how money gets into India | See what each route costs and why | Step 1, Costs |
| Someone curious how smart routing could help | Compare routing methods fairly | Step 3, Replay |
| Someone who wants to feel it working | Run your own transfers and watch them | Step 4, Simulate |
| A developer or co-author | Reproduce every table and figure | Step 6, Reproduce |

---

## Before you start

```
make setup           # one time: Python environment
make data forecast   # build datasets and forecasts (about a minute)
make api             # backend, http://localhost:8000
make web             # frontend, http://localhost:3000   (run `npm install` in web/ once)
```

Open <http://localhost:3000>. A mint chip at the top right reads **Synthetic data, not observations**. That chip stays until real data replaces the synthetic data.

The four sections are in the floating bar at the bottom of every page: **Costs, Forecasts, Replay, Simulate**.

---

## Step 1. Costs: what does it cost to send money into India?

**You do.** Land on the Costs page. Pick a transfer size ($200, $1,000 or $10,000) and a market period (whole period, normal days, stress days).

**You see.**
- Three cards, one per way of sending: **Conventional**, **Compliant stablecoin** and **Onshore exchange**. The cheapest has a dark card and a *Lowest cost* tag. Each shows the all-in cost in basis points (100 bps = 1%) and in dollars.
- **Where the cost comes from**: every charge as its own row (bank or exchange fees, exchange-rate margin, network fee, pool fee, price impact, stablecoin off-peg, regulatory charges), with a bar so you can see which charge dominates. Switch paths with the tabs.
- **Small transfers pay the most**: the same costs across all three sizes. Fixed fees and network fees do not shrink with the amount, so a $200 transfer pays a far bigger share than a $10,000 one.
- **Cost over time**: daily cost for the chosen path, with stress days shaded. Hover to read any day. Every chart has a *View as table* link.

**What it means.**
- The **local price premium** sits on its own dashed line and is **never counted** in the totals. It is measured because it is part of the picture, but it is not a free gain and is not used to rank routes.
- The note under the cards says the ranking is **provisional**: regulatory charges are set to zero and fee levels are placeholders until each is taken from a primary source. Do not quote these numbers.

---

## Step 2. Forecasts: which costs can be predicted?

**You do.** Open Forecasts. Choose *Whole period*, *Normal days* or *Stress days*.

**You see.**
- A table with a row for each cost driver (exchange-rate return, volatility, spread, network fee, peg gap, local premium, pool price impact) and a column for each model. Each cell is a score: the share of a random walk's squared error that the model removes, on hours it never saw.
- **Mint** cells beat the random walk with statistical confidence, **pink** cells are worse, **grey** cells are not clearly different. The words *better*, *worse* and *no clear gap* are printed in every cell, so colour is never the only signal.
- **Forecast against actual**: pick a driver and a model to see the last seven days of predictions against what happened.
- **What the routers receive**: the forecast values the routing methods are handed at the latest hour, and nothing from later hours.

**What it means.** On synthetic data, volatility and some fees can be forecast and exchange-rate returns cannot. That is built into the synthetic world, so treat it as proof the pipeline works, not as a finding about real markets.

---

## Step 3. Replay: does knowing the future lower the bill?

**You do.** Open Replay and scroll. Change the transfer size above the first chart. At the bottom, change the settings in **Try the simulator** and press *Run simulator*.

**You see.**
- **Replay of recorded costs**: four routing methods run over the recorded cost history, only using paths the compliance rules allow. Bars show average cost per method.
  - *Send now* picks the cheapest allowed path right away.
  - *Forecast-aware* may wait an hour if the forecast says it will be cheaper.
  - *Learning router* learns from past results which path tends to be cheapest.
  - *Perfect hindsight* knows the whole future. It cannot be achieved and is there to show how much is left on the table.
- **If the rules about onshore exchanges change**: the same comparison when that path is not allowed, allowed at an extra cost, or allowed. These are research scenarios, not legal conclusions.
- **Simulated multi-rail market**: the same methods in a larger simulated market with four rails (correspondent banking, linked instant rails, stablecoin, and a central-bank-digital-currency bridge) and limited liquidity. Whiskers are 95% intervals across independent simulated worlds.
- **How accurate must a forecast be?** Cost as the forecast gets noisier.
- **Try the simulator**: change the central-bank-digital-currency bridge (absent, pilot, mature), liquidity buffers, and forecast quality, then re-run.

**What it means.** The honest headline from the current runs is modest: knowing the future helps only a little, and a one-hour forecast does not capture most of that help. Sending now is close to as good as the smarter methods. The app reports this plainly rather than hunting for a win.

---

## Step 4. Simulate: send your own transfer and watch it

This is the part to try by hand.

**You do.**
1. Enter an **amount** (50 to 100,000 dollars).
2. Pick **Must arrive within** 6, 24 or 72 hours.
3. Choose the **number of transfers** and **how often** they arrive. One transfer is a single send; several shows how a method behaves over time.
4. Slide **Start in the history** to pick a point in the recorded period.
5. Choose **Paths allowed**. The default is the cautious setting. A rules file decides this and no method can override it.
6. Press **Run simulation**.

**You see.** A dark playback panel:
- A clock showing simulated time, with **Play / Pause**, three speeds (Slow, Medium, Fast), **Skip to end** and a draggable time bar. Playback starts paused so nothing happens until you press Play.
- **What each path costs, hour by hour**: one line per path with the current cost for each. Paths the rules do not allow are dashed and labelled *not eligible*.
- **Each transfer, from arrival to settlement**: one lane per method. A triangle marks arrival, a pale bar shows waiting, a coloured dot shows the moment of sending and the path chosen, and a tick shows settlement (pink-red if late).
- **Cost paid so far**: running dollars per method.
- **Activity**: a plain-language feed such as *Transfer 2 waits an hour (forecast 231 bps next hour vs 237 now)* or *Transfer 3 sent via Compliant stablecoin at 224 bps*. Switch which method's feed you read.
- **Final results**, shown when playback ends: total paid, average cost, how much each method saved against the price you were quoted at arrival, how far it finished behind perfect hindsight, average wait and late arrivals. The lowest real method is marked. Perfect hindsight is excluded from that mark because it cannot be used.

**What it means.**
- *Saved vs. quote* answers "was it worth waiting or being clever?". Zero means no better than sending immediately.
- Nothing in the playback looks ahead. At each hour a method uses only what was known then. The learning router is trained on the 400 hours before your start date, not on your transfers.
- If your schedule is longer than the recorded history allows, the app tells you to use fewer transfers or a shorter interval instead of running a partial result.

---

## Step 5. Know the limits

| What you might wonder | Answer |
|---|---|
| Are these real prices? | No. They are synthetic until real sources are approved. The chip and the footer say so. |
| Are the fees right? | No. Every fee, delay and tax value is a labelled placeholder until it is taken from a primary source. |
| Can I move money with this? | No. It never sends money. It is a measurement and comparison tool. |
| Why is the onshore exchange path off by default? | The rules file is deliberately cautious, and a person has not yet reviewed it. Real-data runs are refused until someone does. |
| Why does "perfect hindsight" sometimes cost more than "send now" in the simulator? | It sees the market path but plans one transfer at a time, so it can spend a liquidity buffer that a later transfer needed. |
| Will the forecast-aware method always win? | No. If it does not beat sending now, the app shows that. |

When something goes wrong the app says what happened and what to do, for example: *Could not load data. Start the API with `make api`.*

---

## Step 6. Reproduce (for researchers and developers)

```
make test        # unit tests, including the compliance filter and no-lookahead checks
make reproduce   # data, forecasts, Paper 1 and Paper 2 tables and figures, feasibility report (about 40 minutes)
```

Where things land:

| Output | Location |
|---|---|
| Datasets and forecasts | `data/processed/` |
| Paper 1 tables and Figure 2 | `paper1/tables/`, `paper1/figures/` |
| Paper 2 tables and figure | `paper2/tables/`, `paper2/figures/` |
| Data feasibility report | `docs/data_feasibility_report.md` |
| What is left before release | `docs/release_checklist.md` |

Every experiment is one YAML file in `configs/` with a seed, and every result is saved with the config's hash, so any number can be traced to the exact settings that made it.

---

## A ten-minute walkthrough

1. **Costs.** Select $200, then $10,000. Notice how the winner and the gap change.
2. **Costs.** Select *Stress days*. Which path's cost rises most?
3. **Forecasts.** Find the row where a model is mint. Open *Forecast against actual* for that driver.
4. **Replay.** Read the note under *Replay of recorded costs*. How big is the gap between forecast-aware and send-now?
5. **Replay.** In *Try the simulator*, choose *Perfect* forecast quality and run it, then *Noisy foresight* at 0.8. How fast does the benefit fade?
6. **Simulate.** Run $1,000, 24 hours, 5 transfers, daily. Press Play on Medium and watch the *Activity* feed.
7. **Simulate.** Run it again with *Paths allowed* set to include the onshore exchange. What changes, and what does that say about depending on a rule you cannot control?
8. Read the **Final results**, then reread Step 5.

---

## Glossary

| Term | Meaning |
|---|---|
| bps (basis points) | One hundredth of a percent. 100 bps = 1%. |
| All-in cost | Every charge together, in bps or dollars. Excludes the local premium. |
| Local price premium | How far the local stablecoin price sits from the reference exchange rate. Reported, never counted as a gain. |
| Peg gap | How far a stablecoin trades from one dollar. |
| Compliance filter | The code that removes disallowed paths before any method chooses. It cannot be overridden. |
| Settlement | When the money arrives. A transfer is *late* if that is after your deadline. |
| Stress days | Days flagged as unusually volatile or disrupted. |
| Perfect hindsight | A method that knows the future. A yardstick, not a real option. |
