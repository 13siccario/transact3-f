export const usd = (n: number, digits = 2) =>
  `${n < 0 ? "−" : ""}$${Math.abs(n).toLocaleString("en-US", { minimumFractionDigits: digits, maximumFractionDigits: digits })}`;

export const bps = (n: number) => `${Math.round(n).toLocaleString("en-US")} bps`;

export const pct = (b: number) => `${(b / 100).toFixed(2)}%`;

export const size = (n: number) => `$${n.toLocaleString("en-US")}`;

export const TERM_LABELS: Record<string, { name: string; hint: string }> = {
  c_ramp: { name: "Bank or exchange fees", hint: "Fixed and percentage fees to move money in and out" },
  c_fx: { name: "Exchange-rate margin", hint: "Market spread plus the provider's margin on the INR conversion" },
  c_gas: { name: "Network fee", hint: "Gas paid to send the stablecoin on-chain" },
  c_lp: { name: "Pool fee", hint: "Liquidity-pool fee on the stablecoin swap" },
  c_slip: { name: "Price impact", hint: "How far the transfer moves the pool price" },
  c_peg: { name: "Stablecoin off-peg", hint: "Gap between the stablecoin and one dollar at settlement" },
  c_reg: { name: "Regulatory charges", hint: "Taxes or levies. Zero until set from a primary source" },
  c_prem: { name: "Local price premium", hint: "Measured gap to the reference rate. Reported, never counted as a gain" },
};

export const TERM_ORDER = ["c_ramp", "c_fx", "c_gas", "c_lp", "c_slip", "c_peg", "c_reg"];

export const PATH_COLOR: Record<string, string> = {
  P0: "var(--p0)",
  P1: "var(--p1)",
  P2: "var(--p2)",
};

export const POLICY_COLOR: Record<string, string> = {
  greedy: "#201f1f",
  forecast_aware: "#c77a12",
  linucb: "#b83f86",
  oracle: "#8e9294",
};
export const POLICY_NAME: Record<string, string> = {
  greedy: "Send now",
  forecast_aware: "Forecast-aware",
  linucb: "Learning router",
  oracle: "Perfect hindsight",
};
export const PATH_NAME: Record<string, string> = { P0: "Conventional", P1: "Compliant stablecoin", P2: "Onshore exchange" };
