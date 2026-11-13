#!/usr/bin/env python3
"""Download all declared sources once and write a SHA-256 manifest. Network step, run in CI."""
from __future__ import annotations
import argparse, hashlib, json, time, urllib.parse, urllib.request
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
import sources as S

HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; BottleneckLabResearch/0.4)",
           "Accept": "application/json,text/csv,application/zip,*/*"}


def get(url: str, tries: int = 4, timeout: int = 90) -> bytes:
    last = None
    for i in range(tries):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=HEADERS), timeout=timeout) as r:
                if r.status != 200:
                    raise RuntimeError(f"HTTP {r.status}")
                return r.read()
        except Exception as e:  # noqa: BLE001 - recorded in the manifest
            last = e
            time.sleep(2 + 4 * i)
    raise RuntimeError(f"{type(last).__name__}: {str(last)[:160]}")


def job(kind: str, name: str, url: str, target: Path, expected: str | None = None) -> dict:
    rec = {"kind": kind, "name": name, "url": url, "file": str(target.name)}
    try:
        raw = get(url)
        rec.update(bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest(),
                   fetched_utc=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), ok=True)
        if expected:
            rec["matches_archived_2026_11_01_hash"] = rec["sha256"] == expected
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(raw)
    except Exception as e:  # noqa: BLE001
        rec.update(ok=False, error=str(e)[:200])
    return rec


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    out = Path(ap.parse_args().out)
    jobs = []
    for f in S.FRENCH_FILES:
        jobs.append(("french", f, S.FRENCH_BASE + urllib.parse.quote(f) + "_CSV.zip", out / "french" / (f + "_CSV.zip"), None))
    for f, (path, sha) in S.OSAP_FILES.items():
        jobs.append(("osap", f, S.OSAP_BASE + path, out / "osap" / f, sha))
    now = int(time.time())
    for s in S.YAHOO_SYMBOLS:
        url = (f"https://query1.finance.yahoo.com/v8/finance/chart/{urllib.parse.quote(s, safe='')}"
               f"?period1=0&period2={now}&interval=1d&events=div%2Csplits")
        jobs.append(("yahoo", s, url, out / "yahoo" / (s + ".json"), None))
    with ThreadPoolExecutor(max_workers=3) as pool:
        records = list(pool.map(lambda j: job(*j), jobs))
    failed = [r for r in records if not r["ok"]]
    manifest = {"created_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                "osap_commit": S.OSAP_SHA, "files": records,
                "failed": [f"{r['kind']}:{r['name']}: {r['error']}" for r in failed]}
    (out / "manifest.json").write_text(json.dumps(manifest, indent=1))
    print(f"{len(records) - len(failed)} of {len(records)} sources stored; {len(failed)} failed")
    for line in manifest["failed"]:
        print("FAILED", line)
    core_failed = [r for r in failed if r["kind"] != "yahoo"]
    if core_failed:
        raise SystemExit("Core source missing: " + ", ".join(r["name"] for r in core_failed))


if __name__ == "__main__":
    main()
