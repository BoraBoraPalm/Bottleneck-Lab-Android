"""Bottleneck Lab v5 research preview: SEC as-filed financials and Q/V/M ranks.

Not an investment signal. Uses a small, incomplete, currently surviving universe.
Only annual 10-K facts filed on/before as_of are accepted; monthly prices are
not point-in-time reconstructed by this module.
"""
from datetime import date, datetime, timezone
import math

REVENUE=("RevenueFromContractWithCustomerExcludingAssessedTax","Revenues",
         "SalesRevenueNet","RevenueFromContractWithCustomerIncludingAssessedTax")
TAG_MAP={
    "revenue":REVENUE,
    "gross_profit":("GrossProfit",),
    "op_cashflow":("NetCashProvidedByUsedInOperatingActivities",),
    "net_income":("NetIncomeLoss",),
    "assets":("Assets",),
    "equity":("StockholdersEquity","StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest"),
    "debt":("LongTermDebt","LongTermDebtNoncurrent",),
    "shares":("WeightedAverageNumberOfDilutedSharesOutstanding",
              "WeightedAverageNumberOfSharesOutstandingBasic")
}
INSTANT={"assets","equity","debt"}
MIN_MOMENTUM_BARS=253

def number(v):
    try:
        x=float(v)
        return x if math.isfinite(x) else None
    except (TypeError,ValueError):
        return None

def select_annual_fact(facts,tags,as_of,instant=False,unit="USD"):
    """Return latest FY figure *available as of date*. No reports filed later."""
    dt=as_of.isoformat() if isinstance(as_of,date) else str(as_of)[:10]
    if not (len(dt)==10 and dt[4]=="-" and dt[7]=="-"):
        raise ValueError("as_of must be YYYY-MM-DD")
    candidates=[]
    for tag in tags:
        for r in facts.get(tag,{}).get("units",{}).get(unit,[]):
            if r.get("form") not in {"10-K","10-K/A"}:continue
            end=r.get("end","");filed=r.get("filed","")
            if not (isinstance(end,str) and isinstance(filed,str) and end<=dt and filed<=dt):continue
            value=number(r.get("val"))
            if value is None:continue
            if not instant:
                begin=r.get("start")
                try:days=(date.fromisoformat(end)-date.fromisoformat(begin)).days
                except (TypeError,ValueError):continue
                if not 330<=days<=390:continue
            candidates.append({"value":value,"end":end,"filed":filed,"tag":tag})
    if not candidates:return None
    # Latest fiscal year end, latest filing that was actually available on as_of.
    return max(candidates,key=lambda x:(x["end"],x["filed"]))

def sec_fundamentals(filing,as_of=None):
    as_of=as_of or datetime.now(timezone.utc).date()
    as_date=as_of.isoformat() if isinstance(as_of,date) else str(as_of)[:10]
    gaap=filing.get("facts",{}).get("us-gaap",{})
    selected={}
    for key,tags in TAG_MAP.items():
        unit="shares" if key=="shares" else "USD"
        fact=select_annual_fact(gaap,tags,as_date,key in INSTANT,unit)
        if fact:selected[key]=fact
    rev=selected.get("revenue")
    if not rev:return None
    fy_end=rev["end"]
    # All relevant numbers must be aligned to the same fiscal year, not
    # an unrelated previous 10-K from another financial period.
    available={}
    for name,f in selected.items():
        if abs((date.fromisoformat(f["end"])-date.fromisoformat(fy_end)).days)<=65:
            available[name]=f
    if "assets" not in available or available["assets"]["value"]<=0:return None

    # Revenue growth: find the latest earlier fiscal-year fact actually filed
    # by as_of, not a later restatement. Select by fiscal year end.
    prev=[]
    for tag in REVENUE:
        for v in gaap.get(tag,{}).get("units",{}).get("USD",[]):
            if v.get("form") not in {"10-K","10-K/A"}:continue
            if not (v.get("filed","")<=as_date and v.get("end","")<fy_end):continue
            value=number(v.get("val"))
            try:duration=(date.fromisoformat(v["end"])-date.fromisoformat(v["start"])).days
            except (TypeError,ValueError):continue
            if value is not None and value>0 and 330<=duration<=390:
                prev.append((v["end"],v["filed"],value))
    growth=None
    if prev:
        _,_,old=max(prev)
        growth=(available["revenue"]["value"]/old-1)*100

    out={"source":"SEC EDGAR XBRL companyfacts","source_url":"https://data.sec.gov/api/xbrl/companyfacts/CIK"+
        f'{int(filing.get("cik",0)):010d}.json',
         "retrieved_at":datetime.now(timezone.utc).isoformat().replace("+00:00","Z"),
         "fiscal_year_end":fy_end,"as_of":as_date,
         "filed":max(v["filed"] for v in available.values())}
    for name,record in available.items():
        out[name+"_usd" if name!="shares" else "diluted_shares"]=round(record["value"],3)
    out["annual_revenue_usd"]=round(available["revenue"]["value"],2)
    if growth is not None:out["annual_revenue_growth_pct"]=round(growth,3)
    if "op_cashflow" in available:out["operating_cashflow_usd"]=round(available["op_cashflow"]["value"],2)
    if "net_income" in available:out["net_income_usd"]=round(available["net_income"]["value"],2)
    return out

def momentum_12_2(closes):
    """Return from 252 sessions ago to 42 sessions ago; no last 42 session prices."""
    if len(closes)<MIN_MOMENTUM_BARS:return None
    a=number(closes[-253]);b=number(closes[-43])
    if a is None or b is None or a<=0 or b<=0:return None
    return b/a-1

def metrics_for_row(row,as_of=None):
    """Construct genuinely observed metrics; never assign scores to missing facts."""
    f=row.get("fundamentals")
    if not isinstance(f,dict):return None
    date_today=(as_of or datetime.now(timezone.utc).date())
    as_date=date_today if isinstance(date_today,date) else date.fromisoformat(str(date_today)[:10])
    try:
        filed=date.fromisoformat(f["filed"])
        fy=date.fromisoformat(f["fiscal_year_end"])
        if filed>as_date or fy>as_date or (as_date-fy).days>610:return None
    except (KeyError,ValueError,TypeError):return None
    if row.get("currency")!="USD":return None
    shares=number(f.get("diluted_shares"))
    price=number(row.get("close"))
    assets=number(f.get("assets_usd"))
    if not shares or shares<=0 or not price or price<=0 or not assets or assets<=0:return None
    marketcap=shares*price
    def ratio(k,den):
        x=number(f.get(k))
        return x/den if x is not None and den>0 else None
    # Net debt is not inferred to be zero if missing: leverage metric is optional.
    q={
        "gross_profit_assets":ratio("gross_profit_usd",assets),
        "operating_cashflow_assets":ratio("op_cashflow_usd",assets),
        "net_income_assets":ratio("net_income_usd",assets),
        "low_debt_assets":(-ratio("debt_usd",assets) if ratio("debt_usd",assets) is not None else None)
    }
    v={
        "earnings_yield":ratio("net_income_usd",marketcap),
        "operating_cashflow_yield":ratio("op_cashflow_usd",marketcap),
        "book_to_market":ratio("equity_usd",marketcap)
    }
    mom=number(row.get("momentum_12_2"))
    # Stable identifiers and transparent minimum evidence: value>=1 quality>=2.
    if mom is None or sum(x is not None for x in q.values())<2 or sum(x is not None for x in v.values())<1:return None
    return {"momentum":mom,"quality":q,"value":v,
            "approx_market_cap_usd":round(marketcap,2),
            "period_end":f["fiscal_year_end"],"filing_date":f["filed"]}

def _rank_scores(entries):
    """Cross-section empirical percentile, with ties; NaNs absent, not zeros."""
    if not entries:return {}
    values=sorted({val for _,val in entries})
    ranks={v:(0.5 if len(values)==1 else i/(len(values)-1)) for i,v in enumerate(values)}
    return {ticker:ranks[val] for ticker,val in entries}

def assign_multifactor(stocks,as_of=None,min_eligible=8):
    """1/3 each factor if all three verified. Avoid ranking unavailable data."""
    candidates={}
    for row in stocks:
        row.pop("multifactor",None)
        if row.get("eligible_for_ranking") is not True:continue
        m=metrics_for_row(row,as_of)
        if m:candidates[row["ticker"]]=m
    if len(candidates)<min_eligible:
        return {"status":"insufficient_data","coverage":len(candidates),"min_required":min_eligible,
                "ranking_count":0,"method":"Q/V/M thirds, within currently covered US stocks only"}
    for key in ("momentum","quality","value"):
        for metric in (["raw"] if key=="momentum" else list(next(iter(candidates.values()))[key])):
            values=[]
            for ticker,m in candidates.items():
                value=m["momentum"] if key=="momentum" else m[key].get(metric)
                if value is not None:values.append((ticker,value))
            ranks=_rank_scores(values)
            for ticker,m in candidates.items():
                m.setdefault("ranks",{}).setdefault(key,{})[metric]=ranks.get(ticker)
    row_by_ticker={s["ticker"]:s for s in stocks}
    result=[]
    for ticker,m in candidates.items():
        ranks=m["ranks"]
        def mean_valid(d):
            vals=[v for v in d.values() if v is not None]
            return sum(vals)/len(vals) if vals else None
        mom=mean_valid(ranks["momentum"])
        quality=mean_valid(ranks["quality"])
        value=mean_valid(ranks["value"])
        if None in (mom,quality,value):continue
        total=(mom+quality+value)/3
        obj={"score":round(total*100,2),"momentum_score":round(mom*100,2),
             "quality_score":round(quality*100,2),"value_score":round(value*100,2),
             "momentum_12_2":round(m["momentum"],6),
             "quality_metrics":m["quality"],"value_metrics":m["value"],
             "market_cap_usd_approx":m["approx_market_cap_usd"],
             "filing_date":m["filing_date"],"fiscal_year_end":m["period_end"],
             "cohort_size":len(candidates),"validated":False}
        row_by_ticker[ticker]["multifactor"]=obj
        result.append((ticker,total))
    return {"status":"experimental","coverage":len(candidates),
            "ranking_count":len(result),"min_required":min_eligible,
            "weights":{"momentum":1/3,"quality":1/3,"value":1/3},
            "method":"Equal cross-sectional percentile averages; 12-2 momentum; SEC annual quality/value; NOT marketwide or sector-neutral",
            "limitations":["Current survivors only","SEC annual data sparse and ticker-biased",
            "Shares from annual 10-K approximate current market cap","No historical QVM validation",
            "No verified industry-neutral comparator","No earnings-revision feed","No quantified bottleneck factor"]}
