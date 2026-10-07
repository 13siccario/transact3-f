import { PATH_COLOR, bps, pct, usd } from "@/lib/format";
import type { Row } from "@/lib/api";

export function PathCards({ rows }: { rows: Row[] }) {
  const sorted = [...rows].sort((a, b) => a.total_bps - b.total_bps);
  const bestPath = sorted[0]?.path;
  return (
    <div className="paths">
      {[...sorted].map((r) => {
        const best = r.path === bestPath;
        const prem = Number(r.c_prem);
        return (
          <article key={r.path} className={`path-card${best ? " best" : ""}`} aria-label={r.label}>
            <div className="path-head">
              <span className="path-name">
                <span className="swatch" style={{ background: PATH_COLOR[r.path] }} />
                {r.label}
              </span>
              {best && <span className="best-tag">Lowest cost</span>}
            </div>
            <p className="caption" style={{ margin: "14px 0 0" }}>All-in cost to send {usd(r.amount, 0)}</p>
            <div className="big num">
              {Math.round(r.total_bps).toLocaleString("en-US")}
              <small>bps</small>
            </div>
            <div className="sub-amount num">{usd(r.total_ex_prem)} <span className="caption">({pct(r.total_bps)})</span></div>
            {prem !== 0 && (
              <p className="prem-note">
                Local premium measured at <b className="num">{usd(prem)}</b>. It is not counted above and is not a free gain.
              </p>
            )}
          </article>
        );
      })}
    </div>
  );
}
