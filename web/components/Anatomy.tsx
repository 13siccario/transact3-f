import { useState } from "react";
import type { Meta, Row } from "@/lib/api";
import { PATH_COLOR, TERM_LABELS, TERM_ORDER, bps, usd } from "@/lib/format";

const ICON: Record<string, string> = { c_ramp: "₹", c_fx: "FX", c_gas: "⛽", c_lp: "%", c_slip: "Δ", c_peg: "$", c_reg: "§", c_prem: "±" };

export function Anatomy({ rows, meta }: { rows: Row[]; meta: Meta }) {
  const paths = Object.keys(meta.paths);
  const [path, setPath] = useState("P1");
  const row = rows.find((r) => r.path === path);
  if (!row) return null;
  const max = Math.max(...TERM_ORDER.map((t) => Number(row[t])), 0.0001);
  const prem = Number(row.c_prem);

  return (
    <section className="panel mint" aria-labelledby="anatomy-h">
      <div className="panel-head">
        <div>
          <h2 id="anatomy-h">Where the cost comes from</h2>
          <p className="lede">Each line is one charge, averaged over the selected period, for a {usd(row.amount, 0)} transfer.</p>
        </div>
        <div className="tabs" role="group" aria-label="Payment path">
          {paths.map((p) => (
            <button key={p} aria-pressed={p === path} onClick={() => setPath(p)}>
              <span className="swatch" style={{ background: PATH_COLOR[p] }} />
              {meta.paths[p]}
            </button>
          ))}
        </div>
      </div>

      <ul className="terms">
        {TERM_ORDER.map((t) => {
          const v = Number(row[t]);
          const info = TERM_LABELS[t];
          return (
            <li key={t} className={`term${v === 0 ? " zero" : ""}`}>
              <span className="term-icon" aria-hidden="true">{ICON[t]}</span>
              <div>
                <div className="term-name">{info.name}</div>
                <div className="term-hint">{info.hint}</div>
              </div>
              <div className="term-amount num">
                {usd(v)}
                <small>{bps((v / row.amount) * 1e4)}</small>
              </div>
              <div className="term-bar" aria-hidden="true">
                <i style={{ width: `${(v / max) * 100}%`, background: PATH_COLOR[path] }} />
              </div>
            </li>
          );
        })}
      </ul>

      <div className="total-line num">
        <span>All-in cost, premium not counted</span>
        <span>{usd(row.total_ex_prem)}</span>
      </div>

      {prem !== 0 && (
        <div className="term prem">
          <span className="term-icon" aria-hidden="true">{ICON.c_prem}</span>
          <div>
            <div className="term-name">{TERM_LABELS.c_prem.name}</div>
            <div className="term-hint">{TERM_LABELS.c_prem.hint}</div>
          </div>
          <div className="term-amount num">{usd(prem)}<small>{bps((prem / row.amount) * 1e4)}</small></div>
        </div>
      )}
    </section>
  );
}
