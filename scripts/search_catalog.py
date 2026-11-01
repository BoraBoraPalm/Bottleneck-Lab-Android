"""Public listing metadata for independent search; no screening or quote claims."""
import json
from datetime import datetime, timezone
from pathlib import Path

FIELDS = ("name", "exchange", "country", "country_code", "region",
          "reference_isin", "listing_key", "stock_sector")


def catalog_payload(known):
    rows = []
    for ticker, meta in sorted(known.items()):
        if not isinstance(ticker, str) or not ticker or not isinstance(meta, dict):
            continue
        row = {"ticker": ticker}
        for key in FIELDS:
            value = meta.get(key)
            if isinstance(value, str) and value.strip():
                row[key] = value.strip()[:160]
        row.setdefault("name", ticker)
        rows.append(row)
    return {"version": 1, "generated_at": datetime.now(timezone.utc).isoformat(),
            "coverage": "Available listing directory; not a guarantee of price data or broker availability",
            "stocks": rows}


def write_catalog(known, path="docs/search-index.json"):
    payload = catalog_payload(known)
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_suffix(".tmp")
    temporary.write_text(json.dumps(payload, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    temporary.replace(target)
    return len(payload["stocks"])
