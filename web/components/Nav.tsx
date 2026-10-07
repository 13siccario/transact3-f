"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const ITEMS = [
  { href: "/", label: "Costs" },
  { href: "/forecasts", label: "Forecasts" },
  { href: "/replay", label: "Replay" },
  { href: "/simulate", label: "Simulate" },
] as const;

export function Nav() {
  const path = usePathname();
  return (
    <nav className="nav" aria-label="Sections">
      {ITEMS.map((i) => (
          <Link key={i.label} href={i.href} aria-current={path === i.href ? "page" : undefined}>{i.label}</Link>
      ))}
    </nav>
  );
}

export function TopBar({ synthetic }: { synthetic: boolean }) {
  return (
    <header className="topbar">
      <div className="brand">
        <svg className="star" viewBox="0 0 24 24" aria-hidden="true" fill="currentColor">
          <path d="M12 0l2.2 7.3L21 4l-3.3 6.8L24 12l-6.3 1.2L21 20l-6.8-3.3L12 24l-2.2-7.3L3 20l3.3-6.8L0 12l6.3-1.2L3 4l6.8 3.3z" />
        </svg>
        transact3.
      </div>
      {synthetic && <span className="chip warn"><span className="dot" />Synthetic data, not observations</span>}
    </header>
  );
}
