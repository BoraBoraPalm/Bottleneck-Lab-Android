"""Beate-Sander-inspired, conservative US-SEC XBRL quality + price-dip screen.

NOT the historical method of Beate Sander, which requires discretionary
business assessment, diversified long-term holdings, dividends and partial
sales. This code only produces research candidates, never BUY recommendations.
All financial values used here must be independently filed and recent.
SEC companyfacts officially supports US-GAAP and filing dates; no guessed
international fundamentals. No valuation or dividend proxy is fabricated.
"""
import json
import math
import re
from datetime import date,datetime,timezone
from urllib.request import Request,urlopen

TICKERS_URL="https://www.sec.gov/files/company_tickers.json"
FACTS_BASE="https://data.sec.gov/api/xbrl/companyfacts/CIK"
USER_AGENT="Bottleneck Lab nonprofit academic research (contact: bottleneck-lab@github.com)"
DEFAULT_MAX=35
# Research heuristics, NOT rules personally specified by Beate Sander.
MIN_DISCOUNT=.15
MAX_DISCOUNT=.55
MIN_PROFIT_MARGIN=.03
MIN_GROWTH=-.10
MAX_FILING_AGE_DAYS=760
EXCLUDE_FINANCIALS=True
BASE_FIELDS=("Revenues","RevenueFromContractWithCustomerExcludingAssessedTax",
             "RevenueFromContractWithCustomerIncludingAssessedTax","SalesRevenueNet",
             "SalesRevenueGoodsNet","SalesRevenueServicesNet")
PROFIT_FIELDS=("NetIncomeLoss","ProfitLoss")
OPERATING_CASH_FIELDS=("NetCashProvidedByUsedInOperatingActivities",)
CANONICAL_FORMS=("10-K","10-K/A")
TICKER_RE=re.compile(r"^[A-Z][A-Z0-9-]{0,9}$")

def get_json(url,timeout=12,max_bytes=9500000):
    req=Request(url,headers={"User-Agent":USER_AGENT,"Accept":"application/json",
                             "Accept-Encoding":"identity"})
    with urlopen(req,timeout=timeout) as resp:
        if resp.status!=200:raise RuntimeError("HTTP "+str(resp.status))
        raw=resp.read(max_bytes+1)
    if len(raw)>max_bytes:raise RuntimeError("Response too large")
    return json.loads(raw)

def ticker_map():
    raw=get_json(TICKERS_URL,timeout=18,max_bytes=2500000)
    result={}
    rows=raw.values() if isinstance(raw,dict) else raw
    for item in rows:
        if not isinstance(item,dict):continue
        ticker=str(item.get("ticker","")).upper()
        try:cik=int(item["cik_str"])
        except (TypeError,ValueError,KeyError):continue
        if ticker and TICKER_RE.fullmatch(ticker) and cik>0:
            result[ticker]=cik
    if len(result)<100:raise RuntimeError("SEC ticker map incomplete")
    return result

def _financial_tag_series(facts,tags):
    """Annual as-filed 10-K nonzero USD, frame-duration, latest amendment wins.

    Keep a common fiscal-year-end per metric, without mixing one quarterly
    or year-to-date observation with annual numbers.
    """
    gaap=facts.get("facts",{}).get("us-gaap",{})
    for tag in tags:
        concept=gaap.get(tag,{})
        observations=concept.get("units",{}).get("USD",[])
        found={}
        for row in observations:
            try:
                if row.get("form") not in CANONICAL_FORMS or row.get("fp")!="FY":continue
                start=date.fromisoformat(row["start"])
                end=date.fromisoformat(row["end"])
                filed=date.fromisoformat(row["filed"])
                duration=(end-start).days
                if duration<335 or duration>385:continue
                value=float(row["val"])
                if not math.isfinite(value):continue
                key=end.isoformat()
                old=found.get(key)
                if old is None or filed>old[0]:
                    found[key]=(filed,value)
            except (ValueError,KeyError,TypeError,OverflowError):
                continue
        if found:return found
    return {}

def _recent_frame(facts,asof=None):
    today=asof or datetime.now(timezone.utc).date()
    rev=_financial_tag_series(facts,BASE_FIELDS)
    income=_financial_tag_series(facts,PROFIT_FIELDS)
    cash=_financial_tag_series(facts,OPERATING_CASH_FIELDS)
    shared=sorted(set(rev)&set(income)&set(cash),reverse=True)
    for end in shared:
        d=date.fromisoformat(end)
        if d>today or (today-d).days>MAX_FILING_AGE_DAYS:continue
        # No future filings. In fact, for the CURRENT screen they must
        # have been submitted by evaluation time.
        filings=(rev[end][0],income[end][0],cash[end][0])
        filed=max(filings)
        if filed>today or (today-filed).days>MAX_FILING_AGE_DAYS:continue
        revenue=rev[end][1]
        net=income[end][1]
        cfo=cash[end][1]
        if revenue<=0:continue
        earlier=sorted((year for year in rev
            if 300<=(d-date.fromisoformat(year)).days<=430
            and rev[year][0]<=today and rev[year][1]>0),reverse=True)
        if not earlier:continue
        growth=revenue/rev[earlier[0]][1]-1
        if not math.isfinite(growth) or abs(growth)>10:continue
        return {"revenue":revenue,"net_income":net,"operating_cashflow":cfo,
            "revenue_growth_yoy":round(growth,6),
            "profit_margin":round(net/revenue,6),
            "fy_end":end,"filed":filed.isoformat(),
            "base_year_end":earlier[0]}
    return None

def fundamental_quality(facts,asof=None):
    annual=_recent_frame(facts,asof)
    if not annual:return None
    annual["quality_ok"]=(
        annual["net_income"]>0 and annual["operating_cashflow"]>0
        and annual["profit_margin"]>=MIN_PROFIT_MARGIN
        and annual["revenue_growth_yoy"]>=MIN_GROWTH)
    annual["source"]="SEC EDGAR 10-K XBRL (US-GAAP)"
    annual["cik"]=int(facts.get("cik",0)) if str(facts.get("cik","")).isdigit() else None
    return annual

def download_fundamental(cik):
    if not isinstance(cik,int) or cik<=0:raise ValueError("Invalid CIK")
    raw=get_json(FACTS_BASE+str(cik).zfill(10)+".json",timeout=16,max_bytes=11000000)
    if int(raw.get("cik",-1))!=cik:raise ValueError("SEC CIK mismatch")
    return fundamental_quality(raw)

def sander_screen(stock,fund):
    """Independent price dip + filed fundamentals; ZERO if no valid fundamentals."""
    if not isinstance(fund,dict) or fund.get("quality_ok") is not True:return None
    if not isinstance(stock,dict) or stock.get("source")!="Yahoo Finance":return None
    dd=stock.get("drawdown_252d")
    if not isinstance(dd,(int,float)) or not math.isfinite(dd):
        return None
    if dd> -MIN_DISCOUNT or dd< -MAX_DISCOUNT:return None
    margin=fund.get("profit_margin")
    growth=fund.get("revenue_growth_yoy")
    if not all(isinstance(v,(int,float)) and math.isfinite(v) for v in (margin,growth)):
        return None
    # More pronounced price dips + stronger fundamental metrics; not valuation.
    dip=100*(abs(dd)-MIN_DISCOUNT)/(MAX_DISCOUNT-MIN_DISCOUNT)
    margin_score=100*max(0,min(1,(margin-MIN_PROFIT_MARGIN)/.17))
    growth_score=100*max(0,min(1,(growth-MIN_GROWTH)/.35))
    return round(.5*dip+.25*margin_score+.25*growth_score,4)

def enrich_stocks(stocks,prior,maximum=DEFAULT_MAX):
    """Update limited SEC queries, retain still-current cached filings.

    Returns status. SEC is independent of normal quote pipeline; errors must
    never lead to fabricated eligible candidates.
    """
    old={s.get("ticker"):s.get("fundamentals") for s in prior.get("stocks",[])
         if isinstance(s,dict) and isinstance(s.get("fundamentals"),dict)}
    today=datetime.now(timezone.utc).date()
    candidates=[s for s in stocks if s.get("eligible_global_ranking") is True
                and isinstance(s.get("ticker"),str) and "." not in s["ticker"]
                and isinstance(s.get("drawdown_252d"),(int,float))
                and -.75<=s["drawdown_252d"]<=-.10]
    candidates.sort(key=lambda s:(
        0 if -.55<=s["drawdown_252d"]<=-.15 else 1,
        abs(s["drawdown_252d"]+.30),
        s["ticker"]))
    try:lookup=ticker_map()
    except Exception as e:
        lookup={}
        error="SEC mapping unavailable: "+str(e)[:120]
    else:error=None
    updated=0
    succeeded=0
    failed=0
    for stock in stocks:
        ticker=stock.get("ticker")
        cached=old.get(ticker)
        if isinstance(cached,dict):
            try:
                age=(today-date.fromisoformat(cached["checked_at"])).days
                if age>=0 and age<=28:
                    stock["fundamentals"]=cached
            except (KeyError,ValueError,TypeError):
                pass
    for s in candidates:
        if updated>=maximum:break
        ticker=s["ticker"]
        if s.get("fundamentals") is not None:continue
        cik=lookup.get(ticker)
        if cik is None:continue
        updated+=1
        try:
            fund=download_fundamental(cik)
            if fund is not None:
                fund["checked_at"]=today.isoformat()
                s["fundamentals"]=fund
                succeeded+=1
            else:failed+=1
        except Exception:
            failed+=1
    qualified=0
    with_fund=0
    for s in stocks:
        fund=s.get("fundamentals")
        if isinstance(fund,dict):
            # Cached figures must still be fresh by SEC filing date.
            try:
                filed=date.fromisoformat(fund["filed"])
                if filed>today or (today-filed).days>MAX_FILING_AGE_DAYS:
                    fund=None
            except (KeyError,TypeError,ValueError):fund=None
        if fund is None:
            s.pop("fundamentals",None)
            s["sander_score"]=None
        else:
            with_fund+=1
            s["sander_score"]=sander_screen(s,fund)
            if s["sander_score"] is not None:qualified+=1
    return {"name":"Beate Sander-inspirierte Kursrückgang-/Qualitätsauswahl",
        "source":"SEC EDGAR XBRL US-GAAP (10-K); US-listed SEC filers only",
        "method":"15–55% under 252-day high; positive net income and operating cash flow, >=3% net margin, >=-10% revenue YoY; 50% drawdown, 25% margin, 25% growth score",
        "checked_this_run":updated,"facts_downloaded":succeeded,"no_usable_facts":failed,
        "with_verified_fundamentals":with_fund,"qualified_candidates":qualified,
        "status":"partial" if error else "ok",
        "warning":error,
        "limitations":"Experimental approximation; SEC 10-K, often no non-US filings. No proven excess returns, valuation, dividends, sector coverage or point-in-time backtest."}
