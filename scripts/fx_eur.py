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
    # UK equity prices are frequently quoted in GBp (pence), not GBP (pounds).
    if "GBP" in result:
        gbp=result["GBP"]
        result["GBp"]={"eur_per_unit":gbp["eur_per_unit"]/100,"fx_date":gbp["fx_date"],"source":"UK pence (1/100 GBP)"}
    if len(result)<20:
        raise ValueError("Too few valid rates: "+str(len(result)))
    return result

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
