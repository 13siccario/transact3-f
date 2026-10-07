"""Phase 0 feasibility probes. Each probe makes one small public request and
records what actually happened. Endpoints are candidates, not verified sources:
a reachable endpoint is not yet a go decision (check history, terms, licence).
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

import httpx


@dataclass
class ProbeResult:
    component: str
    endpoint: str
    status: str      # reachable | http_error | rate_limited | unreachable
    detail: str


def _get(client: httpx.Client, url: str, **kw) -> tuple[str, str]:
    try:
        r = client.get(url, **kw)
    except httpx.HTTPError as e:
        return "unreachable", f"{type(e).__name__}: {e}"
    if r.status_code == 429:
        return "rate_limited", "HTTP 429; inconclusive, retry later"
    if r.status_code >= 400:
        return "http_error", f"HTTP {r.status_code}"
    return "reachable", f"HTTP {r.status_code}, {len(r.content)} bytes"


def run_probes(timeout: float = 15.0) -> list[ProbeResult]:
    # Fixed past weekday (Dukascopy months are 0-indexed: 00 = January) so results are repeatable.
    y, m, d = 2024, 0, 16
    probes = [
        ("USD/INR hourly (tick provider)", "Dukascopy datafeed, USDINR",
         f"https://datafeed.dukascopy.com/datafeed/USDINR/{y}/{m:02d}/{d:02d}/12h_ticks.bi5", {}),
        ("USD/INR hourly (control: EURUSD)", "Dukascopy datafeed, EURUSD",
         f"https://datafeed.dukascopy.com/datafeed/EURUSD/{y}/{m:02d}/{d:02d}/12h_ticks.bi5", {}),
        ("USD/INR daily reference", "FBIL site (reachability only)", "https://www.fbil.org.in/", {}),
        ("Local USDT/INR history", "CoinGecko market_chart (tether, inr, 30d)",
         "https://api.coingecko.com/api/v3/coins/tether/market_chart",
         {"params": {"vs_currency": "inr", "days": "30"}}),
        ("On-chain pools", "DefiLlama yields pools", "https://yields.llama.fi/pools", {}),
        ("Peg deviation", "DefiLlama stablecoins", "https://stablecoins.llama.fi/stablecoins", {}),
    ]
    results = []
    with httpx.Client(timeout=timeout, follow_redirects=True, headers={"User-Agent": "transact3-feasibility/0.1"}) as c:
        for comp, label, url, kw in probes:
            status, detail = _get(c, url, **kw)
            results.append(ProbeResult(comp, label, status, detail))
        # Gas: public JSON-RPC fee history
        try:
            r = c.post("https://ethereum-rpc.publicnode.com",
                       json={"jsonrpc": "2.0", "id": 1, "method": "eth_feeHistory", "params": ["0x4", "latest", []]})
            ok = r.status_code < 400 and "result" in r.json()
            results.append(ProbeResult("Gas fees", "Public Ethereum JSON-RPC eth_feeHistory",
                                       "reachable" if ok else "http_error", f"HTTP {r.status_code}"))
        except (httpx.HTTPError, ValueError) as e:
            results.append(ProbeResult("Gas fees", "Public Ethereum JSON-RPC eth_feeHistory", "unreachable",
                                       f"{type(e).__name__}: {e}"))
    return results


def render_report(results: list[ProbeResult]) -> str:
    when = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    lines = [
        "# Data feasibility report", "",
        f"Generated {when} by `transact3 feasibility`. Phase 0 of the project plan.", "",
        "A reachable endpoint is **not** a go decision. A go needs: confirmed history covering the sample period,",
        "the right frequency, and acceptable source terms. Decisions below are left blank until a person records them.", "",
        "| Component | Candidate endpoint | Probe result | Detail | Decision (go / no-go) | Notes |",
        "|---|---|---|---|---|---|",
    ]
    for r in results:
        lines.append(f"| {r.component} | {r.endpoint} | {r.status} | {r.detail} | _pending_ | |")
    lines += ["", "## Still manual", "",
              "- INR-referenced on-chain token: is there any liquid pool? If not, use non-INR EM proxies (decision gate).",
              "- Regulatory event calendar: every event needs a primary source (see `src/transact3/data/calendar/events.yaml`).",
              "- Sample period must include the June 2026 episode once it is traced to a primary document.", ""]
    return "\n".join(lines)
