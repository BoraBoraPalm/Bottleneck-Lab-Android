#!/usr/bin/env python3
"""Bottleneck Lab v4: broad exchange discovery, rotating quotes, transparent coverage,
optional current SEC annual financial facts, explicit source and as-of dates.
Not a global comprehensive screener and not a validated trading strategy.
"""
import csv
import io
import json
import math
import os
import re
import time
import urllib.parse
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta, timezone
from build_snapshot import GROUPS, quote, fetch_news, read_url

PAGES = "https://boraborapalm.github.io/Bottleneck-Lab-Android/snapshot.json"
NASDAQ = "https://www.nasdaqtrader.com/dynamic/SymDir/nasdaqlisted.txt"
OTHER = "https://www.nasdaqtrader.com/dynamic/SymDir/otherlisted.txt"
SEC_TICKERS = "https://www.sec.gov/files/company_tickers.json"
PROBE_PER_RUN = int(os.getenv("BTL_NEW_PER_RUN", "205"))
MAX_WORKERS = int(os.getenv("BTL_WORKERS", "7"))
MAX_AGE = timedelta(days=8)
SECS_PER_FETCH = 0.25
GLOBAL_SEEDS = {
    "Europäische Industrie": "SAP.DE SIE.DE RHM.DE ENR.DE SU.PA AIR.PA SCHN.PA BN.PA ABBN.SW ATCO-A.ST",
    "Globale Halbleiter": "ASML.AS ASM.AS IFX.DE 6501.T 8035.T 6857.T 005930.KS 000660.KS 2330.TW",
    "Internationale Rohstoffe": "BHP.AX RIO.AX FMG.AX GLEN.L",
    "Globale Energie & Infrastruktur": "ORSTED.CO 9501.T 9503.T 600900.SS"
}
CURATED = {symbol: group for group, symbols in GROUPS.items() for symbol in symbols.split()}
CURATED.update({symbol: group for group, symbols in GLOBAL_SEEDS.items() for symbol in symbols.split()})
SKIP_WORDS = re.compile(r"\b(warrants?|right\b|rights\b|preferred|preference shares|depositary shares|units? representing|notes due|exchange.traded|bond|etf|etn|nextshares|closed.end fund|mutual fund|subscription rights|contingent capital|redeemable units|trust certificates)\b",re.I)
SYMBOL = re.compile(r"^[A-Z][A-Z0-9]{0,5}(?:[.-][A-Z0-9]{1,3})?$")
def parse_directory(url, Nasdaq):
    text = read_url(url, timeout=20).decode("utf-8-sig", errors="replace")
    records = list(csv.DictReader(io.StringIO(text), delimiter="|"))
    if not records or len(records)<400:
        raise ValueError("Directory has no valid entries")
    result={}
    for row in records:
        if not row or any((str(k).startswith("File Creation Time")) for k in row.values()):
            continue
        ticker=(row.get("Symbol") if Nasdaq else row.get("ACT Symbol")) or ""
        ticker=ticker.strip()
        name=(row.get("Security Name") or "").strip()
        if row.get("ETF","N")=="Y" or row.get("Test Issue","N")=="Y":continue
        if not ticker or not SYMBOL.fullmatch(ticker) or not name:continue
        if SKIP_WORDS.search(name):continue
        if not Nasdaq and row.get("Exchange") not in ("A","N","V"):continue
        # Yahoo uses '-' for NYSE dotted class tickers.
        yf_ticker=ticker.replace(".","-")
        result[yf_ticker]={"name":name[:130],"exchange":"Nasdaq" if Nasdaq else row.get("Exchange","NYSE")}
    if len(result)<150:
        raise ValueError("Directory filtered to too few common shares")
    return result

def previous_snapshot():
    try:
        j=json.loads(read_url(PAGES+"?cachebust="+str(int(time.time())),timeout=14))
        if not isinstance(j.get("stocks"), list):raise ValueError("No stocks")
        return j
    except Exception as e:
        print("No previous published cache:",str(e)[:100])
        return {}

def discover(previous):
    found={}
    failures=[]
    for source, nasdaq in ((NASDAQ,True),(OTHER,False)):
        try:
            part=parse_directory(source,nasdaq)
            found.update(part)
            print("Discovery",source,len(part))
        except Exception as e:
            failures.append("Discovery "+source+": "+str(e)[:120])
            print("Discovery unavailable",source,str(e)[:140])
    for ticker,group in CURATED.items():
        found.setdefault(ticker,{"name":ticker,"exchange":"Curated global listing"})
        found[ticker]["curated_theme"]=group
    # In case exchange directories fail, keep known older discovered names.
    if len(found)<400:
        for old in previous.get("stocks",[]):
            t=old.get("ticker")
            if t and SYMBOL.fullmatch(t) and t not in found:
                found[t]={"name":old.get("name",t),"exchange":"Previous snapshot"}
    return found,failures

def pick_batch(known, previous):
    now=datetime.now(timezone.utc)
    prior={x["ticker"]:x for x in previous.get("stocks",[]) if isinstance(x,dict) and x.get("ticker") in known}
    # Curated are included every run, preventing disappearing baseline.
    curated=list(CURATED)
    rest=sorted(t for t in known if t not in CURATED)
    # Deterministic 6-hour rotary selector, traverses every eligible exchange symbol
    # in roughly ceil(N / PROBE_PER_RUN) cycles, not the whole market each refresh.
    slot=int(now.timestamp()//21600)
    begin=(slot*PROBE_PER_RUN)%max(1,len(rest))
    candidates=(rest+rest)[begin:begin+min(PROBE_PER_RUN,len(rest))]
    # Revisit previously successful discoveries without flooding APIs.
    prior_ranked=sorted((v for k,v in prior.items() if k not in CURATED),
        key=lambda r:-float(r.get("score") or 0))
    revisit=[v["ticker"] for v in prior_ranked[:25]]
    all_requested=list(dict.fromkeys(curated+candidates+revisit))
    return all_requested,prior

def carry_fresh(previous,known):
    now=datetime.now(timezone.utc)
    carried={}
    for row in previous.get("stocks",[]):
        if not isinstance(row,dict) or row.get("ticker") not in known:continue
        try:
            gen=datetime.fromisoformat(row.get("last_checked_at","").replace("Z","+00:00"))
            if now-gen<MAX_AGE and all(k in row for k in ("close","atr","momentum","score","price_date")):
                carried[row["ticker"]]=dict(row)
        except (ValueError,TypeError):pass
    return carried

def seconds_ago(x):
    try:return (datetime.now(timezone.utc)-datetime.fromisoformat(x.replace("Z","+00:00"))).total_seconds()
    except (ValueError,TypeError,AttributeError):return float("inf")

def financial_sec_lookup(rows, previous):
    """Current selected US companies only; as-filed annual figures, not point-in-time backtest history."""
    limit=int(os.getenv("BTL_SEC_PER_RUN","10"))
    available={}
    try:
        raw=json.loads(read_url(SEC_TICKERS,timeout=18))
        available={entry["ticker"].upper():entry["cik_str"] for entry in raw.values()}
    except Exception as e:
        print("SEC ticker map unavailable",str(e)[:160])
        return 0
    today=datetime.now(timezone.utc)
    # Historical fundamentals carried from prior snapshot for 14 days.
    previous_sec={r.get("ticker"):r.get("fundamentals") for r in previous.get("stocks",[]) if r.get("fundamentals")}
    for row in rows.values():
        f=previous_sec.get(row["ticker"])
        if f and seconds_ago(f.get("retrieved_at"))<14*86400:
            row["fundamentals"]=f
    eligible=sorted((x for x in rows.values() if x.get("ticker") in available and not x.get("fundamentals")
        and x.get("price_date")),key=lambda x:-x.get("score",0))[:limit]
    successful=0
    for row in eligible:
        cik=available[row["ticker"]]
        url=f"https://data.sec.gov/api/xbrl/companyfacts/CIK{int(cik):010d}.json"
        try:
            req_body=read_url(url,timeout=15,max_bytes=18_000_000)
            filing=json.loads(req_body)
            us=filing.get("facts",{}).get("us-gaap",{})
            def annual(tags):
                for name in tags:
                    x=us.get(name,{}).get("units",{}).get("USD",[])
                    values=[v for v in x if v.get("form")=="10-K" and v.get("fp")=="FY" and v.get("fy")
                        and "start" in v and "end" in v and "filed" in v and v.get("val") is not None
                        and 320 <= (datetime.fromisoformat(v["end"])-datetime.fromisoformat(v["start"])).days <= 380]
                    if values:
                        # choose most recent fiscal year-end; as-filed date for transparency
                        best={}
                        for v in values:
                            key=v["end"]
                            if key not in best or v["filed"]<best[key]["filed"]:
                                best[key]=v
                        ordered=sorted(best.values(),key=lambda r:r["end"],reverse=True)
                        if ordered:return ordered
                return []
            rev=annual(("RevenueFromContractWithCustomerExcludingAssessedTax",
                "Revenues","SalesRevenueNet","RevenueFromContractWithCustomerIncludingAssessedTax"))
            cash=annual(("NetCashProvidedByUsedInOperatingActivities",))
            net=annual(("NetIncomeLoss",))
            if not rev and not cash and not net:continue
            f={"source":"SEC EDGAR companyfacts","source_url":url,"retrieved_at":today.isoformat().replace("+00:00","Z")}
            if rev:
                current=rev[0];f["annual_revenue_usd"]=current["val"];f["fiscal_year_end"]=current["end"];f["filed"]=current["filed"]
                if len(rev)>1 and rev[1]["val"]>0:
                    f["annual_revenue_growth_pct"]=round((rev[0]["val"]/rev[1]["val"]-1)*100,2)
            if cash:f["operating_cashflow_usd"]=cash[0]["val"]
            if net:f["net_income_usd"]=net[0]["val"]
            row["fundamentals"]=f;successful+=1
        except Exception as e:
            print("SEC facts unavailable",row["ticker"],str(e)[:100])
        time.sleep(SECS_PER_FETCH)
    return successful

def main():
    start=time.monotonic(); previous=previous_snapshot()
    known,discovery_errors=discover(previous)
    requested,previous_rows=pick_batch(known,previous)
    cache=carry_fresh(previous,known)
    errors=list(discovery_errors)
    done=0
    checked=datetime.now(timezone.utc).isoformat().replace("+00:00","Z")
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool:
        tasks={pool.submit(quote,t,known[t].get("curated_theme","Nicht klassifiziert")):t for t in requested}
        for future in as_completed(tasks):
            ticker=tasks[future]
            try:
                row,error=future.result()
                if row:
                    row["name"]=known[ticker].get("name",ticker)
                    row["exchange"]=known[ticker].get("exchange")
                    row["theme_source"]="Curated" if ticker in CURATED else "Unknown"
                    row["last_checked_at"]=checked
                    cache[ticker]=row
                    done+=1
                elif error:
                    errors.append(error)
            except Exception as e:
                errors.append(ticker+": "+str(e)[:120])
    rows=dict(cache)
    # Require recently valid prices; no stale titles presented as up-to-date.
    rows={k:v for k,v in rows.items() if seconds_ago(v.get("last_checked_at"))<8*86400}
    if len(rows)<15:
        raise SystemExit("Less than 15 valid recent price records; refusing misleading publication.")
    # Conservative liquidity screen for newly discovered US listings; not proof of investment suitability.
    for v in rows.values():
        adv=v.get("avg_dollar_turnover_20d")
        is_us=v.get("currency")=="USD"
        v["eligible_for_ranking"]=bool(v.get("close",0)>=5 and ((is_us and adv is not None and adv>=5000000) or (not is_us and v["ticker"] in CURATED)))
    # Fundamentals collected for a rotating *subset* with proper filing dates.
    sec_count=financial_sec_lookup(rows,previous)
    stocks=sorted(rows.values(),key=lambda r:(not r.get("eligible_for_ranking",False),-r["score"],r["ticker"]))
    bench,bench_error=quote("SPY","Benchmark")
    if bench_error:errors.append("SPY "+bench_error)
    now=datetime.now(timezone.utc)
    newly_discovered=sum(1 for x in stocks if x["ticker"] not in CURATED)
    out={
        "version":4,
        "generated_at":now.isoformat().replace("+00:00","Z"),
        "universe_size":len(known),
        "universe_region":"Primarily US Nasdaq/NYSE listings, plus curated international additions",
        "discovery_sources":[NASDAQ,OTHER],
        "snapshot_coverage_pct":round(len(stocks)/max(1,len(known))*100,1),
        "scanned_tickers":len(stocks),
        "checked_this_run":len(requested),
        "success_this_run":done,
        "new_discovery_count":newly_discovered,
        "fundamental_coverage":sum(1 for x in stocks if x.get("fundamentals")),
        "ranking_eligible_count":sum(1 for x in stocks if x.get("eligible_for_ranking")),
        "ranking_liquidity_screen":"USD shares: price >= $5 and ADV20 >= $5m; curated non-USD: price >= 5 local units, liquidity not USD-verified",
        "model":"Unvalidated 60-day momentum/ATR heuristic; SEC annual fundamental facts are shown separately and NOT used to rank stocks",
        "stocks":stocks,"benchmark":bench,"news":fetch_news(),"errors":errors[:120],
        "sources":["Nasdaq Trader exchange symbol directories","Yahoo Finance unofficial daily chart","Stooq unofficial fallback","SEC EDGAR where available","Google News RSS"]
    }
    os.makedirs("docs",exist_ok=True)
    with open("docs/snapshot.json","w",encoding="utf-8") as f:
        json.dump(out,f,ensure_ascii=False,separators=(",",":"))
    print(f"V4 {len(stocks)}/{len(known)} known quotes, {done}/{len(requested)} this run, "
          f"{sec_count} new SEC fundamentals, {len(errors)} errors, {time.monotonic()-start:.1f}s")
if __name__=="__main__":main()
