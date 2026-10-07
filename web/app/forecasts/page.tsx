"use client";

import { useEffect, useState } from "react";
import { ForecastChart } from "@/components/ForecastChart";
import { Nav, TopBar } from "@/components/Nav";
import { API, get, type Envelope } from "@/lib/api";

type SRow = { target: string; target_name: string; model: string; n: number; rmse: number; mae: number; skill: number | null; dm_stat: number | null; dm_p: number | null };
type Summary = { meta: { benchmark: string; horizon: number; folds: number; z_model: string; targets: Record<string, string>; models: string[]; regimes: string[]; origins: string[] }; rows: SRow[] };
type Z = { origin_ts: string; model: string; items: { target: string; name: string; value: number }[] };

const MODEL_NAMES: Record<string, string> = {
  random_walk: "Random walk", rolling_median: "Rolling median", ar: "AR(3)", garch: "GARCH(1,1)", lightgbm: "LightGBM", lstm: "LSTM",
};
const ORDER = ["random_walk", "rolling_median", "ar", "garch", "lightgbm", "lstm"];

function fmtZ(t: string, v: number) {
  if (["fx_return", "fx_vol", "peg_dev"].includes(t)) return `${(v * 1e4).toFixed(2)} bps`;
  if (t === "fx_spread" || t === "slip_bps") return `${v.toFixed(3)} bps`;
  if (t === "gas_gwei") return `${v.toFixed(1)} gwei`;
  return `${v.toFixed(2)}%`;
}

export default function Forecasts() {
  const [regime, setRegime] = useState("all");
  const [sum, setSum] = useState<Envelope<Summary> | null>(null);
  const [z, setZ] = useState<Envelope<Z> | null>(null);
  const [target, setTarget] = useState("fx_vol");
  const [model, setModel] = useState("lightgbm");
  const [error, setError] = useState<string | null>(null);

  useEffect(() => { get<Summary>(`/api/forecast/summary?regime=${regime}`).then(setSum).catch((e) => setError(e.message)); }, [regime]);
  useEffect(() => { get<Z>("/api/forecast/z").then(setZ).catch((e) => setError(e.message)); }, []);

  if (error) {
    return <main className="shell"><p className="state error" role="alert">Could not load forecasts: {error}. Start the API with <code>make api</code> (expects {API}) after running <code>make forecast</code>.</p></main>;
  }
  if (!sum || !z) return <main className="shell"><p className="state">Loading forecasts…</p></main>;

  const { meta, rows } = sum.data;
  const models = ORDER.filter((m) => meta.models.includes(m));
  const targets = Object.keys(meta.targets);
  const cell = (t: string, m: string) => rows.find((r) => r.target === t && r.model === m);
  const synthetic = sum.source_kind === "synthetic";

  return (
    <main className="shell">
      <TopBar synthetic={synthetic} />

      <section className="hero" style={{ gridTemplateColumns: "minmax(0, 1fr)" }} aria-labelledby="fh">
        <div>
          <h1 id="fh" className="headline" style={{ maxWidth: "16ch" }}>
            Which costs
            <b>can be forecast</b>
            one hour ahead
          </h1>
          <p className="hero-sub">
            Each model is scored against a {MODEL_NAMES[meta.benchmark].toLowerCase()} on hours it never saw, refitted weekly.
            A positive score means a lower squared error than the benchmark.
          </p>
          <div className="segment" role="group" aria-label="Market period">
            {meta.regimes.map((r) => (
              <button key={r} aria-pressed={r === regime} onClick={() => setRegime(r)}>
                {r === "all" ? "Whole period" : r === "stress" ? "Stress days" : "Normal days"}
              </button>
            ))}
          </div>
        </div>
      </section>

      <section className="panel mint" aria-labelledby="skill-h">
        <div className="panel-head">
          <div>
            <h2 id="skill-h">Forecast skill against the benchmark</h2>
            <p className="lede">Score is the share of the benchmark&apos;s squared error removed. Shaded cells differ from the benchmark at the 5% level (Diebold-Mariano).</p>
          </div>
        </div>
        <div className="scroll-x cards">
          <table className="skill num">
            <thead>
              <tr><th>Cost driver</th>{models.map((m) => <th key={m}>{MODEL_NAMES[m]}</th>)}</tr>
            </thead>
            <tbody>
              {targets.map((t) => (
                <tr key={t}>
                  <th scope="row" className="row-head">{meta.targets[t]}</th>
                  {models.map((m) => {
                    const c = cell(t, m);
                    if (!c) return <td key={m} data-label={MODEL_NAMES[m]}><span className="cell" aria-label="not applicable">–</span></td>;
                    if (m === meta.benchmark) return <td key={m} data-label={MODEL_NAMES[m]}><span className="cell">Benchmark</span></td>;
                    const sig = c.dm_p !== null && c.dm_p < 0.05;
                    const sk = c.skill ?? 0;
                    const cls = sig ? (sk > 0 ? "better" : "worse") : "";
                    const verdict = sig ? (sk > 0 ? "beats benchmark" : "worse than benchmark") : "no clear difference";
                    return (
                      <td key={m} data-label={MODEL_NAMES[m]}>
                        <span className={`cell ${cls}`} aria-label={`${MODEL_NAMES[m]} on ${meta.targets[t]}: ${(sk * 100).toFixed(1)} percent, ${verdict}`}>
                          {sk > 0 ? "+" : sk < 0 ? "−" : ""}{Math.abs(sk * 100).toFixed(1)}%
                          <small>{sig ? (sk > 0 ? "better" : "worse") : "no clear gap"}</small>
                        </span>
                      </td>
                    );
                  })}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <div className="key">
          <span><i style={{ background: "var(--mint)" }} />Beats the benchmark</span>
          <span><i style={{ background: "#f4d9d4" }} />Worse than the benchmark</span>
          <span><i style={{ background: "var(--page)" }} />No clear difference</span>
          <span>– GARCH applies only to USD/INR return and volatility</span>
        </div>
        <p className="note" style={{ color: "#3d4a3e" }}>
          {meta.folds} weekly refits, forecasts from {meta.origins[0].slice(0, 10)} to {meta.origins[1].slice(0, 10)}.
          {synthetic && " The data is synthetic, so these scores show the pipeline works, not what the real market does."}
        </p>
      </section>

      <section className="panel" aria-labelledby="chart-h">
        <div className="panel-head">
          <div>
            <h2 id="chart-h">Forecast against actual</h2>
            <p className="lede">The last seven days of the test period, one point per hour.</p>
          </div>
          <div className="control-row" style={{ gap: 8 }}>
            <label className="sr-only" htmlFor="tsel" style={{ position: "absolute", left: -9999 }}>Cost driver</label>
            <select id="tsel" className="pick" value={target} onChange={(e) => setTarget(e.target.value)}>
              {targets.map((t) => <option key={t} value={t}>{meta.targets[t]}</option>)}
            </select>
            <label htmlFor="msel" style={{ position: "absolute", left: -9999 }}>Model</label>
            <select id="msel" className="pick" value={model} onChange={(e) => setModel(e.target.value)}>
              {models.filter((m) => m !== meta.benchmark).map((m) => <option key={m} value={m}>{MODEL_NAMES[m]}</option>)}
            </select>
          </div>
        </div>
        <ForecastChart target={target} targetName={meta.targets[target]} model={model} modelName={MODEL_NAMES[model]} benchName={MODEL_NAMES[meta.benchmark]} />
      </section>

      <section className="z-card" aria-labelledby="z-h">
        <h2 id="z-h">What the routers receive</h2>
        <p className="lede">
          The forecast vector z(t) at the latest origin ({z.data.origin_ts.slice(0, 16).replace("T", " ")} UTC), from {MODEL_NAMES[z.data.model]}.
          Routers see these values and nothing from later hours.
        </p>
        <ul className="z-list">
          {z.data.items.map((i) => (
            <li key={i.target}><span>{i.name}</span><span className="num">{fmtZ(i.target, i.value)}</span></li>
          ))}
        </ul>
      </section>

      <footer className="footer">
        <span>{sum.disclaimer}</span>
        <span className="num">Data: {sum.source_kind} · horizon {meta.horizon} hour · config {sum.config_hash}</span>
      </footer>
      <Nav />
    </main>
  );
}
