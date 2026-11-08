"""Reference exchange-rate conversion for EUR-based investment dashboard.

Prices remain exchange-specific source close; converted EUR values are estimates,
not real-time executable Trade Republic bid/ask prices.
"""
import json
import math
from datetime import date, datetime, timezone, timedelta
from build_snapshot import read_url

FX_ENDPOINT="https://api.frankfurter.dev/v2/rates?base=EUR"
CACHE_MAX_DAYS=7

def latest_eur_rates(fetch=read_url, today=None):
    today=today or datetime.now(timezone.utc).date()
    raw=json.loads(fetch(FX_ENDPOINT,timeout=16))
    if not isinstance(raw,list):
        raise ValueError("Frankfurter rates response is not a list")
    result={"EUR":{"eur_per_unit":1.0,"fx_date":today.isoformat(),"source":"native EUR"}}
    for item in raw:
        if not isinstance(item,dict) or item.get("base")!="EUR":continue
        curr=item.get("quote")
        try:
            rate=float(item.get("rate"))
            dated=date.fromisoformat(item.get("date",""))
        except (ValueError,TypeError):
            continue
        if not isinstance(curr,str) or len(curr)!=3 or not math.isfinite(rate) or rate<=0:continue
        if dated>today or today-dated>timedelta(days=CACHE_MAX_DAYS):continue
        result[curr]={"eur_per_unit":1/rate,"fx_date":dated.isoformat(),"source":"Frankfurter official-provider reference FX"}
    add_subunits(result)
    if len(result)<20:
        raise ValueError("Too few valid rates: "+str(len(result)))
    return result

# Yahoo quotes some exchanges in sub-units: London pence (GBp/GBX),
# Tel Aviv agorot (ILA), Johannesburg cents (ZAc), Kuwait fils (KWF).
SUBUNITS={"GBp":("GBP",100,"UK pence (1/100 GBP)"),"GBX":("GBP",100,"UK pence GBX (1/100 GBP)"),
          "ILA":("ILS",100,"Israeli agorot (1/100 ILS)"),"ZAc":("ZAR",100,"South African cents (1/100 ZAR)"),
          "KWF":("KWD",1000,"Kuwaiti fils (1/1000 KWD)")}

def add_subunits(result):
    for sub,(main,divisor,label) in SUBUNITS.items():
        if main in result and sub not in result:
            base=result[main]
            result[sub]={"eur_per_unit":base["eur_per_unit"]/divisor,"fx_date":base["fx_date"],"source":label}
    return result

def with_previous_rates(fx,previous,today=None,max_days=CACHE_MAX_DAYS):
    """Fill currencies missing today from the previous snapshot (at most a week old)."""
    today=today or datetime.now(timezone.utc).date()
    merged=dict(fx or {})
    reused=[]
    for curr,val in ((previous or {}).get("fx_eur") or {}).items():
        if curr in merged or not isinstance(val,dict):continue
        try:
            rate=float(val["eur_per_unit"]);dated=date.fromisoformat(val["fx_date"])
        except (KeyError,TypeError,ValueError):
            continue
        if math.isfinite(rate) and rate>0 and timedelta(0)<=today-dated<=timedelta(days=max_days):
            merged[curr]={"eur_per_unit":rate,"fx_date":dated.isoformat(),"source":"previous run (reference FX, "+dated.isoformat()+")"}
            reused.append(curr)
    return add_subunits(merged),sorted(reused)

def needed_main_currencies(currencies,fx):
    """Main currencies (ISO codes) behind stock currencies that have no rate yet."""
    need=set()
    for curr in currencies:
        if not isinstance(curr,str) or curr in fx:continue
        main=SUBUNITS[curr][0] if curr in SUBUNITS else curr
        if len(main)==3 and main.isalpha() and main.isupper() and main not in fx:need.add(main)
    return sorted(need)

def with_yahoo_rates(fx,currencies,fetch=None,today=None,max_days=CACHE_MAX_DAYS,limit=25):
    """Fallback for currencies the reference provider lacks: last Yahoo daily
    close of <CUR>EUR=X, at most a week old. Returns (rates, used, failed)."""
    today=today or datetime.now(timezone.utc).date()
    if fetch is None:
        from build_snapshot import fetch_yahoo as fetch
    merged=dict(fx or {});used=[];failed={}
    for main in needed_main_currencies(currencies,merged)[:limit]:
        try:
            bars,_,_=fetch(main+"EUR=X")
            day,rate=None,None
            for bar in reversed(bars):
                if math.isfinite(bar[3]) and bar[3]>0:
                    day,rate=date.fromisoformat(bar[0]),float(bar[3]);break
            if rate is None or day>today or today-day>timedelta(days=max_days):
                raise ValueError("no close within %d days"%max_days)
            merged[main]={"eur_per_unit":rate,"fx_date":day.isoformat(),"source":"Yahoo Finance FX close %sEUR=X (fallback)"%main}
            used.append(main)
        except Exception as exc:
            failed[main]=type(exc).__name__+": "+str(exc)[:80]
    return add_subunits(merged),used,failed

def add_eur_prices(stock_rows, fx_rates):
    converted=0
    missing=set()
    for row in stock_rows:
        curr=row.get("currency")
        val=fx_rates.get(curr)
        if not val:
            row.pop("eur_per_unit",None)
            row.pop("reference_close_eur",None)
            row.pop("reference_atr_eur",None)
            row.pop("fx_date",None)
            if curr:missing.add(curr)
            continue
        multiplier=val["eur_per_unit"]
        close=row.get("close")
        atr=row.get("atr")
        if not isinstance(close,(float,int)) or not math.isfinite(close) or close<=0:
            continue
        row["eur_per_unit"]=round(multiplier,12)
        row["reference_close_eur"]=round(close*multiplier,6)
        row["reference_atr_eur"]=round(atr*multiplier,6) if isinstance(atr,(int,float)) and math.isfinite(atr) else None
        row["fx_date"]=val["fx_date"]
        row["eur_price_type"]="native_eur_close" if curr=="EUR" else "indicative_fx_conversion"
        converted+=1
    return converted,sorted(missing)
