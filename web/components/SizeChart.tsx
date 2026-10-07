import type { Meta, Row } from "@/lib/api";
import { PATH_COLOR, size } from "@/lib/format";
import { useWidth } from "./useWidth";

export function SizeChart({ rows, meta }: { rows: Row[]; meta: Meta }) {
  const [ref, width] = useWidth<HTMLDivElement>();
  const paths = Object.keys(meta.paths);
  const sizes = meta.sizes;
  const H = 280, m = { t: 24, r: 8, b: 36, l: 44 };
  const max = Math.max(...rows.map((r) => r.total_bps)) * 1.1;
  const y = (v: number) => m.t + (H - m.t - m.b) * (1 - v / max);
  const gw = (width - m.l - m.r) / sizes.length;
  const bw = Math.min(40, (gw * 0.78) / paths.length - 2);
  const ticks = [0, 0.25, 0.5, 0.75, 1].map((f) => Math.round((max * f) / 50) * 50);
  const cell = (p: string, a: number) => rows.find((r) => r.path === p && r.amount === a)!;

  return (
    <section className="panel" aria-labelledby="size-h">
      <div className="panel-head">
        <div>
          <h2 id="size-h">Small transfers pay the most</h2>
          <p className="lede">Fixed fees and network fees do not shrink with the amount, so cost as a share of the transfer falls as it grows.</p>
        </div>
      </div>
      <div className="legend">
        {paths.map((p) => (
          <span key={p}><i className="swatch" style={{ background: PATH_COLOR[p] }} />{meta.paths[p]}</span>
        ))}
      </div>
      <div className="chart" ref={ref}>
        <svg viewBox={`0 0 ${width} ${H}`} role="img" aria-label="All-in cost in basis points by transfer size and payment path">
          <g className="axis">
            {ticks.map((t) => (
              <g key={t}>
                <line x1={m.l} x2={width - m.r} y1={y(t)} y2={y(t)} stroke="var(--line)" />
                <text x={m.l - 8} y={y(t) + 4} textAnchor="end">{t}</text>
              </g>
            ))}
            {sizes.map((a, i) => (
              <text key={a} x={m.l + gw * i + gw / 2} y={H - 10} textAnchor="middle">{size(a)}</text>
            ))}
            <text x={m.l - 8} y={12} textAnchor="end">bps</text>
          </g>
          {sizes.map((a, i) =>
            paths.map((p, j) => {
              const v = cell(p, a).total_bps;
              const x = m.l + gw * i + gw / 2 - (paths.length * (bw + 2)) / 2 + j * (bw + 2);
              const h = y(0) - y(v);
              return (
                <g key={p + a}>
                  <path d={`M${x},${y(0)} v${-(h - 4)} a4,4 0 0 1 4,-4 h${bw - 8} a4,4 0 0 1 4,4 v${h - 4} z`} fill={PATH_COLOR[p]}>
                    <title>{`${meta.paths[p]}, ${size(a)}: ${Math.round(v)} bps`}</title>
                  </path>
                  <text x={x + bw / 2} y={y(v) - 6} textAnchor="middle" fontSize="12" fill="var(--ink)" className="num">{Math.round(v)}</text>
                </g>
              );
            }),
          )}
        </svg>
      </div>
      <details className="table-view">
        <summary>View as table</summary>
        <table className="num">
          <thead><tr><th>Transfer size</th>{paths.map((p) => <th key={p}>{meta.paths[p]} (bps)</th>)}</tr></thead>
          <tbody>{sizes.map((a) => <tr key={a}><td>{size(a)}</td>{paths.map((p) => <td key={p}>{cell(p, a).total_bps.toFixed(1)}</td>)}</tr>)}</tbody>
        </table>
      </details>
    </section>
  );
}
