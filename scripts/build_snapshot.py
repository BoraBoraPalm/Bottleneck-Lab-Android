#!/usr/bin/env python3
"""Minimal OHLC and 12–2 momentum source. No old ATR buy/stop or ranking."""
import csv
import io
import json
import math
import urllib.error
import urllib.parse
import urllib.request



from datetime import datetime, timedelta, timezone

CURATED_THEMES = {
    "Stromnetze": "NEX.PA GEV HUBB ETN NVT ABBN.SW PWR EMR PH WCC POWL GNRC ROK PRY.MI",
    "Rechenzentren": "VRT EQIX DLR ANET DELL SMCI HPE CRDO GLW CSCO AVGO NVDA AMD",
    "Halbleiter": "MU AMAT ASML LRCX KLAC TSM QCOM ADI MPWR ONTO TER SNDK",
    "Energie": "CEG NRG VST NEE DUK SO EXC EIX BE FSLR OKLO CCJ BWXT",
    "Rohstoffe": "FCX SCCO BHP RIO TECK AA MP ALB LAC UUUU",
    "Wasser": "XYL AWK WTRG ECL IEX PNR WTS BMI AOS",
    "Verteidigung": "RTX LMT NOC GD HII LHX",
    "Automation & Logistik": "CAT DE HON ZBRA SYM GXO UPS PANW CRWD FTNT AXON"
}
CURATED = {s: theme for theme, symbols in CURATED_THEMES.items() for s in symbols.split()}
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
            url=f"https://{host}/v8/finance/chart/{s}?range=2y&interval=1d"
            result=json.loads(read_url(url))
            chart=result["chart"]
            if chart.get("error"):
                raise RuntimeError(str(chart["error"]))
            r=chart["result"][0]
            quote=r["indicators"]["quote"][0]
            adjusted=r["indicators"].get("adjclose",[{}])[0].get("adjclose",[])
            ts=r["timestamp"]
            bars=[]
            for i,epoch in enumerate(ts):
                try:
                    c=float(quote["close"][i]); h=float(quote["high"][i]); l=float(quote["low"][i])
                    if all(math.isfinite(k) and k>0 for k in (c,h,l)):
                        adj=None
                        if i<len(adjusted):
                            try:
                                aval=float(adjusted[i])
                                if math.isfinite(aval) and aval>0:adj=aval
                            except (TypeError,ValueError):pass
                        bars.append((datetime.fromtimestamp(epoch,timezone.utc).strftime("%Y-%m-%d"),h,l,c,float(quote.get("volume",[None]*len(ts))[i] or 0),adj))
                except (TypeError,ValueError,IndexError,KeyError):
                    continue
            return bars, r.get("meta",{}).get("currency","USD"),"Yahoo Finance"
        except Exception as e:
            last=type(e).__name__+": "+str(e)[:130]
    raise RuntimeError(last)

def fetch_stooq(symbol):
    if "." in symbol:
        raise RuntimeError("No trusted Stooq fallback for international tickers")
    stooq_symbol=symbol.lower()+".us"
    today=datetime.now(timezone.utc).date()
    beg=today-timedelta(days=790)
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
    return bars,"USD","Stooq US (unverified adjustment)"


def momentum_12_2(closes):
    """Simple total-price momentum, ending 42 trading sessions before today.

    Requires >=253 closing prices. We deliberately never infer momentum from a
    shorter history or calculate a misleading normalized 0–100 buy score.
    """
    if len(closes)<253:return None
    old,new=closes[-253],closes[-43]
    if not old or not new or old<=0 or new<=0 or not math.isfinite(old) or not math.isfinite(new):return None
    return round(new/old-1,7)

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
            adjusted=[x[5] if len(x)>5 else None for x in bars]
            price=closes[-1]
            turnovers=[b[3]*b[4] for b in bars[-20:] if len(b)>4 and b[4]>0 and math.isfinite(b[4])]
            avg_local_turnover=round(sum(turnovers)/len(turnovers),0) if len(turnovers)>=12 else None
            avg_turnover=avg_local_turnover if currency=="USD" else None
            return {"ticker":symbol,"theme":theme,"close":round(price,6),"price_date":dates[-1],
                    "currency":currency,"source":source,"bars_count":len(bars),
                    "avg_dollar_turnover_20d":avg_turnover,
                    "avg_local_turnover_20d":avg_local_turnover,
                    "momentum_12_2":momentum_12_2(adjusted),
                    "momentum_basis":"Yahoo adjusted daily closes" if source=="Yahoo Finance" else "not verified"},None
        except Exception as e:
            errors.append(load.__name__+": "+str(e)[:140])
    return None,symbol+": "+"; ".join(errors)
