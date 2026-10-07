export type BarItem = { label: string; value: number; lo?: number | null; hi?: number | null; color?: string; note?: string };

/** Horizontal bars on a zero baseline, sorted by the caller. Optional 95% interval whiskers. */
export function HBars({ items, unit = "bps", best }: { items: BarItem[]; unit?: string; best?: string }) {
  const max = Math.max(...items.map((i) => Math.max(i.value, i.hi ?? 0)), 1e-9) * 1.05;
  return (
    <div className="hbars" role="list">
      {items.map((i) => (
        <div key={i.label} role="listitem" className={`hbar${i.label === best ? " best" : ""}`}>
          <span className="lab">{i.label}{i.note ? <span className="muted" style={{ color: "var(--ink-2)" }}> {i.note}</span> : null}</span>
          <span className="track" aria-hidden="true">
            <span className="fill" style={{ width: `${(Math.max(i.value, 0) / max) * 100}%`, background: i.color ?? "var(--p1)" }} />
            {i.lo != null && i.hi != null && !Number.isNaN(i.lo) && <span className="whisker" style={{ left: `${(i.lo / max) * 100}%`, width: `${((i.hi - i.lo) / max) * 100}%` }} />}
          </span>
          <span className="val num">{i.value.toFixed(1)} {unit}</span>
        </div>
      ))}
    </div>
  );
}
