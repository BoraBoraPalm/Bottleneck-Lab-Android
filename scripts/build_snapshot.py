#!/usr/bin/env python3
"""Generate source-labelled, verifiable daily closing-price snapshot for GitHub Pages.
No trading, no historical fundamentals, no AI bottleneck predictions.
Uses unofficial providers; missing symbols stay missing.
"""
import csv
import io
import json
import math
import os
import time
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta, timezone

GROUPS = {
    "Stromnetze": "NEX.PA GEV HUBB ETN NVT ABBN.SW PWR EMR PH WCC POWL GNRC ROK PRY.MI",
    "Rechenzentren": "VRT EQIX DLR ANET DELL SMCI HPE CRDO GLW CSCO AVGO NVDA AMD",
    "Halbleiter": "MU AMAT ASML LRCX KLAC TSM QCOM ADI MPWR ONTO TER SNDK",
    "Energie": "CEG NRG VST NEE DUK SO EXC EIX BE FSLR OKLO CCJ BWXT",
    "Rohstoffe": "FCX SCCO BHP RIO TECK AA MP ALB LAC UUUU",
    "Wasser": "XYL AWK WTRG ECL IEX PNR WTS BMI AOS",
    "Verteidigung": "RTX LMT NOC GD HII LHX",
    "Automation & Logistik": "CAT DE HON ZBRA SYM GXO UPS PANW CRWD FTNT AXON"
}
UNIVERSE = {s: theme for theme, symbols in GROUPS.items() for s in symbols.split()}
# Yahoo may limit requests. Stooq (where coverage exists) is a fallback for daily OHLC.
HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; BottleneckLabResearch/0.3)",
           "Accept": "application/json,text/csv,application/xml,text/xml,*/*"}
def read_url(url, timeout=12, max_bytes=3_000_000):
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=timeout) as response:
        if response.status != 200:
            raise RuntimeError("HTTP " + str(response.status))
        body=response.read(max_bytes+1)
        if len(body)>max_bytes:
            raise RuntimeError("Response too large")
    return body

def fetch_yahoo(symbol):
    last = ""
    for host in ("query1.finance.yahoo.com", "query2.finance.yahoo.com"):
        try:
            s=urllib.parse.quote(symbol, safe="")
            url=f"https://{host}/v8/finance/chart/{s}?range=1y&interval=1d"
            result=json.loads(read_url(url))
            chart=result["chart"]
            if chart.get("error"):
                raise RuntimeError(str(chart["error"]))
            r=chart["result"][0]
            quote=r["indicators"]["quote"][0]
            ts=r["timestamp"]
            bars=[]
            for i,epoch in enumerate(ts):
                try:
                    c=float(quote["close"][i]); h=float(quote["high"][i]); l=float(quote["low"][i])
                    if all(math.isfinite(k) and k>0 for k in (c,h,l)):
                        bars.append((datetime.fromtimestamp(epoch,timezone.utc).strftime("%Y-%m-%d"),h,l,c,float(quote.get("volume",[None]*len(ts))[i] or 0)))
                except (TypeError,ValueError,IndexError,KeyError):
                    continue
            return bars, r.get("meta",{}).get("currency","USD"),"Yahoo Finance"
        except Exception as e:
            last=type(e).__name__+": "+str(e)[:130]
    raise RuntimeError(last)

def fetch_stooq(symbol):
    if symbol.endswith(".PA") or symbol.endswith(".MI") or symbol.endswith(".SW"):
        raise RuntimeError("Stooq fallback unavailable for this exchange")
    stooq_symbol=symbol.lower()+".us"
    today=datetime.now(timezone.utc).date()
    beg=today-timedelta(days=395)
    params=urllib.parse.urlencode({"s":stooq_symbol,"d1":beg.strftime("%Y%m%d"),"d2":today.strftime("%Y%m%d"),"i":"d"})
    url="https://stooq.com/q/d/l/?"+params
    content=read_url(url).decode("utf-8-sig",errors="replace")
    bars=[]
    for row in csv.DictReader(io.StringIO(content)):
        try:
            d=row["Date"]; h=float(row["High"]); l=float(row["Low"]); c=float(row["Close"])
            if c>0 and h>0 and l>0 and all(math.isfinite(v) for v in (h,l,c)):
                bars.append((d,h,l,c,float(row.get("Volume") or 0)))
        except (TypeError,ValueError,KeyError):
            continue
    return bars,"USD","Stooq (daily CSV)"

def quote(symbol,theme):
    errors=[]
    for load in (fetch_yahoo,fetch_stooq):
        try:
            bars,currency,source=load(symbol)
            bars=sorted(set(bars),key=lambda x:x[0])
            if len(bars)<65:
                raise RuntimeError("Less than 65 daily bars: "+str(len(bars)))
            dates=[v[0] for v in bars]
            last_date=datetime.strptime(dates[-1],"%Y-%m-%d").replace(tzinfo=timezone.utc)
            if (datetime.now(timezone.utc)-last_date).days>11:
                raise RuntimeError("Stale quote from "+dates[-1])
            closes=[x[3] for x in bars]
            trs=[max(bars[i][1]-bars[i][2], abs(bars[i][1]-closes[i-1]), abs(bars[i][2]-closes[i-1])) for i in range(1,len(bars))]
            atr=sum(trs[-14:])/14
            price=closes[-1];mom=price/closes[-61]-1
            vol=atr/price
            # Heuristic price-only score, NOT a validated forward-return estimator.
            score=round(max(0,min(100,50+180*mom-80*vol)),1)
            turnovers=[b[3]*b[4] for b in bars[-20:] if len(b)>4 and b[4]>0 and math.isfinite(b[4])]
            avg_turnover=round(sum(turnovers)/len(turnovers),0) if len(turnovers)>=12 and currency=="USD" else None
            return {"ticker":symbol,"theme":theme,"close":round(price,4),"price_date":dates[-1],
                    "currency":currency,"source":source,"atr":round(atr,4),"momentum":round(mom,6),
                    "score":score,"avg_dollar_turnover_20d":avg_turnover},None
        except Exception as e:
            errors.append(load.__name__+": "+str(e)[:140])
    return None,symbol+": "+"; ".join(errors)

TOPICS = [
  ("Stromnetze","power transformer shortages grid connection lead time"),
  ("Rechenzentren","AI datacenter power supply cooling infrastructure"),
  ("Halbleiter","HBM memory advanced packaging bottleneck"),
  ("Energie","electricity grid power generation capacity data center"),
  ("Rohstoffe","copper supply deficit mining smelter"),
  ("Wasser","water treatment infrastructure shortages"),
  ("Verteidigung","defense manufacturing supply chain bottleneck")
]
def fetch_news():
    seen=set();out=[]
    for theme,query in TOPICS:
        try:
            url="https://news.google.com/rss/search?"+urllib.parse.urlencode({"q":query+" when:7d","hl":"en-US","gl":"US","ceid":"US:en"})
            root=ET.fromstring(read_url(url,timeout=13))
            for item in root.findall("./channel/item")[:3]:
                title=(item.findtext("title") or "").strip()
                link=(item.findtext("link") or "").strip()
                when=(item.findtext("pubDate") or "").strip()
                if not title or not link.startswith("https://") or title in seen:continue
                seen.add(title)
                out.append({"topic":theme,"title":title[:250],"url":link,"published":when[:55]})
        except Exception as e:
            print("RSS source unavailable:",theme,type(e).__name__)
    return out

def main():
    t0=time.monotonic()
    results=[];errors=[]
    with ThreadPoolExecutor(max_workers=5) as pool:
        tasks={pool.submit(quote,t,theme):t for t,theme in UNIVERSE.items()}
        for f in as_completed(tasks):
            try:r,e=f.result()
            except Exception as ex:r,e=None,str(ex)
            if r:results.append(r)
            if e:errors.append(e)
    results.sort(key=lambda x:(-x["score"],x["ticker"]))
    bench,b_err=quote("SPY","Benchmark")
    if b_err:errors.append("SPY "+b_err)
    if not results:
        raise SystemExit("No valid recent daily stock quotes — refusing to publish an empty live snapshot.")
    out={
      "generated_at":datetime.now(timezone.utc).isoformat().replace("+00:00","Z"),
      "universe_size":len(UNIVERSE),
      "model":"Heuristic momentum/ATR score; not a fundamental, shortage or validated profitability forecast",
      "stocks":results,
      "benchmark":bench,
      "news":fetch_news(),
      "errors":errors,
      "sources":["Yahoo Finance unofficial chart API","Stooq daily CSV fallback","Google News RSS"]
    }
    os.makedirs("docs",exist_ok=True)
    with open("docs/snapshot.json","w",encoding="utf-8") as f:
        json.dump(out,f,ensure_ascii=False,separators=(",",":"))
    print(f"Snapshot: {len(results)}/{len(UNIVERSE)} stocks, {len(errors)} errors, {len(out['news'])} news, {time.monotonic()-t0:.1f}s")
if __name__=="__main__":main()
