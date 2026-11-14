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
from concurrent.futures import ThreadPoolExecutor
from itertools import zip_longest
from urllib.request import Request,urlopen
from growth_radar import sec_quarters,relay_quarters,comparable_quarters
from factor_research import sec_earnings_history,relay_earnings_history,earnings_window

TICKERS_URL="https://www.sec.gov/files/company_tickers.json"
FACTS_BASE="https://data.sec.gov/api/xbrl/companyfacts/CIK"
USER_AGENT="Bottleneck Lab nonprofit academic research (contact: bottleneck-lab@github.com)"
DEFAULT_MAX=60
SCHEMA_VERSION=4
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
BALANCE_FIELDS={
    "assets":("Assets",),
    "equity":("StockholdersEquity",),
    "liabilities":("Liabilities",),
    "current_assets":("AssetsCurrent",),
    "current_liabilities":("LiabilitiesCurrent",),
}
CAPEX_FIELDS=("PaymentsToAcquirePropertyPlantAndEquipment",)
GROSS_PROFIT_FIELDS=("GrossProfit",)
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

def _financial_tag_series(facts,tags,asof=None,instant=False):
    """Finite USD facts; annual durations or exact balance dates, latest filing wins.

    Keep a common fiscal-year-end per metric, without mixing one quarterly
    or year-to-date observation with annual numbers.
    """
    gaap=facts.get("facts",{}).get("us-gaap",{})
    today=asof or datetime.now(timezone.utc).date()
    for tag in tags:
        concept=gaap.get(tag,{})
        observations=concept.get("units",{}).get("USD",[])
        found={}
        for row in observations:
            try:
                allowed=CANONICAL_FORMS+("10-Q","10-Q/A") if instant else CANONICAL_FORMS
                if row.get("form") not in allowed:continue
                if not instant and row.get("fp")!="FY":continue
                end=date.fromisoformat(row["end"])
                filed=date.fromisoformat(row["filed"])
                if filed>today or end>today:continue
                if instant:
                    if row.get("start"):continue
                else:
                    start=date.fromisoformat(row["start"])
                    duration=(end-start).days
                    if duration<335 or duration>385:continue
                if isinstance(row["val"],bool):continue
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
    rev=_financial_tag_series(facts,BASE_FIELDS,today)
    income=_financial_tag_series(facts,PROFIT_FIELDS,today)
    cash=_financial_tag_series(facts,OPERATING_CASH_FIELDS,today)
    for end in sorted(rev,reverse=True):
        d=date.fromisoformat(end)
        if d>today or (today-d).days>MAX_FILING_AGE_DAYS:continue
        # No future filings. In fact, for the CURRENT screen they must
        # have been submitted by evaluation time.
        filings=[series[end][0] for series in (rev,income,cash) if end in series]
        filed=max(filings)
        if filed>today or (today-filed).days>MAX_FILING_AGE_DAYS:continue
        revenue=rev[end][1]
        net=income[end][1] if end in income else None
        cfo=cash[end][1] if end in cash else None
        if revenue<0:continue
        earlier=sorted((year for year in rev
            if 300<=(d-date.fromisoformat(year)).days<=430
            and rev[year][0]<=today and rev[year][1]>0),reverse=True)
        prior=earlier[0] if earlier else None
        annual={"revenue":revenue,"net_income":net,"operating_cashflow":cfo,
            "prior_revenue":rev[prior][1] if prior else None,
            "prior_net_income":income[prior][1] if prior in income else None,
            "fy_end":end,"filed":filed.isoformat(),
            "base_year_end":prior}
        capex=_financial_tag_series(facts,CAPEX_FIELDS,today)
        if end in capex:
            annual["capex"]=capex[end][1]
            filings.append(capex[end][0])
        gross=_financial_tag_series(facts,GROSS_PROFIT_FIELDS,today)
        if end in gross:
            annual["gross_profit"]=gross[end][1]
            filings.append(gross[end][0])
        balance_filings=[]
        for key,tags in BALANCE_FIELDS.items():
            series=_financial_tag_series(facts,tags,today,instant=True)
            if end in series:
                annual[key]=series[end][1]
                balance_filings.append(series[end][0])
            if key=="assets":
                earlier_assets=sorted((k for k in series if 350<=(d-date.fromisoformat(k)).days<=385
                                       and series[k][1]>0),reverse=True)
                if earlier_assets:
                    prior_asset_end=earlier_assets[0]
                    annual["prior_assets"]=series[prior_asset_end][1]
                    annual["prior_assets_end"]=prior_asset_end
                    balance_filings.append(series[prior_asset_end][0])
        if balance_filings:annual["balance_filed"]=max(balance_filings).isoformat()
        annual["filed"]=max(filings+balance_filings).isoformat()
        return _derived_metrics(annual)
    return None

def _number(value):
    return isinstance(value,(int,float)) and not isinstance(value,bool) and math.isfinite(value)

def _ratio(numerator,denominator):
    if not _number(numerator) or not _number(denominator) or denominator<=0:return None
    result=numerator/denominator
    return round(result,6) if math.isfinite(result) else None

def _derived_metrics(annual):
    """Keep verified partial reports useful; missing figures never become zero."""
    revenue=annual.get("revenue")
    net=annual.get("net_income")
    cfo=annual.get("operating_cashflow")
    prior=annual.get("prior_net_income")
    growth=_ratio(revenue,annual.get("prior_revenue"))
    annual["revenue_growth_yoy"]=round(growth-1,6) if growth is not None else None
    annual["profit_margin"]=_ratio(net,revenue)
    annual["operating_cashflow_margin"]=_ratio(cfo,revenue)
    earnings_growth=_ratio(net,prior)
    annual["net_income_growth_yoy"]=round(earnings_growth-1,6) if earnings_growth is not None else None
    annual["earnings_comparison"]=("loss" if _number(net) and net<=0 else
        "turnaround" if _number(net) and _number(prior) and prior<=0 else
        "comparable" if earnings_growth is not None else "missing")
    capex=annual.get("capex")
    annual["free_cashflow"]=cfo-capex if _number(cfo) and _number(capex) and capex>=0 else None
    annual["free_cashflow_margin"]=_ratio(annual["free_cashflow"],revenue)
    annual["equity_ratio"]=_ratio(annual.get("equity"),annual.get("assets"))
    annual["current_ratio"]=_ratio(annual.get("current_assets"),annual.get("current_liabilities"))
    annual["liabilities_to_equity"]=_ratio(annual.get("liabilities"),annual.get("equity"))
    annual["gross_profit_to_assets"]=_ratio(annual.get("gross_profit"),annual.get("assets"))
    annual["cashflow_to_assets"]=_ratio(cfo,annual.get("assets"))
    assets_growth=_ratio(annual.get("assets"),annual.get("prior_assets"))
    annual["asset_growth_yoy"]=round(assets_growth-1,6) if assets_growth is not None else None
    annual["quality_ok"]=(
        _number(net) and net>0 and _number(cfo) and cfo>0
        and _number(annual["profit_margin"]) and annual["profit_margin"]>=MIN_PROFIT_MARGIN
        and _number(annual["revenue_growth_yoy"]) and annual["revenue_growth_yoy"]>=MIN_GROWTH)
    annual["currency"]="USD"
    annual["schema_version"]=SCHEMA_VERSION
    return annual

def fundamental_quality(facts,asof=None):
    annual=_recent_frame(facts,asof)
    if not annual:return None
    annual["source"]="SEC EDGAR 10-K XBRL (US-GAAP)"
    annual["cik"]=int(facts.get("cik",0)) if str(facts.get("cik","")).isdigit() else None
    annual["quarterly"]=sec_quarters(facts,asof)
    annual["quarterly"]["earnings"]=sec_earnings_history(facts,asof)
    return annual

def download_fundamental(cik):
    if not isinstance(cik,int) or cik<=0:raise ValueError("Invalid CIK")
    raw=get_json(FACTS_BASE+str(cik).zfill(10)+".json",timeout=16,max_bytes=11000000)
    if int(raw.get("cik",-1))!=cik:raise ValueError("SEC CIK mismatch")
    return fundamental_quality(raw)


TGM_ROOT="https://tgmcharts.com/api/v1/statements/"

def tgm_annual_quality(ticker):
    """Attributed SEC-derived annual statements, including optional balance data."""
    if not TICKER_RE.fullmatch(ticker):return None
    today=datetime.now(timezone.utc).date()
    def fetch(statement):
        obj=get_json(TGM_ROOT+ticker+"/"+statement+"?period=annual&years=4",
                     timeout=14,max_bytes=1800000)
        if (obj.get("symbol","").upper()!=ticker or obj.get("period")!="annual"
            or obj.get("currency")!="USD" or obj.get("status")):
            return {},None
        out={}
        for row in obj.get("rows") or []:
            if not isinstance(row,dict):continue
            allowed=CANONICAL_FORMS+("10-Q","10-Q/A") if statement=="balance-sheet" else CANONICAL_FORMS
            if row.get("form") not in allowed or row.get("fiscalPeriod")!="FY":continue
            try:
                end=date.fromisoformat(row["periodEnd"])
                filing=date.fromisoformat(row["filed"])
                if filing>today or end>today:continue
                # Retain the previous year's evidence even when it is older
                # than the maximum age of the CURRENT report.
                if (today-end).days>MAX_FILING_AGE_DAYS+430:continue
                if (today-filing).days>MAX_FILING_AGE_DAYS+430:continue
                if statement!="balance-sheet":
                    start=date.fromisoformat(row["periodStart"])
                    if not 335<=(end-start).days<=385:continue
            except (KeyError,TypeError,ValueError):continue
            old=out.get(end.isoformat())
            if old is None or row["filed"]>old["filed"]:out[end.isoformat()]=row
        return out,obj.get("cik")
    def value(row,key):
        v=(row.get("metrics") or {}).get(key)
        provenance=(row.get("provenance") or {}).get(key)
        if provenance:
            try:
                if date.fromisoformat(provenance["filed"])>today:return None
            except (KeyError,TypeError,ValueError):return None
        return v if _number(v) else None
    incomerows,cik=fetch("income-statement")
    if not incomerows:return None
    try:cashrows,_=fetch("cash-flow")
    except Exception:cashrows={}
    try:balances,_=fetch("balance-sheet")
    except Exception:balances={}
    for end in sorted(incomerows,reverse=True):
        if (today-date.fromisoformat(end)).days>MAX_FILING_AGE_DAYS:continue
        a=incomerows[end]
        b=cashrows.get(end,{})
        balance=balances.get(end,{})
        rev=value(a,"revenue")
        if rev is None or rev<0:continue
        older=sorted((k for k in incomerows
            if 300<=(date.fromisoformat(end)-date.fromisoformat(k)).days<=430
            and value(incomerows[k],"revenue") is not None
            and value(incomerows[k],"revenue")>0),reverse=True)
        previous=incomerows[older[0]] if older else {}
        annual={"revenue":rev,"net_income":value(a,"netIncome"),
            "gross_profit":value(a,"grossProfit"),
            "operating_cashflow":value(b,"operatingCashFlow"),
            "prior_revenue":value(previous,"revenue"),
            "prior_net_income":value(previous,"netIncome"),
            "capex":value(b,"capitalExpenditure"),
            "fy_end":end,"base_year_end":older[0] if older else None,
            "filed":max(row["filed"] for row in (a,b,balance) if row),
            "source":"TGMCharts (SEC EDGAR 10-K XBRL)",
            "cik":int(cik) if str(cik).isdigit() else None}
        if balance:annual["balance_filed"]=balance["filed"]
        for key,provider_key in (("assets","totalAssets"),("equity","totalStockholdersEquity"),
            ("liabilities","totalLiabilities"),("current_assets","totalCurrentAssets"),
            ("current_liabilities","totalCurrentLiabilities")):
            annual[key]=value(balance,provider_key)
        asset_prior=sorted((k for k in balances if 350<=(date.fromisoformat(end)-date.fromisoformat(k)).days<=385
                            and _number(value(balances[k],"totalAssets"))
                            and value(balances[k],"totalAssets")>0),reverse=True)
        if asset_prior:
            annual["prior_assets"]=value(balances[asset_prior[0]],"totalAssets")
            annual["prior_assets_end"]=asset_prior[0]
            annual["filed"]=max(annual["filed"],balances[asset_prior[0]]["filed"])
        annual=_derived_metrics(annual)
        annual["quarterly"]=tgm_quarterly(ticker)
        return annual
    return None

def tgm_quarterly(ticker):
    """One bounded, attributed quarterly income request; no estimates."""
    if not TICKER_RE.fullmatch(ticker):return {}
    try:
        raw=get_json(TGM_ROOT+ticker+"/income-statement?period=quarterly&years=5",
                     timeout=14,max_bytes=1800000)
        quarterly=relay_quarters(raw,ticker)
        quarterly["earnings"]=relay_earnings_history(raw,ticker)
        return quarterly
    except Exception:return {}

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
    # The dip only qualifies. Until 2026-11-14 its depth made up half of the score.
    # The archived strategy audit (research/tests/2026-11-14-strategy-audit) found that
    # deeper fallers kept lagging, so only the fundamental metrics rank now. Not valuation,
    # and not validated as profitable either.
    margin_score=100*max(0,min(1,(margin-MIN_PROFIT_MARGIN)/.17))
    growth_score=100*max(0,min(1,(growth-MIN_GROWTH)/.35))
    return round(.5*margin_score+.5*growth_score,4)

def enrich_stocks(stocks,prior,maximum=DEFAULT_MAX,priority=None):
    """Rotate across ordinary stocks and dip candidates, preserving verified caches.

    A failed lookup is retried after two days rather than starving later symbols.
    The data panel is independent of Sander eligibility and factor selection.
    """
    old={s.get("ticker"):s for s in prior.get("stocks",[]) if isinstance(s,dict)}
    today=datetime.now(timezone.utc).date()
    candidates=[s for s in stocks if (s.get("eligible_global_ranking") is True or s.get("eligible_liquid_ranking") is True)
                and isinstance(s.get("ticker"),str) and TICKER_RE.fullmatch(s["ticker"])]
    by_dip=sorted((s for s in candidates if _number(s.get("drawdown_252d"))
        and -.55<=s["drawdown_252d"]<=-.15),
        key=lambda s:(abs(s["drawdown_252d"]+.30),s["ticker"]))
    by_momentum=sorted(candidates,key=lambda s:(
        -s["momentum_12_2"] if _number(s.get("momentum_12_2")) else 999,s["ticker"]))
    by_growth=sorted(candidates,key=lambda s:(
        -s["return_63d"] if _number(s.get("return_63d")) else 999,s["ticker"]))
    ordered=[]
    seen=set()
    # Stocks loaded in the search come first, even if not (yet) liquid/eligible.
    wanted=set(priority or [])
    for stock in stocks:
        if stock.get("ticker") in wanted and isinstance(stock.get("ticker"),str) and TICKER_RE.fullmatch(stock["ticker"]):
            ordered.append(stock);seen.add(stock["ticker"])
    for pair in zip_longest(by_momentum,by_dip,by_growth):
        for stock in pair:
            if stock and stock["ticker"] not in seen:
                ordered.append(stock)
                seen.add(stock["ticker"])
    for stock in stocks:
        previous=old.get(stock.get("ticker"),{})
        cached=previous.get("fundamentals")
        if isinstance(cached,dict) and not isinstance(stock.get("fundamentals"),dict):
            try:
                age=(today-date.fromisoformat(cached["checked_at"])).days
                if 0<=age<=28:stock["fundamentals"]=cached
            except (KeyError,ValueError,TypeError):pass
        if previous.get("fundamentals_checked_at"):
            stock["fundamentals_checked_at"]=previous["fundamentals_checked_at"]
        if previous.get("fundamentals_schema_checked"):
            stock["fundamentals_schema_checked"]=previous["fundamentals_schema_checked"]
    targets=[]
    for stock in ordered:
        cached=stock.get("fundamentals") or {}
        try:cache_age=(today-date.fromisoformat(cached.get("checked_at",""))).days
        except (ValueError,TypeError):cache_age=999
        if cached.get("schema_version")==SCHEMA_VERSION and 0<=cache_age<=7:continue
        try:
            attempted=(today-date.fromisoformat(stock.get("fundamentals_checked_at", ""))).days
            already_upgraded=(cached.get("schema_version")==SCHEMA_VERSION
                              or stock.get("fundamentals_schema_checked")==SCHEMA_VERSION)
            if (not cached or already_upgraded) and 0<=attempted<2:continue
        except (TypeError,ValueError):pass
        targets.append(stock)
        if len(targets)>=max(0,maximum):break
    if maximum<=0:targets=[]
    error=None
    lookup={}
    if targets:
        try:lookup=ticker_map()
        except Exception as e:error="SEC mapping unavailable: "+str(e)[:120]
    def load(stock):
        ticker=stock["ticker"]
        fund=None
        cik=lookup.get(ticker)
        try:
            if cik is not None:fund=download_fundamental(cik)
        except Exception:pass
        if fund is not None and (not comparable_quarters(fund.get("quarterly"))
                                or not earnings_window((fund.get("quarterly") or {}).get("earnings") or {},today)):
            quarterly=tgm_quarterly(ticker)
            if not comparable_quarters(fund.get("quarterly")) and comparable_quarters(quarterly):
                fund["quarterly"]=quarterly
            elif earnings_window(quarterly.get("earnings") or {},today):
                fund.setdefault("quarterly",{})["earnings"]=quarterly["earnings"]
        if fund is None:
            try:fund=tgm_annual_quality(ticker)
            except Exception:pass
        return fund
    succeeded=0
    # Three concurrent companies, each requesting sequentially; bounded API load.
    with ThreadPoolExecutor(max_workers=3) as pool:
        for stock,fund in zip(targets,pool.map(load,targets)):
            stock["fundamentals_checked_at"]=today.isoformat()
            stock["fundamentals_schema_checked"]=SCHEMA_VERSION
            if fund is not None:
                fund["checked_at"]=today.isoformat()
                stock["fundamentals"]=fund
                succeeded+=1
    qualified=0
    with_fund=0
    for stock in stocks:
        fund=stock.get("fundamentals")
        if isinstance(fund,dict):
            try:
                filed=date.fromisoformat(fund["filed"])
                end=date.fromisoformat(fund["fy_end"])
                if (filed>today or end>today or (today-filed).days>MAX_FILING_AGE_DAYS
                    or (today-end).days>MAX_FILING_AGE_DAYS):fund=None
            except (KeyError,TypeError,ValueError):fund=None
        if fund is None:
            stock.pop("fundamentals",None)
            stock["sander_score"]=None
        else:
            with_fund+=1
            stock["sander_score"]=sander_screen(stock,fund)
            if stock["sander_score"] is not None:qualified+=1
    return {"name":"Beate Sander-inspirierte Kursrückgang-/Qualitätsauswahl",
        "source":"SEC EDGAR XBRL US-GAAP, direct API or TGMCharts filing statement relay (10-K)",
        "method":"15–55% under 252-day high; positive net income and operating cash flow, >=3% net margin, >=-10% revenue YoY; score since 2026-11-14: 50% margin, 50% revenue growth, depth of the fall not scored",
        "checked_this_run":len(targets),"facts_downloaded":succeeded,
        "no_usable_facts":len(targets)-succeeded,
        "with_verified_fundamentals":with_fund,"qualified_candidates":qualified,
        "status":"partial" if error and with_fund==0 else "ok",
        "warning":error,
        "limitations":"Experimental approximation; SEC 10-K, often no non-US filings. Third-party relay credited to TGMCharts. No proven excess returns, valuation, dividends, sector coverage or point-in-time backtest."}
