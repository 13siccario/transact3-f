export const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export type Envelope<T> = {
  source_kind: "synthetic" | "real";
  config_hash: string;
  cost_params: string;
  disclaimer: string;
  data: T;
};

export type Meta = {
  paths: Record<string, string>;
  terms: string[];
  sizes: number[];
  regimes: string[];
  start: string;
  end: string;
};

export type Row = {
  path: string;
  label: string;
  amount: number;
  n_hours: number;
  total: number;
  total_ex_prem: number;
  total_bps: number;
} & Record<string, number | string>;

export type TimelinePoint = { date: string; total_bps: number; premium_bps: number; regime: string };
export type CalendarEvent = { id: string; date: string | null; title: string; status: string; primary_source: string | null };
export type Timeline = { series: TimelinePoint[]; events: CalendarEvent[] };

export async function get<T>(path: string): Promise<Envelope<T>> {
  const res = await fetch(`${API}${path}`);
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail ?? `Request failed (${res.status})`);
  }
  return res.json();
}

export type SimMeta = {
  start: string; end: string; hours: number; policies: Record<string, string>;
  default_scenario: string; scenarios: Record<string, string[]>; paths: Record<string, string>;
  latency_h: Record<string, number>; rules_version: string; rules_reviewed: boolean;
};
export type SimTransfer = {
  transfer: number; arrive_i: number; send_i: number; settle_i: number; wait_h: number; path: string;
  cost_bps: number; penalty_bps: number; total_bps: number; total_usd: number; quote_bps: number;
  saving_vs_quote_bps: number; oracle_bps: number; regret_bps: number; late: boolean;
};
export type SimEvent = { i: number; type: "arrive" | "wait" | "send" | "settle"; transfer: number; path?: string; bps?: number; late?: boolean; now_bps?: number; forecast_next_bps?: number | null };
export type SimPolicy = {
  label: string; transfers: SimTransfer[]; events: SimEvent[];
  summary: { total_usd: number; mean_bps: number; mean_regret_bps: number; mean_wait_h: number; late: number };
};
export type SimResult = {
  amount: number; deadline_h: number; count: number; interval_h: number; scenario: string; eligible_paths: string[];
  start_ts: string; start_range: [string, string];
  market: { i: number; ts: string; regime: string; premium_pct: number; cost_bps: Record<string, number> }[];
  policies: Record<string, SimPolicy>;
};
export type Table = { caption: string; columns: string[]; rows: Record<string, number | string | null>[] };
