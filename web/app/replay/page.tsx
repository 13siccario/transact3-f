"use client";

import { useEffect, useState } from "react";
import { HBars, type BarItem } from "@/components/HBars";
import { Nav, TopBar } from "@/components/Nav";
import { useWidth } from "@/components/useWidth";
import { API, get, type Table } from "@/lib/api";
import { POLICY_NAME, size } from "@/lib/format";

type Row = Record<string, number | string | null>;
const num = (v: unknown) => (typeof v === "number" ? v : Number(v));

const colorFor = (p: string) =>
  p.startsWith("fixed") ? "#9a9d9f" : p.startsWith("forecast") ? "#c77a12" : p === "linucb" ? "#b83f86" : p === "ppo" ? "#2a78d6" : p === "oracle" ? "#c8c9c9" : "#201f1f";
const nameFor = (p: string) => POLICY_NAME[p] ?? p.replace("fixed_", "Always ").replace("forecast_model", "Forecast-aware (model)").replace("forecast_noisy", "Forecast-aware (noisy)").replace("ppo", "PPO").replace("linucb", "Learning router").replace("greedy", "Send now").replace("oracle", "Perfect hindsight");

function useTable(paper: string, name: string) {
  const [t, setT] = useState<Table | null | "missing">(null);
  useEffect(() => { get<Table>(`/api/results/${paper}/${name}`).then((r) => setT(r.data)).catch(() => setT("missing")); }, [paper, name]);
  return t;
}

function NoiseChart({ sweep, greedy, oracle }: { sweep: Row[]; greedy?: number; oracle?: number }) {
  const [ref, width] = useWidth<HTMLDivElement>();
  const H = 250, m = { t: 26, r: 12, b: 36, l: 52 };
  const xs = sweep.map((r) => num(r.sigma)), ys = sweep.flatMap((r) => [num(r.ci_lo), num(r.ci_hi)]);
  const all = [...ys, greedy ?? NaN, oracle ?? NaN].filter((v) => !Number.isNaN(v));
  const lo = Math.min(...all) * 0.95, hi = Math.max(...all) * 1.05;
  const x = (v: number) => m.l + ((width - m.l - m.r) * (v - xs[0])) / (xs[xs.length - 1] - xs[0]);
  const y = (v: number) => m.t + (H - m.t - m.b) * (1 - (v - lo) / (hi - lo));
  const line = sweep.map((r, i) => `${i ? "L" : "M"}${x(num(r.sigma))},${y(num(r.total_bps))}`).join("");
  const band = sweep.map((r) => `${x(num(r.sigma))},${y(num(r.ci_hi))}`).join(" ") + " " + [...sweep].reverse().map((r) => `${x(num(r.sigma))},${y(num(r.ci_lo))}`).join(" ");
  return (
    <div className="chart" ref={ref}>
      <svg viewBox={`0 0 ${width} ${H}`} role="img" aria-label="Cost of forecast-aware routing as forecast noise rises, against send-now and perfect hindsight">
        <g className="axis">
          {[0, 0.5, 1].map((f) => { const v = lo + (hi - lo) * f; return <g key={f}><line x1={m.l} x2={width - m.r} y1={y(v)} y2={y(v)} stroke="var(--line)" /><text x={m.l - 8} y={y(v) + 4} textAnchor="end">{Math.round(v)}</text></g>; })}
          {sweep.map((r) => <text key={String(r.sigma)} x={x(num(r.sigma))} y={H - 14} textAnchor="middle">{num(r.sigma)}</text>)}
          <text x={(m.l + width - m.r) / 2} y={H - 0} textAnchor="middle">Forecast noise</text>
          <text x={m.l - 8} y={10} textAnchor="end">bps</text>
        </g>
        <polygon points={band} fill="#c77a12" opacity="0.15" />
        {greedy != null && <><line x1={m.l} x2={width - m.r} y1={y(greedy)} y2={y(greedy)} stroke="#201f1f" strokeDasharray="5 4" /><text x={width - m.r} y={y(greedy) - 5} textAnchor="end" fontSize="12" fill="#201f1f">Send now</text></>}
        {oracle != null && <><line x1={m.l} x2={width - m.r} y1={y(oracle)} y2={y(oracle)} stroke="#8e9294" strokeDasharray="2 4" /><text x={width - m.r} y={y(oracle) + 14} textAnchor="end" fontSize="12" fill="#66686a">Perfect hindsight</text></>}
        <path d={line} fill="none" stroke="#c77a12" strokeWidth="2" />
        {sweep.map((r) => <circle key={String(r.sigma)} cx={x(num(r.sigma))} cy={y(num(r.total_bps))} r="4" fill="#c77a12" stroke="#fff" strokeWidth="2"><title>{`noise ${num(r.sigma)}: ${num(r.total_bps).toFixed(1)} bps`}</title></circle>)}
      </svg>
    </div>
  );
}

function Playground() {
  const [cbdc, setCbdc] = useState("none");
  const [liq, setLiq] = useState(1);
  const [fc, setFc] = useState("model");
  const [noise, setNoise] = useState(0.3);
  const [rows, setRows] = useState<Row[] | null>(null);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  async function run() {
    setBusy(true); setErr(null);
    try { setRows((await get<{ rows: Row[] }>(`/api/playground?cbdc=${cbdc}&liquidity=${liq}&forecast=${fc}&noise=${noise}&episodes=500`)).data.rows); }
    catch (e) { setErr((e as Error).message); } finally { setBusy(false); }
  }
  useEffect(() => { run(); /* eslint-disable-next-line react-hooks/exhaustive-deps */ }, []);
  const sorted = rows ? [...rows].sort((a, b) => num(a.total_bps) - num(b.total_bps)) : [];
  return (
    <section className="panel" aria-labelledby="pg-h">
      <div className="panel-head"><div><h2 id="pg-h">Try the simulator</h2><p className="lede">Change the world and re-run 1,000 simulated transfers per method. Settings here are not saved.</p></div></div>
      <div className="form" style={{ marginBottom: 18 }}>
        <div className="field"><span id="c1">Central-bank digital currency bridge</span>
          <div className="segment" role="group" aria-labelledby="c1" style={{ marginTop: 0 }}>{["none", "pilot", "mature"].map((c) => <button key={c} aria-pressed={c === cbdc} onClick={() => setCbdc(c)}>{c === "none" ? "Absent" : c === "pilot" ? "Pilot" : "Mature"}</button>)}</div></div>
        <div className="field"><span id="c2">Liquidity buffers</span>
          <div className="segment" role="group" aria-labelledby="c2" style={{ marginTop: 0 }}>{[0.5, 1, 2].map((l) => <button key={l} aria-pressed={l === liq} onClick={() => setLiq(l)}>{l === 1 ? "Baseline" : `${l}×`}</button>)}</div></div>
        <div className="field"><span id="c3">Forecast quality for the forecast-aware method</span>
          <div className="segment" role="group" aria-labelledby="c3" style={{ marginTop: 0 }}>{[["none", "None"], ["model", "Model"], ["noisy", "Noisy foresight"], ["perfect", "Perfect"]].map(([k, l]) => <button key={k} aria-pressed={k === fc} onClick={() => setFc(k)}>{l}</button>)}</div></div>
        {fc === "noisy" && <label className="field"><span>Noise level: <b className="num">{noise.toFixed(1)}</b></span><input className="scrub light" type="range" min={0} max={1.6} step={0.1} value={noise} onChange={(e) => setNoise(Number(e.target.value))} /></label>}
        <div className="field submit"><button className="pill-btn dark" onClick={run} disabled={busy}>{busy ? "Running…" : "Run simulator"}</button></div>
      </div>
      {err && <p className="state error" role="alert" style={{ padding: 0 }}>{err}</p>}
      {sorted.length > 0 && <>
        <h3 className="sub-h" style={{ marginTop: 6 }}>All transfers, average all-in cost</h3>
        <HBars best={nameFor(String(sorted[0].policy))} items={sorted.map((r) => ({ label: nameFor(String(r.policy)), value: num(r.total_bps), color: colorFor(String(r.policy)) }))} />
        <h3 className="sub-h">Small transfers only (under $500)</h3>
        <HBars items={[...rows!].sort((a, b) => num(a.small_bps) - num(b.small_bps)).map((r) => ({ label: nameFor(String(r.policy)), value: num(r.small_bps), color: colorFor(String(r.policy)) }))} />
      </>}
    </section>
  );
}

export default function Replay() {
  const t6 = useTable("paper2", "table6_replay");
  const t7 = useTable("paper2", "table7_legal_status");
  const t6c = useTable("paper2", "table6c_paired");
  const t5 = useTable("paper1", "table5_main");
  const e4 = useTable("paper1", "table_e4_noise");
  const [amount, setAmount] = useState(1000);
  const missing = [t6, t7, t6c, t5, e4].some((t) => t === "missing");
  const loading = [t6, t7, t6c, t5, e4].some((t) => t === null);
  const tb = (t: Table | null | "missing") => (t && t !== "missing" ? t.rows : []);

  const replay = tb(t6).filter((r) => num(r.amount) === amount).sort((a, b) => num(a.total_bps) - num(b.total_bps));
  const paired = tb(t6c).filter((r) => r.comparison === "forecast_aware - greedy" && r.scenario === "p2_excluded");
  const maxGain = paired.length ? Math.min(...paired.map((r) => num(r.diff_bps))) : 0;
  const maxLoss = paired.length ? Math.max(...paired.map((r) => num(r.diff_bps))) : 0;
  const main = tb(t5);
  const sweep = tb(e4);
  const greedy = main.find((r) => r.policy === "greedy"), oracle = main.find((r) => r.policy === "oracle");
  const legal = tb(t7);
  const scenarios = [...new Set(legal.map((r) => String(r.scenario)))];

  return (
    <main className="shell">
      <TopBar synthetic />
      <section className="hero" style={{ gridTemplateColumns: "minmax(0, 1fr)" }} aria-labelledby="rh">
        <div>
          <h1 id="rh" className="headline" style={{ maxWidth: "15ch" }}>
            Does knowing
            <b>the future</b>
            lower the bill
          </h1>
          <p className="hero-sub">Routing methods compared two ways: on the recorded cost history, and in a simulated multi-rail market. Every method acts only on eligible paths.</p>
        </div>
      </section>

      {loading && !missing && <p className="state">Loading results…</p>}
      {missing && <p className="state error" role="alert">Some result tables are missing. Run <code>make reproduce</code>, then restart the API ({API}).</p>}

      {replay.length > 0 && (
        <section className="panel mint" aria-labelledby="r1">
          <div className="panel-head">
            <div><h2 id="r1">Replay of recorded costs</h2><p className="lede">Average all-in cost for a transfer arriving every hour, with the default rules (onshore exchange not allowed). Averaged over 6, 24 and 72 hour deadlines.</p></div>
            <div className="tabs" role="group" aria-label="Transfer size">{[200, 1000, 10000].map((a) => <button key={a} aria-pressed={a === amount} onClick={() => setAmount(a)}>{size(a)}</button>)}</div>
          </div>
          <HBars best="Perfect hindsight" items={replay.map((r) => ({ label: nameFor(String(r.policy)), value: num(r.total_bps), color: colorFor(String(r.policy)), note: num(r.wait_h) > 0 ? `waits ${num(r.wait_h).toFixed(1)}h` : undefined }))} />
          <p className="note" style={{ color: "#3d4a3e" }}>
            Forecast-aware differs from send-now by between {maxGain.toFixed(1)} and +{maxLoss.toFixed(1)} bps across sizes and deadlines. Perfect hindsight saves far more by waiting, so there is room to gain, but a one-hour forecast cannot find it.
          </p>
        </section>
      )}

      {legal.length > 0 && (
        <section className="panel" aria-labelledby="r2">
          <div className="panel-head"><div><h2 id="r2">If the rules about onshore exchanges change</h2><p className="lede">Average cost across all sizes under three assumptions about whether the onshore exchange path may be used. These are research scenarios, not legal conclusions.</p></div></div>
          <div className="scroll-x"><table className="plain-t num">
            <thead><tr><th>Method</th>{scenarios.map((s) => <th key={s}>{s === "p2_excluded" ? "Not allowed" : s === "p2_included_with_cost" ? "Allowed, extra cost" : "Allowed"}</th>)}</tr></thead>
            <tbody>{["greedy", "forecast_aware", "linucb", "oracle"].map((p) => (
              <tr key={p}><td>{nameFor(p)}</td>{scenarios.map((s) => { const r = legal.find((x) => x.policy === p && x.scenario === s); return <td key={s}>{r ? `${num(r.total_bps).toFixed(0)} bps` : ""}</td>; })}</tr>
            ))}</tbody>
          </table></div>
        </section>
      )}

      {main.length > 0 && (
        <section className="panel" aria-labelledby="r3">
          <div className="panel-head"><div><h2 id="r3">Simulated multi-rail market</h2><p className="lede">Average all-in cost over independent simulated worlds. Whiskers show the 95% interval across worlds. Failures and late arrivals are charged as extra cost.</p></div></div>
          <HBars best={nameFor(String(main.filter((r) => r.policy !== "oracle")[0]?.policy))} items={main.map((r) => ({ label: nameFor(String(r.policy)), value: num(r.total_bps), lo: num(r.ci_lo), hi: num(r.ci_hi), color: colorFor(String(r.policy)) }))} />
          <p className="note">Perfect hindsight sees the market path but plans one transfer at a time, so it is not a global optimum when liquidity is scarce.</p>
        </section>
      )}

      {sweep.length > 0 && (
        <section className="panel" aria-labelledby="r4">
          <div className="panel-head"><div><h2 id="r4">How accurate must a forecast be?</h2><p className="lede">Cost of the forecast-aware method as its forecast gets noisier, against sending now and perfect hindsight.</p></div></div>
          <NoiseChart sweep={sweep} greedy={greedy ? num(greedy.total_bps) : undefined} oracle={oracle ? num(oracle.total_bps) : undefined} />
        </section>
      )}

      <Playground />
      <footer className="footer"><span>Research findings, not legal or financial advice. All figures come from synthetic data and provisional parameters.</span></footer>
      <Nav />
    </main>
  );
}
