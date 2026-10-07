"use client";

import { useEffect, useState } from "react";
import { Anatomy } from "@/components/Anatomy";
import { PathCards } from "@/components/PathCards";
import { SizeChart } from "@/components/SizeChart";
import { Timeline } from "@/components/Timeline";
import { Curl } from "@/components/Star";
import { Nav, TopBar } from "@/components/Nav";
import { API, get, type Envelope, type Meta, type Row, type Timeline as TimelineData } from "@/lib/api";
import { size } from "@/lib/format";

export default function Page() {
  const [meta, setMeta] = useState<Envelope<Meta> | null>(null);
  const [amount, setAmount] = useState(1000);
  const [regime, setRegime] = useState("all");
  const [rows, setRows] = useState<Row[] | null>(null);
  const [tlPath, setTlPath] = useState("P1");
  const [timeline, setTimeline] = useState<TimelineData | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    get<Meta>("/api/meta").then(setMeta).catch((e) => setError(e.message));
  }, []);
  useEffect(() => {
    get<Row[]>(`/api/costs/anatomy?regime=${regime}`).then((r) => setRows(r.data)).catch((e) => setError(e.message));
  }, [regime]);
  useEffect(() => {
    get<TimelineData>(`/api/costs/timeline?path=${tlPath}&amount=${amount}`).then((r) => setTimeline(r.data)).catch((e) => setError(e.message));
  }, [tlPath, amount]);

  if (error) {
    return (
      <main className="shell">
        <p className="state error" role="alert">
          Could not load data: {error}. Start the API with <code>make api</code> (expects {API}).
        </p>
      </main>
    );
  }
  if (!meta || !rows || !timeline) return <main className="shell"><p className="state">Loading cost data…</p></main>;

  const sel = rows.filter((r) => r.amount === amount);
  const synthetic = meta.source_kind === "synthetic";

  return (
    <main className="shell">
      <TopBar synthetic={synthetic} />

      <section className="hero" aria-labelledby="hero-h">
        <div>
          <h1 id="hero-h" className="headline">
            What it costs
            <b>to send {size(amount)}</b>
            to India
          </h1>
          <p className="hero-sub">
            Three ways to move money, with every charge itemised. Pick a transfer size and a market period to compare them.
          </p>
          <Curl className="curl" />
          <div className="control-row">
            <div className="segment" role="group" aria-label="Transfer size">
              {meta.data.sizes.map((s) => (
                <button key={s} aria-pressed={s === amount} onClick={() => setAmount(s)}>{size(s)}</button>
              ))}
            </div>
            <div className="segment" role="group" aria-label="Market period">
              {["all", ...meta.data.regimes].filter((v, i, a) => a.indexOf(v) === i).map((r) => (
                <button key={r} aria-pressed={r === regime} onClick={() => setRegime(r)}>
                  {r === "all" ? "Whole period" : r === "stress" ? "Stress days" : "Normal days"}
                </button>
              ))}
            </div>
          </div>
        </div>
        <div>
          <PathCards rows={sel} />
          <p className="note">
            Provisional ranking: regulatory charges are set to zero and fee levels are placeholders until each is sourced from a primary document.
          </p>
        </div>
      </section>

      <Anatomy key={amount} rows={sel} meta={meta.data} />
      <SizeChart rows={rows} meta={meta.data} />
      <Timeline data={timeline} meta={meta.data} path={tlPath} amount={amount} onPath={setTlPath} />

      <footer className="footer">
        <span>{meta.disclaimer} Fee and tax parameters are {meta.cost_params} until calibrated from primary sources.</span>
        <span className="num">Data: {meta.source_kind} · {meta.data.start.slice(0, 10)} to {meta.data.end.slice(0, 10)} · config {meta.config_hash}</span>
      </footer>

      <Nav />
    </main>
  );
}
