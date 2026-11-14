#!/usr/bin/env python3
"""Exploratory supplement, declared after the main results were seen (see protocol).

Loads what a direct test of the app's own stock rules needs and stores it in compact form:
historical S&P 500 membership, daily prices of all members since 2010 (reduced to month-end
signals), annual SEC XBRL frames, and real emerging-market factor funds. Network step for CI.
"""
from __future__ import annotations
import argparse, hashlib, io, json, math, sys, time, urllib.parse, urllib.request
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
import numpy as np
import pandas as pd
sys.path.insert(0, str(Path(__file__).resolve().parent))
import lib  # noqa: E402

BROWSER = {"User-Agent": "Mozilla/5.0 (compatible; BottleneckLabResearch/0.4)", "Accept": "*/*"}
SEC = {"User-Agent": "Bottleneck Lab nonprofit academic research (contact: bottleneck-lab@github.com)", "Accept": "application/json",
       "Accept-Encoding": "identity"}   # same headers as the app pipeline (scripts/sander_fundamentals.py)
MEMBERS_URL = "https://raw.githubusercontent.com/fja05680/sp500/master/S%26P%20500%20Historical%20Components%20%26%20Changes%20(Updated).csv"
# Old index ticker -> today's ticker of the same company (best effort; unlisted names stay missing).
ALIAS = {"FB": "META", "ANTM": "ELV", "FISV": "FI", "ABC": "COR", "PKI": "RVTY", "WLTW": "WTW", "BLL": "BALL", "CTL": "LUMN",
         "HRS": "LHX", "TMK": "GL", "KORS": "CPRI", "PCLN": "BKNG", "LUK": "JEF", "COG": "CTRA", "JEC": "J", "HCN": "WELL",
         "CBG": "CBRE", "BHGE": "BKR", "UTX": "RTX", "LB": "BBWI", "ADS": "BFH", "RE": "EG", "FLT": "CPAY", "PEAK": "DOC",
         "CDAY": "DAY", "DISCA": "WBD", "VIAC": "PARA", "SYMC": "GEN", "NLOK": "GEN", "WYN": "TNL", "HCP": "DOC", "CBS": "PARA",
         "KFT": "MDLZ", "COH": "TPR", "DLPH": "APTV", "BBT": "TFC", "MYL": "VTRS", "FBHS": "FBIN", "GPS": "GAP", "HFC": "DINO"}
CIK_MIRROR = "https://raw.githubusercontent.com/jadchaar/sec-cik-mapper/main/mappings/stocks/ticker_to_cik.json"
EM_FUNDS = ["VEIEX", "EEM", "DFEVX", "DFEMX", "DFCEX", "EEMO", "EMGF", "FNDE", "PXH", "DEM", "DGS", "EDIV", "EEMV", "AVEM",
            "AVES", "QEMM", "TLTE", "JPEM", "GEM", "EUNM.DE", "IS3N.DE", "5MVL.DE", "EUNZ.DE", "PSRM.DE", "WTEI.DE"]
DURATION = ["NetIncomeLoss", "NetCashProvidedByUsedInOperatingActivities", "Revenues",
            "RevenueFromContractWithCustomerExcludingAssessedTax", "RevenueFromContractWithCustomerIncludingAssessedTax",
            "SalesRevenueNet", "GrossProfit"]
YEARS = range(2009, 2026)


def get(url: str, headers: dict, tries: int = 3, timeout: int = 60) -> bytes:
    last = None
    for i in range(tries):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=timeout) as r:
                return r.read()
        except Exception as e:  # noqa: BLE001
            last = e
            if getattr(e, "code", None) in (403, 404):
                break
            time.sleep(1.5 + 3 * i)
    raise RuntimeError(f"{type(last).__name__}: {str(last)[:120]}")


def yahoo_series(sym: str, start: int) -> pd.Series:
    url = (f"https://query1.finance.yahoo.com/v8/finance/chart/{urllib.parse.quote(sym, safe='')}"
           f"?period1={start}&period2={int(time.time())}&interval=1d&events=div%2Csplits")
    r = json.loads(get(url, BROWSER))["chart"]["result"][0]
    idx = pd.to_datetime(r["timestamp"], unit="s").normalize()
    s = pd.Series(r["indicators"]["adjclose"][0]["adjclose"], index=idx, dtype=float).dropna()
    s = s[s > 0]
    return s[~s.index.duplicated(keep="last")].sort_index()


def stock_fields(px: pd.Series) -> pd.DataFrame:
    """Month-end close and the app's price signals as of that close."""
    lr = np.log(px).diff()
    f = pd.DataFrame({"px": px, "mom": px.shift(21) / px.shift(252) - 1,
                      "vol": lr.rolling(252).std() * math.sqrt(252),
                      "sma": px / px.rolling(200).mean() - 1, "dd": px / px.rolling(252).max() - 1})
    m = f.groupby(f.index.to_period("M")).tail(1)
    m.index = m.index.to_period("M")
    return m


def main() -> None:
    """Each part is stored once; a rerun only loads what is still missing (the SEC sometimes refuses cloud hosts)."""
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    out = Path(ap.parse_args().out)
    out.mkdir(parents=True, exist_ok=True)
    mf = out / "manifest.json"
    man = json.loads(mf.read_text()) if mf.is_file() else {"sources": []}
    man["updated_utc"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    def note(name, url, raw):
        man["sources"].append({"name": name, "url": url, "bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest(),
                               "fetched_utc": man["updated_utc"]})

    # 1) membership and prices -> month-end panels
    if not (out / "stock_px.parquet").is_file():
        raw = get(MEMBERS_URL, BROWSER)
        note("sp500_membership", MEMBERS_URL, raw)
        mem = pd.read_csv(io.BytesIO(raw))
        mem = mem[mem.date >= "2009-06-01"]
        mem.to_csv(out / "sp500_membership.csv.gz", index=False)
        tickers = sorted({t for row in mem.tickers for t in row.split(",")})
        start = int(datetime(2008, 6, 1, tzinfo=timezone.utc).timestamp())

        def load(t: str):
            try:
                px = yahoo_series(ALIAS.get(t, t).replace(".", "-"), start)
                if len(px) < 260:
                    return t, None, {"error": "fewer than 260 closes"}
                d = px.pct_change().abs()
                return t, stock_fields(px), {"first": str(px.index[0].date()), "last": str(px.index[-1].date()), "days": int(len(px)),
                                             "max_abs_daily_move": float(d.max()), "yahoo": ALIAS.get(t, t).replace(".", "-")}
            except Exception as e:  # noqa: BLE001
                return t, None, {"error": str(e)[:100]}

        with ThreadPoolExecutor(max_workers=4) as pool:
            res = list(pool.map(load, tickers))
        ok = {t: f for t, f, _ in res if f is not None}
        for field in ("px", "mom", "vol", "sma", "dd"):
            pd.DataFrame({t: f[field] for t, f in ok.items()}).sort_index().astype("float32").to_parquet(out / f"stock_{field}.parquet", compression="zstd")
        (out / "stock_audit.json").write_text(json.dumps({t: a for t, _, a in res}, indent=0))
        man["stocks"] = {"index_tickers_since_2009": len(tickers), "with_prices": len(ok)}
    # 2) emerging-market funds
    if not (out / "em_monthly_returns.csv").is_file():
        cols, em_audit = {}, {}
        for s in EM_FUNDS:
            try:
                px = yahoo_series(s, 0)
                d = px.pct_change().dropna()
                cols[s] = lib.to_monthly(px)
                em_audit[s] = {"first": str(px.index[0].date()), "last": str(px.index[-1].date()), "days": int(len(px)),
                               "moves_over_12pct": [[str(a.date()), round(float(b), 4)] for a, b in d[d.abs() > 0.12].items()][:60]}
            except Exception as e:  # noqa: BLE001
                em_audit[s] = {"error": str(e)[:100]}
        pd.DataFrame(cols).sort_index().to_csv(out / "em_monthly_returns.csv", float_format="%.8f")
        (out / "em_audit.json").write_text(json.dumps(em_audit, indent=1))
        man["em_funds"] = {s: a.get("first", a.get("error")) for s, a in em_audit.items()}
    # 3) SEC annual frames for the members
    if not (out / "sec_frames.parquet").is_file():
        try:
            names = list(pd.read_parquet(out / "stock_px.parquet").columns)
            try:   # www.sec.gov refuses GitHub-hosted runners; a public mirror of the same list is tried first
                raw = get(CIK_MIRROR, BROWSER)
                note("ticker_to_cik_mirror", CIK_MIRROR, raw)
                cik_of = {k.upper(): int(v) for k, v in json.loads(raw).items()}
            except Exception:  # noqa: BLE001
                raw = get("https://www.sec.gov/files/company_tickers.json", SEC)
                note("sec_company_tickers", "https://www.sec.gov/files/company_tickers.json", raw)
                cik_of = {v["ticker"].upper(): int(v["cik_str"]) for v in json.loads(raw).values()}
            cik_by_ticker = {t: cik_of[ALIAS.get(t, t).replace(".", "-")] for t in names if ALIAS.get(t, t).replace(".", "-") in cik_of}
            wanted = set(cik_by_ticker.values())
            rows, failed = [], []
            jobs = [(c, f"CY{y}") for y in YEARS for c in DURATION] + [("Assets", f"CY{y}Q{q}I") for y in YEARS for q in (1, 2, 3, 4)]
            for concept, frame in jobs:
                url = f"https://data.sec.gov/api/xbrl/frames/us-gaap/{concept}/USD/{frame}.json"
                try:
                    for d in json.loads(get(url, SEC))["data"]:
                        if d["cik"] in wanted:
                            rows.append((concept, frame, d["cik"], d.get("start"), d["end"], float(d["val"])))
                except Exception as e:  # noqa: BLE001
                    failed.append(f"{concept}/{frame}: {str(e)[:60]}")
                    if len(failed) >= 4 and not rows:
                        raise RuntimeError("data.sec.gov refuses this host: " + failed[0])
                time.sleep(0.15)
            man["sec"] = {"frames_requested": len(jobs), "frames_failed": failed[:40], "frames_failed_count": len(failed),
                          "rows": len(rows), "members_with_cik": len(cik_by_ticker)}
            if len(failed) > len(jobs) / 4:
                raise RuntimeError(f"{len(failed)} of {len(jobs)} frames failed")
            pd.DataFrame(rows, columns=["concept", "frame", "cik", "start", "end", "val"]).to_parquet(out / "sec_frames.parquet", compression="zstd")
            (out / "cik_map.json").write_text(json.dumps(cik_by_ticker))
        except Exception as e:  # noqa: BLE001 - recorded; the next run retries this part only
            man["sec_error"] = str(e)[:200]
    mf.write_text(json.dumps(man, indent=1))
    print(json.dumps({k: man.get(k) for k in ("stocks", "em_funds", "sec", "sec_error")}, indent=1)[:2500])


if __name__ == "__main__":
    main()
