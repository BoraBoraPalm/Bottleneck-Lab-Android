"""Benchmark series for the Depot-Check tab.

Every benchmark is a broad, investable ETF (one per market). Each run
downloads ten years of daily data and publishes it in the chart format
(adjusted closes scaled to the latest close, i.e. distributions reinvested)
plus the raw closes, so the app can see each distribution (needed for the
Austrian dividend tax option). The app shows either the ETF itself (with its
running costs, TER, already inside the price) or the index estimate
"ETF + TER" (no fund costs).

A distributing ETF is only published if its distributions are visible in the
data; otherwise the adjusted series would silently miss the dividends. Then
the next candidate (usually an accumulating ETF) is used. index.json lists
which ETF was chosen per benchmark, so the app only auto-selects benchmarks
with verified data.
"""
import json
import os
from datetime import datetime, timezone
from pathlib import Path

from build_snapshot import fetch_yahoo
from chart_history import chart_payload

ROOT = Path("docs/benchmarks")
EUROPE = ["AT", "BE", "CH", "CZ", "DK", "ES", "FI", "FR", "GR", "HU", "IE", "IS", "IT", "LU", "NL", "NO", "PL", "PT", "RO", "SE"]
EMERGING = ["AE", "BR", "CL", "CO", "EG", "ID", "KW", "MX", "MY", "PE", "PH", "QA", "SA", "TH", "TR", "ZA"]
# A distribution must show up within this many sessions (annual payers included).
RECENT_SESSIONS = 400
MIN_YIELD, MAX_YIELD = 1e-4, 0.9


def etf(symbol, detail, ter_percent, distributing):
    # distributing: True = must show distributions, False = accumulating, None = unknown (not checked)
    return {"symbol": symbol, "detail": detail, "ter_percent": ter_percent, "distributing": distributing}


# markets: issuer countries (ISO) for the automatic choice; "*" is the fallback.
# ter_percent: running costs p.a. from the provider (checked 2026-11-09).
BENCHMARKS = [
    {"id": "SPY", "name": "S&P 500", "markets": ["US"],
     "etfs": [etf("SPY", "SPDR S&P 500 ETF, ausschüttend", 0.0945, True)]},
    {"id": "DAX", "name": "DAX", "markets": ["DE"],
     "etfs": [etf("EL4F.DE", "Deka DAX (ausschüttend) UCITS ETF", 0.15, True),
              etf("EXS1.DE", "iShares Core DAX UCITS ETF (DE), thesaurierend", 0.16, False)]},
    {"id": "STOXX600", "name": "STOXX Europe 600", "markets": EUROPE,
     "etfs": [etf("EXSA.DE", "iShares STOXX Europe 600 UCITS ETF (DE), ausschüttend", 0.20, True),
              etf("XSX6.DE", "Xtrackers STOXX Europe 600 UCITS ETF 1C, thesaurierend", 0.20, False)]},
    {"id": "FTSE100", "name": "FTSE 100", "markets": ["GB"],
     "etfs": [etf("ISF.L", "iShares Core FTSE 100 UCITS ETF, ausschüttend", 0.07, True)]},
    {"id": "TSX60", "name": "S&P/TSX 60", "markets": ["CA"],
     "etfs": [etf("XIU.TO", "iShares S&P/TSX 60 Index ETF, ausschüttend", 0.17, True)]},
    {"id": "TOPIX", "name": "TOPIX", "markets": ["JP"],
     "etfs": [etf("1306.T", "NEXT FUNDS TOPIX ETF, ausschüttend", 0.0822, True)]},
    {"id": "HSI", "name": "Hang Seng", "markets": ["HK"],
     "etfs": [etf("2800.HK", "Tracker Fund of Hong Kong, ausschüttend", 0.06, True)]},
    {"id": "ASX200", "name": "S&P/ASX 200", "markets": ["AU", "NZ"],
     "etfs": [etf("STW.AX", "SPDR S&P/ASX 200 Fund, ausschüttend", 0.05, True)]},
    {"id": "KOSPI200", "name": "KOSPI 200", "markets": ["KR"],
     "etfs": [etf("069500.KS", "Samsung KODEX 200 ETF, ausschüttend", 0.15, True)]},
    {"id": "TW50", "name": "Taiwan 50", "markets": ["TW"],
     "etfs": [etf("0050.TW", "Yuanta Taiwan Top 50 ETF, ausschüttend", 0.13, True)]},
    {"id": "NIFTY50", "name": "Nifty 50", "markets": ["IN"],
     "etfs": [etf("NIFTYBEES.NS", "Nippon India ETF Nifty 50 BeES", 0.04, None)]},
    {"id": "CSI300", "name": "CSI 300", "markets": ["CN"],
     "etfs": [etf("510300.SS", "Huatai-PineBridge CSI 300 ETF", 0.20, None)]},
    {"id": "EM", "name": "MSCI Emerging Markets", "markets": EMERGING,
     "etfs": [etf("EEM", "iShares MSCI Emerging Markets ETF, ausschüttend", 0.72, True)]},
    {"id": "WORLD", "name": "MSCI World", "markets": [],
     "etfs": [etf("IWDA.AS", "iShares Core MSCI World UCITS ETF, thesaurierend", 0.20, False)]},
    {"id": "ACWI", "name": "MSCI ACWI (Welt)", "markets": ["*"],
     "etfs": [etf("ACWI", "iShares MSCI ACWI ETF, ausschüttend", 0.32, True)]},
]


def _bars_with_adjusted(bars):
    # One bar per date (the last one); without adjclose the close is used.
    by_date = {}
    for bar in bars:
        by_date[bar[0]] = bar if bar[5] is not None else (*bar[:5], bar[3])
    return [by_date[d] for d in sorted(by_date)]


def distributions(points, closes):
    """Indices of ex-days: the adjusted/raw ratio rises by the payout yield."""
    out = []
    for i in range(1, len(points)):
        before, now = points[i - 1][1] / closes[i - 1], points[i][1] / closes[i]
        if now > 0 and MIN_YIELD <= 1 - before / now < MAX_YIELD:
            out.append(i)
    return out


def _load(symbol, fetch):
    bars, currency, source = fetch(symbol)
    bars = _bars_with_adjusted(bars)
    chart = chart_payload(symbol, bars, currency, source)
    if not chart:
        raise RuntimeError("no usable daily series")
    raw = {bar[0]: float(bar[3]) for bar in bars}
    chart["closes"] = [raw[day] for day, _ in chart["points"]]
    return chart, currency


def publish_benchmarks(root=ROOT, fetch=fetch_yahoo, now=None):
    root = Path(root)
    root.mkdir(parents=True, exist_ok=True)
    listed = []
    for item in BENCHMARKS:
        entry = {k: item[k] for k in ("id", "name", "markets")}
        entry.update(available=False, total_return=True)
        tried = {}
        for candidate in item["etfs"]:
            try:
                chart, currency = _load(candidate["symbol"], fetch)
                recent = [i for i in distributions(chart["points"], chart["closes"])
                          if i >= len(chart["points"]) - RECENT_SESSIONS]
                if candidate["distributing"] and not recent:
                    raise RuntimeError("distributions missing in the Yahoo data")
                meta = dict(candidate, id=item["id"], name=item["name"], distributions_recent=len(recent))
                chart["benchmark"] = meta
                path = root / (item["id"] + ".json")
                tmp = path.with_suffix(".tmp")
                tmp.write_text(json.dumps(chart, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
                os.replace(tmp, path)
                entry.update(meta, available=True, currency=currency, asof=chart["asof"],
                             first=chart["points"][0][0], points=len(chart["points"]))
                break
            except Exception as exc:
                tried[candidate["symbol"]] = type(exc).__name__ + ": " + str(exc)[:120]
        if tried:
            entry["rejected"] = tried
        if not entry["available"]:
            entry["error"] = "; ".join(f"{s}: {e}" for s, e in tried.items())
        listed.append(entry)
    stamp = (now or datetime.now(timezone.utc)).isoformat().replace("+00:00", "Z")
    (root / "index.json").write_text(json.dumps({"version": 2, "generated_at": stamp, "benchmarks": listed},
                                                ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    return {"available": sum(1 for e in listed if e["available"]), "total": len(listed),
            "missing": [e["id"] for e in listed if not e["available"]],
            "chosen": {e["id"]: e.get("symbol") for e in listed if e["available"]},
            "rejected": {s: e for x in listed for s, e in x.get("rejected", {}).items()}}
