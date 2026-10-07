"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import type { SimResult } from "@/lib/api";
import { PATH_NAME, POLICY_NAME, usd } from "@/lib/format";
import { useWidth } from "./useWidth";

const SPEEDS = [{ label: "Slow", hps: 2 }, { label: "Medium", hps: 8 }, { label: "Fast", hps: 24 }];

function stamp(startTs: string, hours: number) {
  const d = new Date(new Date(startTs).getTime() + hours * 3600_000);
  return d.toLocaleString("en-US", { month: "short", day: "numeric", hour: "2-digit", minute: "2-digit", hour12: false, timeZone: "UTC" }) + " UTC";
}

export function Player({ sim }: { sim: SimResult }) {
  const n = sim.market.length - 1;
  const [cursor, setCursor] = useState(0);
  const [playing, setPlaying] = useState(false);
  const [speed, setSpeed] = useState(1);
  const [focus, setFocus] = useState<string>(Object.keys(sim.policies)[0]);
  const raf = useRef<number | null>(null);
  const last = useRef<number>(0);
  const [wrap, width] = useWidth<HTMLDivElement>();
  const policies = Object.keys(sim.policies);
  const reduced = typeof window !== "undefined" && window.matchMedia?.("(prefers-reduced-motion: reduce)").matches;

  useEffect(() => { setCursor(0); setPlaying(false); setFocus(Object.keys(sim.policies)[0]); }, [sim]);

  useEffect(() => {
    if (!playing) return;
    last.current = performance.now();
    const tick = (t: number) => {
      const dt = (t - last.current) / 1000;
      last.current = t;
      setCursor((c) => {
        const next = Math.min(n, c + dt * SPEEDS[speed].hps);
        if (next >= n) setPlaying(false);
        return next;
      });
      raf.current = requestAnimationFrame(tick);
    };
    raf.current = requestAnimationFrame(tick);
    return () => { if (raf.current) cancelAnimationFrame(raf.current); };
  }, [playing, speed, n]);

  const now = Math.floor(cursor);
  const finished = cursor >= n;

  // ---- derived state at the cursor -----------------------------------------------------------
  const cum = useMemo(() => Object.fromEntries(policies.map((p) => {
    const arr = new Array(n + 1).fill(0);
    sim.policies[p].transfers.forEach((t) => { for (let h = Math.max(0, t.send_i); h <= n; h++) arr[h] += t.total_usd; });
    return [p, arr as number[]];
  })), [sim, n]);   // eslint-disable-line react-hooks/exhaustive-deps

  const status = (p: string) => {
    const ts = sim.policies[p].transfers;
    const waiting = ts.filter((t) => t.arrive_i <= now && now < t.send_i).length;
    const transit = ts.filter((t) => t.send_i <= now && now < t.settle_i).length;
    const done = ts.filter((t) => t.settle_i <= now).length;
    return { waiting, transit, done, spent: cum[p][Math.min(now, n)] };
  };

  const best = useMemo(() => {
    const real = policies.filter((p) => p !== "oracle");
    return real.reduce((a, b) => (sim.policies[a].summary.total_usd <= sim.policies[b].summary.total_usd ? a : b));
  }, [sim]);   // eslint-disable-line react-hooks/exhaustive-deps

  // ---- geometry ------------------------------------------------------------------------------
  const m = { l: 56, r: 16 };
  const x = (i: number) => m.l + ((width - m.l - m.r) * i) / n;
  const maxBps = Math.max(...sim.market.flatMap((r) => sim.eligible_paths.map((p) => r.cost_bps[p])));
  const MH = 170;
  const my = (v: number) => 12 + (MH - 36) * (1 - v / (maxBps * 1.08));
  const pathsAll = Object.keys(sim.market[0].cost_bps);
  const lane = 34;
  const LH = policies.length * lane + 30;
  const maxUsd = Math.max(...policies.map((p) => cum[p][n]), 0.01);
  const CH = 150;
  const cy = (v: number) => 10 + (CH - 34) * (1 - v / (maxUsd * 1.08));

  const events = sim.policies[focus].events.filter((e) => e.i <= now).slice(-7).reverse();
  const evText = (e: SimResult["policies"][string]["events"][number]) => {
    const t = sim.policies[focus].transfers[e.transfer];
    if (e.type === "arrive") return { icon: "↓", text: `Transfer ${e.transfer + 1} arrives`, sub: `Quote ${Math.round(t.quote_bps)} bps if sent now` };
    if (e.type === "wait") return { icon: "…", text: `Transfer ${e.transfer + 1} waits an hour`, sub: `Forecast ${Math.round(e.forecast_next_bps ?? 0)} bps next hour vs ${Math.round(e.now_bps ?? 0)} now` };
    if (e.type === "send") return { icon: "↗", text: `Transfer ${e.transfer + 1} sent via ${PATH_NAME[e.path!]}`, sub: `${Math.round(e.bps!)} bps${t.wait_h ? `, after waiting ${t.wait_h}h` : ""}` };
    return { icon: e.late ? "!" : "✓", text: `Transfer ${e.transfer + 1} ${e.late ? "settled late" : "settled"}`, sub: `Total ${Math.round(t.total_bps)} bps, ${usd(t.total_usd)}` };
  };

  return (
    <section className="player" aria-label="Simulation playback">
      <div className="player-bar">
        <div>
          <div className="clock num" aria-live="off">{stamp(sim.start_ts, cursor)}</div>
          <div className="caption" style={{ color: "#b9bdbc" }}>Hour {now} of {n}</div>
        </div>
        <div className="player-controls">
          <button className="pill-btn" onClick={() => { if (finished) setCursor(0); setPlaying((p) => !p); }} aria-label={playing ? "Pause" : finished ? "Replay" : "Play"}>
            {playing ? "Pause" : finished ? "Replay" : "Play"}
          </button>
          <div className="mini-seg" role="group" aria-label="Playback speed">
            {SPEEDS.map((s, i) => <button key={s.label} aria-pressed={i === speed} onClick={() => setSpeed(i)}>{s.label}</button>)}
          </div>
          <button className="ghost-btn" onClick={() => { setPlaying(false); setCursor(n); }}>Skip to end</button>
        </div>
      </div>
      <input className="scrub" type="range" min={0} max={n} step={0.1} value={cursor} aria-label="Simulated time"
        onChange={(e) => { setPlaying(false); setCursor(Number(e.target.value)); }} />

      <div ref={wrap} className="player-body">
        <h3 className="sub-h">What each path costs, hour by hour</h3>
        <svg viewBox={`0 0 ${width} ${MH}`} role="img" aria-label="Cost in basis points for each payment path over the simulated period">
          <g className="axis">
            {[0, 0.5, 1].map((f) => <g key={f}><line x1={m.l} x2={width - m.r} y1={my(maxBps * f)} y2={my(maxBps * f)} stroke="#ffffff22" /><text x={m.l - 8} y={my(maxBps * f) + 4} textAnchor="end" fill="#b9bdbc">{Math.round(maxBps * f)}</text></g>)}
            <text x={m.l - 8} y={8} textAnchor="end" fill="#b9bdbc">bps</text>
          </g>
          {pathsAll.map((p) => {
            const ok = sim.eligible_paths.includes(p);
            const pts = sim.market.map((r, i) => `${i ? "L" : "M"}${x(i).toFixed(1)},${my(Math.min(r.cost_bps[p], maxBps * 1.08)).toFixed(1)}`).join("");
            return <path key={p} d={pts} fill="none" stroke={PATH_COLOR_ON_DARK[p]} strokeWidth={ok ? 2 : 1.2} strokeDasharray={ok ? undefined : "3 4"} opacity={ok ? 1 : 0.6} />;
          })}
          <line x1={x(cursor)} x2={x(cursor)} y1={6} y2={MH - 28} stroke="#fff" strokeOpacity="0.8" />
        </svg>
        <div className="legend dark">
          {pathsAll.map((p) => (
            <span key={p}><i className="swatch" style={{ background: PATH_COLOR_ON_DARK[p] }} />{PATH_NAME[p]}: <b className="num">{Math.round(sim.market[now].cost_bps[p])} bps</b>{sim.eligible_paths.includes(p) ? "" : " (not eligible)"}</span>
          ))}
        </div>

        <h3 className="sub-h">Each transfer, from arrival to settlement</h3>
        <svg viewBox={`0 0 ${width} ${LH}`} role="img" aria-label="Timeline of each transfer for each routing policy">
          {policies.map((p, li) => {
            const yy = 14 + li * lane;
            return (
              <g key={p}>
                <text x={0} y={yy + 4} fill="#fff" fontSize="12">{POLICY_NAME[p]}</text>
                <line x1={m.l + 60} x2={width - m.r} y1={yy} y2={yy} stroke="#ffffff1c" />
                {sim.policies[p].transfers.map((t) => {
                  const scale = (i: number) => m.l + 60 + ((width - m.l - m.r - 60) * i) / n;
                  const a = scale(t.arrive_i), s = scale(Math.min(t.send_i, cursor)), sent = t.send_i <= cursor;
                  return (
                    <g key={t.transfer}>
                      {t.arrive_i <= cursor && <path d={`M${a},${yy - 7} l-4,-7 h8 z`} fill="#fff" />}
                      {t.arrive_i <= cursor && s > a && <rect x={a} y={yy - 3} width={s - a} height={6} rx={3} fill="#ffffff55" />}
                      {sent && <circle cx={scale(t.send_i)} cy={yy} r={6} fill={PATH_COLOR_ON_DARK[t.path]} stroke="#201f1f" strokeWidth={2} />}
                      {sent && t.settle_i <= cursor && <path d={`M${scale(t.settle_i) - 4},${yy} l3,3 l5,-6`} stroke={t.late ? "#ff8a80" : "#c8e9ca"} strokeWidth={2} fill="none" />}
                    </g>
                  );
                })}
                <line x1={m.l + 60 + ((width - m.l - m.r - 60) * cursor) / n} x2={m.l + 60 + ((width - m.l - m.r - 60) * cursor) / n} y1={yy - 14} y2={yy + 14} stroke="#fff" strokeOpacity="0.5" />
              </g>
            );
          })}
        </svg>
        <p className="caption" style={{ color: "#b9bdbc" }}>Triangle: transfer arrives. Pale bar: waiting. Dot: sent, coloured by path. Tick: settled.</p>

        <h3 className="sub-h">Cost paid so far</h3>
        <svg viewBox={`0 0 ${width} ${CH}`} role="img" aria-label="Cumulative cost in US dollars for each routing policy">
          <g className="axis">
            {[0, 0.5, 1].map((f) => <g key={f}><line x1={m.l} x2={width - m.r} y1={cy(maxUsd * f)} y2={cy(maxUsd * f)} stroke="#ffffff22" /><text x={m.l - 8} y={cy(maxUsd * f) + 4} textAnchor="end" fill="#b9bdbc">{usd(maxUsd * f, 0)}</text></g>)}
          </g>
          {policies.map((p) => {
            const upto = Math.min(now, n);
            const d = cum[p].slice(0, upto + 1).map((v, i) => `${i ? "L" : "M"}${x(i).toFixed(1)},${cy(v).toFixed(1)}`).join("");
            return <path key={p} d={d} fill="none" stroke={p === "greedy" ? "#ffffff" : POLICY_COLOR_ON_DARK[p]} strokeWidth={p === "oracle" ? 1.4 : 2} strokeDasharray={p === "oracle" ? "4 3" : undefined} />;
          })}
          <line x1={x(cursor)} x2={x(cursor)} y1={6} y2={CH - 28} stroke="#fff" strokeOpacity="0.5" />
        </svg>
        <div className="legend dark">
          {policies.map((p) => {
            const st = status(p);
            return <span key={p}><i className="swatch" style={{ background: p === "greedy" ? "#fff" : POLICY_COLOR_ON_DARK[p] }} />{POLICY_NAME[p]}: <b className="num">{usd(st.spent)}</b> <span className="muted">({st.waiting} waiting, {st.transit} in transit, {st.done} settled)</span></span>;
          })}
        </div>
      </div>

      <div className="feed">
        <div className="feed-head">
          <h3 className="sub-h" style={{ margin: 0 }}>Activity</h3>
          <div className="mini-seg" role="group" aria-label="Policy shown in the activity feed">
            {policies.map((p) => <button key={p} aria-pressed={p === focus} onClick={() => setFocus(p)}>{POLICY_NAME[p]}</button>)}
          </div>
        </div>
        {events.length === 0 && <p className="caption" style={{ color: "#b9bdbc" }}>Press Play to start. Nothing has happened yet.</p>}
        <ul className="z-list">
          {events.map((e, i) => { const t = evText(e); return (
            <li key={`${e.type}-${e.transfer}-${e.i}-${i}`}><span style={{ display: "flex", gap: 12, alignItems: "center" }}><span className="term-icon" style={{ background: "#ffffff1c", color: "#fff" }} aria-hidden="true">{t.icon}</span><span>{t.text}<br /><span className="muted">{t.sub}</span></span></span><span className="muted num">{stamp(sim.start_ts, e.i).replace(" UTC", "")}</span></li>
          ); })}
        </ul>
      </div>

      <div className="results">
        <h3 className="sub-h">{finished ? "Final results" : "Final results (available when playback ends)"}</h3>
        {finished ? (
          <div className="scroll-x">
            <table className="res num">
              <thead><tr><th>Policy</th><th>Total paid</th><th>Average cost</th><th>Saved vs. quote</th><th>Behind hindsight</th><th>Average wait</th><th>Late</th></tr></thead>
              <tbody>
                {policies.map((p) => {
                  const s = sim.policies[p].summary, ts = sim.policies[p].transfers;
                  const saved = ts.reduce((a, t) => a + t.saving_vs_quote_bps, 0) / ts.length;
                  return (
                    <tr key={p} className={p === best ? "win" : ""}>
                      <td>{POLICY_NAME[p]}{p === best ? " (lowest, excl. hindsight)" : ""}</td>
                      <td>{usd(s.total_usd)}</td><td>{Math.round(s.mean_bps)} bps</td>
                      <td>{saved > 0 ? "+" : saved < 0 ? "−" : ""}{Math.abs(saved).toFixed(1)} bps</td>
                      <td>{s.mean_regret_bps.toFixed(1)} bps</td><td>{s.mean_wait_h.toFixed(1)} h</td><td>{s.late}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        ) : null}
      </div>
    </section>
  );
}

const PATH_COLOR_ON_DARK: Record<string, string> = { P0: "#9085e9", P1: "#199e70", P2: "#3987e5" };
const POLICY_COLOR_ON_DARK: Record<string, string> = { greedy: "#ffffff", forecast_aware: "#c98500", linucb: "#d55181", oracle: "#9aa0a3" };
