import { useState } from "react";
import type { Meta, Timeline as T } from "@/lib/api";
import { PATH_COLOR, bps, size } from "@/lib/format";
import { useWidth } from "./useWidth";

export function Timeline({ data, meta, path, amount, onPath }: {
  data: T; meta: Meta; path: string; amount: number; onPath: (p: string) => void;
}) {
  const [ref, width] = useWidth<HTMLDivElement>();
  const [hover, setHover] = useState<number | null>(null);
  const s = data.series;
  const H = 300, m = { t: 20, r: 12, b: 32, l: 48 };
  const max = Math.max(...s.map((p) => p.total_bps)) * 1.08;
  const min = Math.min(...s.map((p) => p.total_bps)) * 0.92;
  const x = (i: number) => m.l + ((width - m.l - m.r) * i) / Math.max(1, s.length - 1);
  const y = (v: number) => m.t + (H - m.t - m.b) * (1 - (v - min) / (max - min));
  const line = s.map((p, i) => `${i ? "L" : "M"}${x(i).toFixed(1)},${y(p.total_bps).toFixed(1)}`).join("");
  const color = PATH_COLOR[path];
  const stress = s.map((p, i) => ({ p, i })).filter(({ p }) => p.regime === "stress");
  const dated = data.events.filter((e) => e.date && e.status === "verified");
  const leads = data.events.filter((e) => e.status !== "verified").length;
  const labelIdx = [0, Math.floor(s.length / 2), s.length - 1];
  const hp = hover === null ? null : s[hover];

  return (
    <section className="panel" aria-labelledby="time-h">
      <div className="panel-head">
        <div>
          <h2 id="time-h">Cost over time</h2>
          <p className="lede">Daily average all-in cost for a {size(amount)} transfer, premium not counted. Shaded days are the stress regime.</p>
        </div>
        <div className="tabs" role="group" aria-label="Payment path" style={{ background: "var(--page)" }}>
          {Object.keys(meta.paths).map((p) => (
            <button key={p} aria-pressed={p === path} onClick={() => onPath(p)}>
              <span className="swatch" style={{ background: PATH_COLOR[p] }} />{meta.paths[p]}
            </button>
          ))}
        </div>
      </div>
      <div className="chart-wrap chart" ref={ref}>
        <svg
          viewBox={`0 0 ${width} ${H}`} role="img"
          aria-label={`Daily all-in cost in basis points for ${meta.paths[path]}`}
          onPointerMove={(e) => {
            const r = e.currentTarget.getBoundingClientRect();
            const px = ((e.clientX - r.left) / r.width) * width;
            setHover(Math.min(s.length - 1, Math.max(0, Math.round(((px - m.l) / (width - m.l - m.r)) * (s.length - 1)))));
          }}
          onPointerLeave={() => setHover(null)}
        >
          <g className="axis">
            {[0, 0.5, 1].map((f) => {
              const v = min + (max - min) * f;
              return (
                <g key={f}>
                  <line x1={m.l} x2={width - m.r} y1={y(v)} y2={y(v)} stroke="var(--line)" />
                  <text x={m.l - 8} y={y(v) + 4} textAnchor="end">{Math.round(v)}</text>
                </g>
              );
            })}
            {labelIdx.map((i) => (
              <text key={i} x={x(i)} y={H - 8} textAnchor={i === 0 ? "start" : i === s.length - 1 ? "end" : "middle"}>{s[i].date}</text>
            ))}
            <text x={m.l - 8} y={10} textAnchor="end">bps</text>
          </g>
          {stress.length > 0 && (
            <rect x={x(stress[0].i)} width={x(stress[stress.length - 1].i) - x(stress[0].i)} y={m.t} height={H - m.t - m.b} fill="var(--mint)" opacity="0.55" />
          )}
          <path d={line} fill="none" stroke={color} strokeWidth="2" strokeLinejoin="round" strokeLinecap="round" />
          {hover !== null && hp && (
            <g>
              <line x1={x(hover)} x2={x(hover)} y1={m.t} y2={H - m.b} stroke="var(--ink)" strokeOpacity="0.35" />
              <circle cx={x(hover)} cy={y(hp.total_bps)} r="5" fill={color} stroke="#fff" strokeWidth="2" />
            </g>
          )}
        </svg>
        {hp && hover !== null && (
          <div className="tooltip num" style={{ left: `${(x(hover) / width) * 100}%`, top: `${(y(hp.total_bps) / H) * 100}%`, marginTop: -12 }}>
            <b>{hp.date}</b><br />{bps(hp.total_bps)} · {hp.regime}
          </div>
        )}
      </div>
      <p className="note">
        {dated.length === 0
          ? `No dated regulatory events are shown yet: ${leads} calendar entries are unverified leads and are held back until each has a primary source.`
          : `${dated.length} verified regulatory events are in the calendar.`}
      </p>
      <details className="table-view">
        <summary>View as table</summary>
        <table className="num">
          <thead><tr><th>Date</th><th>Cost (bps)</th><th>Regime</th></tr></thead>
          <tbody>{s.map((p) => <tr key={p.date}><td>{p.date}</td><td>{p.total_bps.toFixed(1)}</td><td>{p.regime}</td></tr>)}</tbody>
        </table>
      </details>
    </section>
  );
}
