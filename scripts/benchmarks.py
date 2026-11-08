"""Benchmark series for the Depot-Check tab.

Each run downloads ten years of daily data for a small, fixed list of broad
market benchmarks (ETFs or total-return indices, i.e. including dividends)
and publishes them in the chart format (adjusted closes scaled to the latest
close) under docs/benchmarks/. index.json lists which ones are available, so
the app only auto-selects benchmarks with verified data.
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
# markets: issuer countries (ISO) for the automatic choice; "*" is the fallback.
BENCHMARKS = [
    {"id": "SPY", "symbol": "SPY", "name": "S&P 500", "detail": "SPDR S&P 500 ETF, inkl. Dividenden", "markets": ["US"]},
    {"id": "DAX", "symbol": "^GDAXI", "name": "DAX", "detail": "Performanceindex, inkl. Dividenden", "markets": ["DE"]},
    {"id": "STOXX600", "symbol": "EXSA.DE", "name": "STOXX Europe 600", "detail": "iShares-ETF, inkl. Dividenden", "markets": EUROPE},
    {"id": "FTSE100", "symbol": "ISF.L", "name": "FTSE 100", "detail": "iShares Core FTSE 100 ETF, inkl. Dividenden", "markets": ["GB"]},
    {"id": "TSX60", "symbol": "XIU.TO", "name": "S&P/TSX 60", "detail": "iShares-ETF, inkl. Dividenden", "markets": ["CA"]},
    {"id": "TOPIX", "symbol": "1306.T", "name": "TOPIX", "detail": "NEXT FUNDS TOPIX ETF, inkl. Dividenden", "markets": ["JP"]},
    {"id": "HSI", "symbol": "2800.HK", "name": "Hang Seng", "detail": "Tracker Fund of Hong Kong, inkl. Dividenden", "markets": ["HK"]},
    {"id": "ASX200", "symbol": "STW.AX", "name": "S&P/ASX 200", "detail": "SPDR-ETF, inkl. Dividenden", "markets": ["AU", "NZ"]},
    {"id": "KOSPI200", "symbol": "069500.KS", "name": "KOSPI 200", "detail": "KODEX 200 ETF, inkl. Dividenden", "markets": ["KR"]},
    {"id": "TW50", "symbol": "0050.TW", "name": "Taiwan 50", "detail": "Yuanta-ETF, inkl. Dividenden", "markets": ["TW"]},
    {"id": "NIFTY50", "symbol": "NIFTYBEES.NS", "name": "Nifty 50", "detail": "Nippon India ETF, inkl. Dividenden", "markets": ["IN"]},
    {"id": "CSI300", "symbol": "510300.SS", "name": "CSI 300", "detail": "Huatai-PineBridge ETF, inkl. Dividenden", "markets": ["CN"]},
    {"id": "EM", "symbol": "EEM", "name": "MSCI Emerging Markets", "detail": "iShares-ETF, inkl. Dividenden", "markets": EMERGING},
    {"id": "WORLD", "symbol": "IWDA.AS", "name": "MSCI World", "detail": "iShares Core MSCI World, thesaurierend", "markets": []},
    {"id": "ACWI", "symbol": "ACWI", "name": "MSCI ACWI (Welt)", "detail": "iShares-ETF, inkl. Dividenden", "markets": ["*"]},
]


def _bars_with_adjusted(bars):
    # One bar per date (the last one); indices may come without adjclose,
    # their close already is the index level.
    by_date = {}
    for bar in bars:
        by_date[bar[0]] = bar if bar[5] is not None else (*bar[:5], bar[3])
    return [by_date[d] for d in sorted(by_date)]


def publish_benchmarks(root=ROOT, fetch=fetch_yahoo, now=None):
    root = Path(root)
    root.mkdir(parents=True, exist_ok=True)
    listed = []
    for item in BENCHMARKS:
        entry = dict(item, total_return=True)
        try:
            bars, currency, source = fetch(item["symbol"])
            chart = chart_payload(item["symbol"], _bars_with_adjusted(bars), currency, source)
            if not chart:
                raise RuntimeError("no usable daily series")
            chart["benchmark"] = {k: entry[k] for k in ("id", "name", "detail")}
            path = root / (item["id"] + ".json")
            tmp = path.with_suffix(".tmp")
            tmp.write_text(json.dumps(chart, separators=(",", ":")), encoding="utf-8")
            os.replace(tmp, path)
            entry.update(available=True, currency=currency, asof=chart["asof"],
                         first=chart["points"][0][0], points=len(chart["points"]))
        except Exception as exc:
            entry.update(available=False, error=type(exc).__name__ + ": " + str(exc)[:120])
        listed.append(entry)
    stamp = (now or datetime.now(timezone.utc)).isoformat().replace("+00:00", "Z")
    (root / "index.json").write_text(json.dumps({"version": 1, "generated_at": stamp, "benchmarks": listed},
                                                ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    return {"available": sum(1 for e in listed if e["available"]), "total": len(listed),
            "missing": [e["symbol"] for e in listed if not e["available"]]}
