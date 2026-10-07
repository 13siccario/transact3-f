"use client";

import { useEffect, useState } from "react";
import { Nav, TopBar } from "@/components/Nav";
import { Player } from "@/components/Player";
import { API, get, type Envelope, type SimMeta, type SimResult } from "@/lib/api";
import { PATH_NAME, POLICY_NAME, usd } from "@/lib/format";

const DEADLINES = [6, 24, 72];
const INTERVALS = [{ h: 6, label: "Every 6 hours" }, { h: 24, label: "Daily" }, { h: 72, label: "Every 3 days" }, { h: 168, label: "Weekly" }];

export default function Simulate() {
  const [meta, setMeta] = useState<Envelope<SimMeta> | null>(null);
  const [amount, setAmount] = useState("1000");
  const [deadline, setDeadline] = useState(24);
  const [count, setCount] = useState(5);
  const [interval, setIntervalH] = useState(24);
  const [pos, setPos] = useState(0.5);
  const [scenario, setScenario] = useState<string>("");
  const [sim, setSim] = useState<Envelope<SimResult> | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => { get<SimMeta>("/api/simulate/meta").then((m) => { setMeta(m); setScenario(m.data.default_scenario); }).catch((e) => setError(e.message)); }, []);

  if (error && !meta) return <main className="shell"><p className="state error" role="alert">Could not load the simulator: {error}. Start the API with <code>make api</code> (expects {API}).</p></main>;
  if (!meta) return <main className="shell"><p className="state">Loading…</p></main>;

  const m = meta.data;
  const t0 = new Date(m.start).getTime(), t1 = new Date(m.end).getTime();
  const startTs = new Date(t0 + pos * (t1 - t0)).toISOString();
  const amt = Number(amount);
  const amtOk = Number.isFinite(amt) && amt >= 50 && amt <= 100000;
  const synthetic = meta.source_kind === "synthetic";

  async function run() {
    setBusy(true); setError(null);
    try {
      const q = new URLSearchParams({ amount: String(amt), deadline_h: String(deadline), count: String(count), interval_h: String(interval), start_ts: startTs, scenario });
      setSim(await get<SimResult>(`/api/simulate?${q}`));
    } catch (e) { setError((e as Error).message); setSim(null); } finally { setBusy(false); }
  }

  return (
    <main className="shell">
      <TopBar synthetic={synthetic} />
      <section className="hero" style={{ gridTemplateColumns: "minmax(0, 1fr)" }} aria-labelledby="sh">
        <div>
          <h1 id="sh" className="headline" style={{ maxWidth: "14ch" }}>
            Send it,
            <b>then watch</b>
            what happens
          </h1>
          <p className="hero-sub">
            Describe a transfer, press run, and see how four routing methods handle it hour by hour: when they send, which path they pick, what it costs, and how that compares with the price you were quoted at the start.
          </p>
        </div>
      </section>

      <section className="panel" aria-labelledby="form-h">
        <div className="panel-head"><div><h2 id="form-h">Your transfer</h2><p className="lede">Prices replay the observed hourly history, so every method sees only what was known at that hour.</p></div></div>
        <form className="form" onSubmit={(e) => { e.preventDefault(); if (amtOk) run(); }}>
          <label className="field">
            <span>Amount (USD)</span>
            <input className="pick num" inputMode="decimal" value={amount} onChange={(e) => setAmount(e.target.value)} aria-invalid={!amtOk} aria-describedby="amt-help" />
            <small id="amt-help" className={amtOk ? "" : "bad"}>{amtOk ? "Between $50 and $100,000" : "Enter an amount between $50 and $100,000"}</small>
          </label>
          <div className="field">
            <span id="dl">Must arrive within</span>
            <div className="segment" role="group" aria-labelledby="dl" style={{ marginTop: 0 }}>
              {DEADLINES.map((d) => <button type="button" key={d} aria-pressed={d === deadline} onClick={() => setDeadline(d)}>{d} hours</button>)}
            </div>
          </div>
          <div className="field">
            <span id="cnt">Number of transfers</span>
            <div className="stepper" role="group" aria-labelledby="cnt">
              <button type="button" aria-label="Fewer transfers" onClick={() => setCount((c) => Math.max(1, c - 1))}>−</button>
              <b className="num">{count}</b>
              <button type="button" aria-label="More transfers" onClick={() => setCount((c) => Math.min(30, c + 1))}>+</button>
            </div>
          </div>
          <div className="field">
            <span>How often</span>
            <select className="pick" value={interval} disabled={count === 1} onChange={(e) => setIntervalH(Number(e.target.value))}>
              {INTERVALS.map((i) => <option key={i.h} value={i.h}>{i.label}</option>)}
            </select>
          </div>
          <label className="field wide">
            <span>Start in the history: <b className="num">{new Date(startTs).toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric", timeZone: "UTC" })}</b></span>
            <input className="scrub light" type="range" min={0} max={1} step={0.01} value={pos} onChange={(e) => setPos(Number(e.target.value))} aria-label="Start date" />
          </label>
          <label className="field">
            <span>Paths allowed</span>
            <select className="pick" value={scenario} onChange={(e) => setScenario(e.target.value)}>
              {Object.entries(m.scenarios).map(([s, paths]) => <option key={s} value={s}>{paths.map((p) => PATH_NAME[p]).join(" + ")}{s === m.default_scenario ? " (default)" : ""}</option>)}
            </select>
            <small>A rules file decides this, and no method can override it.</small>
          </label>
          <div className="field submit">
            <button className="pill-btn dark" type="submit" disabled={!amtOk || busy}>{busy ? "Running…" : "Run simulation"}</button>
            <small>{usd(amt || 0, 0)} × {count} = {usd((amt || 0) * count, 0)} in total</small>
          </div>
        </form>
        {error && <p className="state error" role="alert" style={{ padding: "12px 0 0" }}>{error}</p>}
      </section>

      {sim && <Player sim={sim.data} />}
      {!sim && !error && <p className="note" style={{ textAlign: "center" }}>Nothing has been simulated yet. Set up a transfer above and press Run simulation.</p>}

      <details className="panel table-view" style={{ marginTop: 20 }}>
        <summary style={{ fontWeight: 500 }}>What the four methods are</summary>
        <ul className="plain">
          {Object.entries(m.policies).map(([k, v]) => <li key={k}><b>{POLICY_NAME[k]}.</b> {v}.</li>)}
        </ul>
      </details>

      <footer className="footer">
        <span>{meta.disclaimer} Fees and settlement times are provisional placeholders.</span>
        <span className="num">Data: {meta.source_kind} · rules v{m.rules_version}{m.rules_reviewed ? "" : " (not yet reviewed by a person)"} · config {meta.config_hash}</span>
      </footer>
      <Nav />
    </main>
  );
}
