import { useEffect, useState } from "react";
import { get } from "@/lib/api";
import { useWidth } from "./useWidth";

type Pt = { target_ts: string; y_true: number; regime: string; model_pred: number; benchmark_pred: number };

export function ForecastChart({ target, targetName, model, modelName, benchName }: {
  target: string; targetName: string; model: string; modelName: string; benchName: string;
}) {
  const [pts, setPts] = useState<Pt[] | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [hover, setHover] = useState<number | null>(null);
  const [ref, width] = useWidth<HTMLDivElement>();

  useEffect(() => {
    setPts(null);
    get<{ points: Pt[] }>(`/api/forecast/series?target=${target}&model=${model}`)
      .then((r) => { setPts(r.data.points); setErr(null); })
      .catch((e) => setErr(e.message));
  }, [target, model]);

  if (err) return <p className="state error" role="alert">{err}</p>;
  if (!pts) return <p className="state">Loading…</p>;

  const H = 300, m = { t: 16, r: 12, b: 32, l: 56 };
  const vals = pts.flatMap((p) => [p.y_true, p.model_pred, p.benchmark_pred]);
  const lo = Math.min(...vals), hi = Math.max(...vals), pad = (hi - lo) * 0.08 || 1;
  const x = (i: number) => m.l + ((width - m.l - m.r) * i) / Math.max(1, pts.length - 1);
  const y = (v: number) => m.t + (H - m.t - m.b) * (1 - (v - (lo - pad)) / (hi - lo + 2 * pad));
  const path = (k: keyof Pt) => pts.map((p, i) => `${i ? "L" : "M"}${x(i).toFixed(1)},${y(p[k] as number).toFixed(1)}`).join("");
  const fmt = (v: number) => (Math.abs(v) < 0.01 ? v.toExponential(1) : v.toFixed(Math.abs(v) < 10 ? 3 : 1));
  const hp = hover === null ? null : pts[hover];
  const stressIdx = pts.map((p, i) => ({ p, i })).filter(({ p }) => p.regime === "stress");

  return (
    <>
      <div className="legend">
        <span><i className="swatch" style={{ background: "var(--ink)" }} />Actual</span>
        <span><i className="swatch" style={{ background: "var(--p1)" }} />{modelName}</span>
        <span><i className="swatch" style={{ background: "#9a9d9f" }} />{benchName} (benchmark)</span>
      </div>
      <div className="chart-wrap chart" ref={ref}>
        <svg
          viewBox={`0 0 ${width} ${H}`} role="img" aria-label={`${targetName}: actual, ${modelName} forecast and benchmark forecast, last seven days`}
          onPointerMove={(e) => {
            const r = e.currentTarget.getBoundingClientRect();
            const px = ((e.clientX - r.left) / r.width) * width;
            setHover(Math.min(pts.length - 1, Math.max(0, Math.round(((px - m.l) / (width - m.l - m.r)) * (pts.length - 1)))));
          }}
          onPointerLeave={() => setHover(null)}
        >
          <g className="axis">
            {[0, 0.5, 1].map((f) => {
              const v = lo - pad + (hi - lo + 2 * pad) * f;
              return <g key={f}><line x1={m.l} x2={width - m.r} y1={y(v)} y2={y(v)} stroke="var(--line)" /><text x={m.l - 8} y={y(v) + 4} textAnchor="end">{fmt(v)}</text></g>;
            })}
            {[0, Math.floor(pts.length / 2), pts.length - 1].map((i) => (
              <text key={i} x={x(i)} y={H - 8} textAnchor={i === 0 ? "start" : i === pts.length - 1 ? "end" : "middle"}>{pts[i].target_ts.slice(5, 16)}</text>
            ))}
          </g>
          {stressIdx.length > 0 && <rect x={x(stressIdx[0].i)} width={x(stressIdx[stressIdx.length - 1].i) - x(stressIdx[0].i)} y={m.t} height={H - m.t - m.b} fill="var(--mint)" opacity="0.5" />}
          <path d={path("benchmark_pred")} fill="none" stroke="#9a9d9f" strokeWidth="1.5" strokeDasharray="4 3" />
          <path d={path("y_true")} fill="none" stroke="var(--ink)" strokeWidth="1.5" />
          <path d={path("model_pred")} fill="none" stroke="var(--p1)" strokeWidth="2" />
          {hover !== null && <line x1={x(hover)} x2={x(hover)} y1={m.t} y2={H - m.b} stroke="var(--ink)" strokeOpacity="0.35" />}
        </svg>
        {hp && hover !== null && (
          <div className="tooltip num" style={{ left: `${(x(hover) / width) * 100}%`, top: 0, transform: "translate(-50%, 0)" }}>
            <b>{hp.target_ts.slice(0, 16)}</b><br />
            Actual {fmt(hp.y_true)}<br />{modelName} {fmt(hp.model_pred)}<br />Benchmark {fmt(hp.benchmark_pred)}
          </div>
        )}
      </div>
      <details className="table-view">
        <summary>View as table</summary>
        <table className="num">
          <thead><tr><th>Hour (UTC)</th><th>Actual</th><th>{modelName}</th><th>Benchmark</th></tr></thead>
          <tbody>{pts.map((p) => <tr key={p.target_ts}><td>{p.target_ts.slice(0, 16)}</td><td>{fmt(p.y_true)}</td><td>{fmt(p.model_pred)}</td><td>{fmt(p.benchmark_pred)}</td></tr>)}</tbody>
        </table>
      </details>
    </>
  );
}
