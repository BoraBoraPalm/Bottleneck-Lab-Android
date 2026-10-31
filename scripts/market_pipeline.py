#!/usr/bin/env python3
"""Bottleneck Lab: one worldwide price-only screening feed.

No scores fitted on historical winners, no pseudo-optimal ATR orders, no
US-only fundamentals presented as global. The only ranked metric is observed
12–2-month price momentum. This is a RESEARCH screen, not a return forecast.
"""
import csv
import io
import json
import math
import os
import re
import time
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date, datetime, timedelta, timezone

from build_snapshot import CURATED, read_url, quote
from fx_eur import latest_eur_rates, add_eur_prices
from global_universe import discover_global, grouped_batch, SOURCE
from tr_at_universe import apply_tr_filter

PAGES="https://boraborapalm.github.io/Bottleneck-Lab-Android/snapshot.json"
NASDAQ="https://www.nasdaqtrader.com/dynamic/SymDir/nasdaqlisted.txt"
OTHER="https://www.nasdaqtrader.com/dynamic/SymDir/otherlisted.txt"
PROBE=int(os.getenv("BTL_NEW_PER_RUN","205"))
WORKERS=int(os.getenv("BTL_WORKERS","7"))
MAX_AGE=timedelta(days=8)
DATE_FMT="%Y-%m-%d"
SYMBOL=re.compile(r"^[A-Z][A-Z0-9]{0,5}(?:[.-][A-Z0-9]{1,3})?$")
SKIP=re.compile(r"\b(warrants?|rights?|preferred|depositary shares|units? representing|notes due|exchange.traded|bond|etf|etn|closed.end fund|mutual fund|subscription rights)\b",re.I)
SEEDS={
  "Europa":"SAP.DE SIE.DE ASML.AS ASM.AS IFX.DE RHM.DE AIR.PA OR.PA MC.PA NESN.SW NOVN.SW ROG.SW NOVO-B.CO AZN.L ULVR.L GLEN.L",
  "Asien":"7203.T 6758.T 9984.T 6857.T 0700.HK 9988.HK 3690.HK 600519.SS 601318.SS 300750.SZ RELIANCE.NS TCS.NS INFY.NS 005930.KS 000660.KS 2330.TW",
  "Nordamerika":"SHOP.TO CNQ.TO CP.TO CSU.TO TD.TO RY.TO",
  "Lateinamerika":"VALE3.SA PETR4.SA ITUB4.SA WMT.MX",
  "Ozeanien":"CBA.AX CSL.AX WES.AX BHP.AX RIO.AX",
  "Afrika":"NPN.JO",
  "Naher Osten":"D05.SI"
}
SEED_NAMES={s:r for r,syms in SEEDS.items() for s in syms.split()}
CURATED_SYMBOLS=set(CURATED)|set(SEED_NAMES)
SUFFIX_REGION={
 ".DE":"Europa",".F":"Europa",".PA":"Europa",".MI":"Europa",".AS":"Europa",".SW":"Europa",".CO":"Europa",".ST":"Europa",".L":"Europa",
 ".T":"Asien",".TWO":"Asien",".KS":"Asien",".TW":"Asien",".HK":"Asien",".SS":"Asien",".SZ":"Asien",".NS":"Asien",".BO":"Asien",".SI":"Asien",
 ".TO":"Nordamerika",".SA":"Lateinamerika",".MX":"Lateinamerika",".AX":"Ozeanien",".JO":"Afrika"
}

def seconds_old(ts):
    try:return (datetime.now(timezone.utc)-datetime.fromisoformat(ts.replace("Z","+00:00"))).total_seconds()
    except (TypeError,ValueError,AttributeError):return float("inf")

def previous_snapshot():
    try:
        x=json.loads(read_url(PAGES+"?refresh="+str(int(time.time())),timeout=16,max_bytes=8000000))
        if not isinstance(x.get("stocks"),list):raise ValueError("Stocks not in snapshot")
        return x
    except Exception as exc:
        print("Previous cache unavailable",str(exc)[:130],flush=True)
        return {}

def parse_directory(url,nasdaq):
    text=read_url(url,timeout=20).decode("utf-8-sig",errors="replace")
    result={}
    for row in csv.DictReader(io.StringIO(text),delimiter="|"):
        t=((row.get("Symbol") if nasdaq else row.get("ACT Symbol")) or "").strip()
        n=(row.get("Security Name") or "").strip()
        if not n or not SYMBOL.fullmatch(t) or SKIP.search(n):continue
        if row.get("ETF")=="Y" or row.get("Test Issue")=="Y":continue
        if not nasdaq and row.get("Exchange") not in {"A","N","V"}:continue
        yf=t.replace(".","-")
        result[yf]={"name":n[:130],"exchange":"NASDAQ" if nasdaq else "US "+row.get("Exchange","NYSE"),
                    "region":"Nordamerika","country_code":"US"}
    if len(result)<150:raise ValueError("Fewer than 150 US symbols")
    return result

def discover(old):
    known={}
    details={"status":"unavailable","mapped_symbol_count":0,"listed_stocks":0,"source":SOURCE}
    errors=[]
    try:
        global_rows,details=discover_global()
        known.update(global_rows)
        details["status"]="ok"
    except Exception as exc:
        errors.append("Global directory unavailable: "+str(exc)[:160])
    for url,kind in ((NASDAQ,True),(OTHER,False)):
        try:
            for ticker,meta in parse_directory(url,kind).items():
                if ticker in known:known[ticker].update({"name":meta["name"],"exchange":meta["exchange"]})
                else:known[ticker]=meta
        except Exception as exc:
            errors.append("US directory unavailable: "+str(exc)[:140])
    for ticker in CURATED_SYMBOLS:
        region=SEED_NAMES.get(ticker)
        if region is None:
            region=next((reg for suffix,reg in SUFFIX_REGION.items() if ticker.endswith(suffix)),"Nordamerika")
        if ticker not in known:
            known[ticker]={"name":ticker,"exchange":"Curated","region":region}
        known[ticker].setdefault("region",region)
    if not known and old:
        for x in old.get("stocks",[]):
            t=x.get("ticker")
            if isinstance(t,str):
                known[t]={"name":x.get("name",t),"exchange":x.get("exchange","Older snapshot"),
                          "region":x.get("region","Unbekannt")}
    if len(known)<30:raise RuntimeError("No usable stock universe")
    return known,details,errors

CACHE_FIELDS=(
  "ticker","close","currency","price_date","source","bars_count","momentum_12_2",
  "avg_dollar_turnover_20d","avg_local_turnover_20d","last_checked_at"
)
def cached_quotes(old,known):
    existing={}
    for x in old.get("stocks",[]):
        if not isinstance(x,dict) or x.get("ticker") not in known:continue
        if seconds_old(x.get("last_checked_at"))>=MAX_AGE.total_seconds():continue
        if not all(x.get(k) is not None for k in ("close","currency","price_date","last_checked_at")):continue
        if not isinstance(x.get("avg_local_turnover_20d"),(int,float)):continue
        try:
            last=datetime.strptime(x["price_date"],DATE_FMT).replace(tzinfo=timezone.utc)
            if (datetime.now(timezone.utc)-last)>timedelta(days=11):continue
        except (TypeError,ValueError):continue
        existing[x["ticker"]]={k:x[k] for k in CACHE_FIELDS if k in x}
    return existing

def requested_batch(known,cache):
    slot=int(datetime.now(timezone.utc).timestamp()//21600)
    core=grouped_batch(known,CURATED_SYMBOLS,slot,PROBE)
    # Repeat a small portion of recently scanned top momentum names only for
    # fresh dates, not because any evidence proves an alpha forecast.
    extra=sorted((s for s in cache.values() if s.get("momentum_12_2") is not None),
                 key=lambda x:-float(x["momentum_12_2"]))[:15]
    return list(dict.fromkeys(core+[x["ticker"] for x in extra]))

def enrich(meta,raw,ticker):
    row=dict(raw)
    details=meta[ticker]
    row["name"]=details.get("name",ticker)
    row["exchange"]=details.get("exchange","unknown")
    row["region"]=details.get("region") or "Unbekannt"
    for attr in ("country","country_code","stock_sector","reference_isin","listing_key"):
        if details.get(attr):row[attr]=details[attr]
    return row

def group_highlights(stocks,count=20,region_cap=4):
    eligible=sorted((x for x in stocks if x.get("eligible_global_ranking")),
         key=lambda v:(-v["momentum_12_2"],v["ticker"]))
    tally=Counter()
    result=[]
    for stock in eligible:
        region=stock.get("region") or "Unbekannt"
        if tally[region]>=region_cap:continue
        tally[region]+=1
        result.append(stock["ticker"])
        if len(result)>=count:break
    return result

def main():
    started=time.monotonic()
    old=previous_snapshot()
    known,global_details,errors=discover(old)
    cache=cached_quotes(old,known)
    targets=requested_batch(known,cache)
    checked=datetime.now(timezone.utc).isoformat().replace("+00:00","Z")
    success=0
    with ThreadPoolExecutor(max_workers=WORKERS) as pool:
        futs={pool.submit(quote,t,SEED_NAMES.get(t) or CURATED.get(t) or "Global"):t for t in targets}
        for fut in as_completed(futs):
            t=futs[fut]
            try:r,error=fut.result()
            except Exception as ex:r,error=None,str(ex)
            if r:
                r["last_checked_at"]=checked
                cache[t]=r
                success+=1
            elif error and len(errors)<30:errors.append(t+": "+str(error)[:135])
    if len(cache)<25:raise RuntimeError("Fewer than 25 valid quotes; refusing publication")
    fx=latest_eur_rates()
    stocks=[enrich(known,v,t) for t,v in cache.items()]
    n_fx,missing=add_eur_prices(stocks,fx)
    if n_fx<max(20,int(.80*len(stocks))):
        raise RuntimeError("EUR FX coverage below 80%; last live website retained")
    now=datetime.now(timezone.utc)
    for s in stocks:
        val=s.get("avg_local_turnover_20d")
        cur=s.get("eur_per_unit")
        momentum=s.get("momentum_12_2")
        eur=s.get("reference_close_eur")
        valid_fx=all(isinstance(v,(int,float)) and math.isfinite(v) and v>0 for v in (val,cur,eur))
        s["avg_turnover_20d_eur"]=round(val*cur,2) if valid_fx else None
        try:dated=date.fromisoformat(s.get("price_date",""))
        except (ValueError,TypeError):dated=None
        recent=bool(dated and 0<=(now.date()-dated).days<=7)
        s["eligible_global_ranking"]=bool(valid_fx and recent and eur>=2
            and s["avg_turnover_20d_eur"]>=2000000
            and isinstance(momentum,(int,float)) and math.isfinite(momentum))
    tr=apply_tr_filter(stocks)
    stocks.sort(key=lambda s:(not s["eligible_global_ranking"],-(s.get("momentum_12_2") or -999),s["ticker"]))
    counts=Counter(s.get("region") or "Unbekannt" for s in known.values())
    have=Counter(s.get("region") or "Unbekannt" for s in stocks)
    eligible=Counter(s.get("region") or "Unbekannt" for s in stocks if s["eligible_global_ranking"])
    output={
        "version":6,
        "generated_at":now.isoformat().replace("+00:00","Z"),
        "display_currency":"EUR",
        "method":"Worldwide 12–2-month historical momentum watchlist; not a validated investment recommendation",
        "caveat":"Global discovery is incomplete; no evidence of reliable future outperformance.",
        "universe_size":len(known),
        "scanned_tickers":len(stocks),
        "checked_this_run":len(targets),
        "success_this_run":success,
        "global_discovery":global_details,
        "regions_universe":dict(counts),
        "regions_quoted":dict(have),
        "regions_eligible":dict(eligible),
        "eligible_count":sum(s["eligible_global_ranking"] for s in stocks),
        "highlights":group_highlights(stocks),
        "fx_missing_currencies":missing,
        "tr_at_verification":tr,
        "stocks":stocks,
        "errors":errors[:25],
        "sources":[SOURCE,NASDAQ,OTHER,"Yahoo Finance daily charts","Stooq US daily CSV",
                   "Frankfurter reference FX","Trade Republic AT official instrument list"]
    }
    os.makedirs("docs",exist_ok=True)
    with open("docs/snapshot.json","w",encoding="utf-8") as f:
        json.dump(output,f,ensure_ascii=False,separators=(",",":"))
    print("WORLD_READY="+json.dumps({
        "known":len(known),"quotes":len(stocks),"eligible":output["eligible_count"],
        "highlights":len(output["highlights"]),"regions_quoted":dict(have),
        "TR_verified":tr["verified"],"errors":len(errors),
        "duration_s":round(time.monotonic()-started,1)
    }),flush=True)
if __name__=="__main__":main()
