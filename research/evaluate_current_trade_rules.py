#!/usr/bin/env python3
"""Research ONLY: counterfactual 2021–2026 global stock selection and entry/exit rules.

Do not import mutable live app ranking rules dynamically. Constants documented
here are locked to their CURRENT values in scripts/trade_guidance.py on Oct 31,
2026. Current app has no automated order duration/holding period, so simulated
5-day pending limit, 20-session maximum horizon, 10 equal-weight holdings and
automatic next-open review exits are RESEARCH ASSUMPTIONS, not live app returns.

Important biases: currently surviving stock tickers, incomplete world/ADR
coverage, no historically exact broker orderability, Yahoo revised adjusted data,
not a genuinely untouched out-of-sample period, no taxes or full real spreads.
Publish all ablations, failed tickers and cost sensitivity; never select a winner.
"""
import csv
import hashlib
import io
import json
import math
import os
import random
import statistics
import sys
import time
import urllib.parse
import urllib.request
from bisect import bisect_right
from collections import Counter
from concurrent.futures import ThreadPoolExecutor,as_completed
from datetime import datetime,date,timezone
from pathlib import Path
from zoneinfo import ZoneInfo

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
from market_pipeline import CURATED_SYMBOLS,SEED_NAMES,NASDAQ,OTHER,parse_directory
from global_universe import discover_global

# Ex-ante fixed analysis design. Do NOT tune against observed results.
SEED=20261031
DATE_BEGIN="2020-03-01"
SIGNALS_FROM="2021-11-01"
LATEST_SIGNAL="2026-09-25"
DATE_END="2026-10-31"
TEST_FROM="2024-11-01"
START_CASH=10000.0
MAX_POSITIONS=10
MAX_PER_REGION=4
HOLD_DAYS=20
PENDING_DAYS=5
ENTRY_ATR=1.0
STOP_ATR=2.5
BROKER_EUR=1.0
SLIP=.001
FX_HEADWIND=.0
MIN_VOL_EUR=2e6
MIN_SHARE_EUR=2.0
REBALANCE_STRIDE=20
N_US_RANDOM=90
N_INT_RANDOM_PER_REGION=13
MAX_US_CURATED=115
MIN_HISTORIES=110
MIN_NONUS=24
BOOTSTRAP=2500
BLOCK_LENGTH=3
RANDOM_DATES=320
BENCH="ACWI"
MODELS=(
 "momentum_market",
 "momentum_limit",
 "momentum_limit_stop",
 "filtered_market",
 "filtered_limit",
 "filtered_market_stop",
 "filtered_limit_stop"
)
OUT=Path("research/current_rules_results")
OUT.mkdir(parents=True,exist_ok=True)
HEADERS={"User-Agent":"Mozilla/5.0 (compatible; BottleneckLabIndependentResearch/1.0)",
         "Accept":"application/json,text/csv,*/*"}
DATES=(datetime(2020,2,25,tzinfo=timezone.utc).timestamp(),
       datetime(2026,11,1,tzinfo=timezone.utc).timestamp())
ROOT="https://query1.finance.yahoo.com/v8/finance/chart/"
FRANKFURTER="https://api.frankfurter.dev/v2/rates"
SPLIT="Jan 2021–Oct 2024 training diagnostic / Nov 2024–Sep 2026 later period; NOT unseen OOS"

def request(url,timeout=19,max_size=3_000_000):
    req=urllib.request.Request(url,headers=HEADERS)
    with urllib.request.urlopen(req,timeout=timeout) as res:
        if res.status!=200:raise RuntimeError(f"HTTP {res.status}")
        content=res.read(max_size+1)
    if len(content)>max_size:raise RuntimeError("Oversized response")
    return content

def fixed_universe():
    # Historic selection membership is unavailable: this is a CURRENT-survivor
    # diagnostic, with deterministic SHA sampling and no use of final returns.
    symbols=set(CURATED_SYMBOLS)
    us={}
    for address,nasdaq in ((NASDAQ,True),(OTHER,False)):
        try:us.update(parse_directory(address,nasdaq))
        except Exception as e:print("WARN US listing",str(e)[:120],flush=True)
    extras=sorted((t for t in us if t not in symbols),
       key=lambda x:hashlib.sha256(f"{SEED}:US:{x}".encode()).hexdigest())
    selected=set(t for t in symbols if "." not in t)
    selected|=set(extras[:N_US_RANDOM])
    selected|=set(t for t in symbols if "." in t)
    try:
        found,meta=discover_global()
        regions={}
        for ticker,details in found.items():
            if ticker in selected or details["region"] in ("Nordamerika","Unbekannt"):continue
            if "." not in ticker:continue
            regions.setdefault(details["region"],[]).append(ticker)
        for reg,all_t in regions.items():
            subset=sorted(all_t,key=lambda x:hashlib.sha256(f"{SEED}:{reg}:{x}".encode()).hexdigest())
            selected.update(subset[:N_INT_RANDOM_PER_REGION])
        print("GLOBAL_DIRECTORY",meta["mapped_symbol_count"],
            "regions_in_research",list(regions),flush=True)
    except Exception as e:print("WARN global directory",str(e)[:160],flush=True)
    selected=list(selected)
    # More non-US than raw US is useful, but the true current app's universe is
    # not available historically. All results are sample dependent.
    selected.sort(key=lambda x:hashlib.sha256(f"{SEED}:ORDER:{x}".encode()).hexdigest())
    return selected

def get_price(symbol):
    messages=[]
    for host in ("query1.finance.yahoo.com","query2.finance.yahoo.com"):
        try:
            url=f"https://{host}/v8/finance/chart/{urllib.parse.quote(symbol,safe='')}?period1={int(DATES[0])}&period2={int(DATES[1])}&interval=1d"
            data=json.loads(request(url,timeout=20,max_size=1800000))
            result=data["chart"]["result"][0]
            quote=result["indicators"]["quote"][0]
            adjusted=result["indicators"].get("adjclose",[{}])[0].get("adjclose",[])
            currency=result.get("meta",{}).get("currency","USD")
            if not currency or not isinstance(currency,str):raise ValueError("Currency unavailable")
            zone=ZoneInfo(result.get("meta",{}).get("exchangeTimezoneName","UTC"))
            points={}
            for i,ts in enumerate(result.get("timestamp",[])):
                try:
                    dt=datetime.fromtimestamp(ts,zone).date().isoformat()
                    if not (DATE_BEGIN<=dt<=DATE_END):continue
                    o,h,l,c,v=[float(quote[k][i]) for k in ("open","high","low","close","volume")]
                    adj=float(adjusted[i]) if i<len(adjusted) and adjusted[i] is not None else float("nan")
                    if not all(math.isfinite(x) for x in (o,h,l,c,v,adj)) or min(o,h,l,c,adj)<=0 or h<l or v<0:continue
                    # DAILY adjustment from CURRENT data, may incorporate future
                    # corporate-action factors. In ratios up to the signal date,
                    # common future adjustment factors cancel; not genuine PIT data.
                    factor=adj/c
                    points[dt]=[o*factor,h*factor,l*factor,adj,v,o,c,factor]
                except (ValueError,KeyError,TypeError,IndexError,OverflowError):pass
            if len(points)<310:raise ValueError(f"Only {len(points)} price observations")
            return symbol,{"bars":points,"currency":currency,"source":host},None
        except Exception as e:
            messages.append(type(e).__name__+":"+str(e)[:90])
    return symbol,None,";".join(messages)[-240:]

def fx_rates(currencies):
    iso=set()
    for cur in currencies:
        upper=cur.upper()
        iso.add("GBP" if upper in ("GBX","GBP","GBPENCE","GBP.") else upper)
    iso.discard("EUR")
    currencies=sorted(iso)
    allowed=set("USD GBP CHF JPY CAD AUD HKD CNY INR KRW TWD BRL SEK DKK NOK SGD NZD ZAR MXN PLN ILS SAR TRY AED IDR MYR THB".split())
    currencies=[c for c in currencies if c in allowed]
    if "USD" not in currencies:currencies.append("USD")
    url=(FRANKFURTER+"?from=2020-01-01&to=2026-10-31&base=EUR"
         +"&quotes="+urllib.parse.quote(",".join(sorted(currencies)),safe=","))
    rows=json.loads(request(url,timeout=50,max_size=9000000))
    if not isinstance(rows,list):raise ValueError("Unexpected FX format")
    by_currency={}
    for item in rows:
        try:
            if item["base"]!="EUR":continue
            k=item["quote"].upper()
            rate=float(item["rate"])
            if not math.isfinite(rate) or rate<=0:continue
            by_currency.setdefault(k,{})[item["date"]]=1/rate
        except (KeyError,TypeError,ValueError):pass
    result={}
    for code,observations in by_currency.items():
        ks=sorted(observations)
        if len(ks)<1000:continue
        result[code]=(ks,[observations[k] for k in ks])
    if "USD" not in result:raise RuntimeError("USD/EUR historical FX missing")
    def rate(cur,day):
        if cur=="EUR":return 1.0
        cur=cur.upper()
        factor=.01 if cur in ("GBX","GBp".upper()) else 1.0
        if cur in ("GBX","GBP".lower().upper()): cur="GBP"
        if cur not in result:return None
        keys,values=result[cur]
        i=bisect_right(keys,day)-1
        if i<0 or (date.fromisoformat(day)-date.fromisoformat(keys[i])).days>8:return None
        return values[i]*factor
    return rate,{"fx_currencies":sorted(result),"fx_points":{x:len(y[0]) for x,y in result.items()}}

def prepare(d):
    days=sorted(d["bars"])
    arr=[d["bars"][key] for key in days]
    d["days"]=days
    d["values"]=arr
    d["idx"]={day:i for i,day in enumerate(days)}
    return d

def true_range(a,b,prev):
    return max(a[1]-a[2],abs(a[1]-prev[3]),abs(a[2]-prev[3]))

def features(symbol,d,day,rate,market=False):
    idx=d["idx"].get(day)
    if idx is None or idx<252:return None
    bars=d["values"]
    close=bars[idx][3]
    older=bars[idx-252][3]
    past42=bars[idx-42][3] # alternative common 12-2 formulation; current live uses 252->42? See below
    # LIVE APP uses price at [-253] to [-43], i.e. idx-252 and idx-42
    mom=past42/older-1
    if not all(math.isfinite(x) for x in (close,mom)) or close<=0:return None
    ret21=close/bars[idx-21][3]-1
    peak=max(bars[j][3] for j in range(idx-251,idx+1))
    drawdown=close/peak-1
    sma=sum(x[3] for x in bars[idx-199:idx+1])/200
    atr=sum(true_range(bars[j],bars[j-1],bars[j-1]) for j in range(idx-13,idx+1))/14
    # true_range uses b[j-1][3], adjusted daily prices.
    eur=rate(d["currency"],day)
    if eur is None or not math.isfinite(eur) or eur<=0:return None
    factor=bars[idx][7]
    raw_close=bars[idx][6]
    share_eur=raw_close*eur
    adv=sum(bars[j][6]*bars[j][4] for j in range(idx-19,idx+1))/20*eur
    if not market and (share_eur<MIN_SHARE_EUR or adv<MIN_VOL_EUR):return None
    if atr<=0:return None
    crash=ret21<=-.15 or drawdown<=-.25
    warning=ret21<=-.08 or drawdown<=-.15
    return {"ticker":symbol,"mom":mom,"trend":close/sma-1,
      "crash":crash,"correction":warning,"atr":atr,"close":close,
      "region":region_for(symbol),"date":day,
      "currency":d["currency"],"adv_eur":adv,
      "price_eur":share_eur,"ret21":ret21,"dd":drawdown}

def region_for(t):
    if "." not in t:return "Nordamerika"
    suffix=t.rsplit(".",1)[-1]
    return {
      "DE":"Europa","PA":"Europa","MI":"Europa","SW":"Europa","AS":"Europa","CO":"Europa","ST":"Europa","L":"Europa","MC":"Europa",
      "T":"Asien","TW":"Asien","HK":"Asien","SS":"Asien","SZ":"Asien","KS":"Asien","NS":"Asien","BO":"Asien","KQ":"Asien","SI":"Asien",
      "TO":"Nordamerika","V":"Nordamerika","SA":"Lateinamerika","MX":"Lateinamerika",
      "AX":"Ozeanien","JO":"Afrika","NZ":"Ozeanien"
    }.get(suffix,"Unbekannt")

def pick(rows,filtered,market_ok):
    rows.sort(key=lambda x:(-x["mom"],x["ticker"]))
    if filtered:
        if not market_ok:return []
        rows=[r for r in rows if r["mom"]>0 and r["trend"]>0 and not r["crash"] and not r["correction"]]
    tops=[];reg=Counter()
    for r in rows:
        if reg[r["region"]]>=MAX_PER_REGION:continue
        tops.append(r);reg[r["region"]]+=1
        if len(tops)>=MAX_POSITIONS:break
    return tops

def trade(signal,model,day_idx,calendar,history,rate,stake,slippage=SLIP):
    """Account for stock splits/dividends via adjusted OHLC + synthetic units.

    Actual trade quantity is whole raw shares at entry, adjusted synthetic
    units preserve exposure through future corporate actions and approximate
    dividend reinvestment. Stop execution at a worse gap open and conservative
    worst-case when entry and stop share a bar.
    """
    typ="limit" if model in ("momentum_limit","momentum_limit_stop","filtered_limit","filtered_limit_stop") else "market"
    use_stop=model in ("momentum_limit_stop","filtered_limit_stop","filtered_market_stop")
    use_review=model.startswith("filtered")
    v=signal
    entry_limit=v["close"]-ENTRY_ATR*v["atr"]
    stop=v["close"]-3.5*v["atr"] if typ=="limit" else v["close"]-STOP_ATR*v["atr"]
    if typ=="limit" and (entry_limit<=0 or (use_stop and stop<=0)):return None
    if use_stop and stop<=0:return None
    end=min(day_idx+HOLD_DAYS,len(calendar)-1)
    if end<=day_idx:return None
    d=history
    dbar=d["bars"]
    fill=None;entry_j=None
    for j in range(day_idx+1,min(end,day_idx+(PENDING_DAYS if typ=="limit" else 1))+1):
        day=calendar[j]
        if day not in dbar:continue
        b=dbar[day]
        if typ=="limit":
            if b[2]>entry_limit:continue
            px=min(b[0],entry_limit)
        else:px=b[0]
        fx=rate(d["currency"],day)
        if not fx:continue
        # Actual raw share price in the provider currency, using split factor.
        rawpx=px/b[7]
        units=math.floor((stake-BROKER_EUR)/(rawpx*(1+slippage)*fx))
        if units<=0:return None
        synthetic=units/b[7]
        spent=units*rawpx*(1+slippage)*fx+BROKER_EUR
        fill=(day,px,spent,synthetic,units)
        entry_j=j
        break
    if fill is None:return None
    buy_day,buy_px,spent,synthetic,units=fill
    exit_price=None;exit_date=None;reason=None
    # Do not evaluate a post-close exit rule on the signal close itself.
    # For the day of purchase, evaluate stop pessimistically if breached.
    for j in range(entry_j,end+1):
        today=calendar[j]
        if today not in dbar:continue
        b=dbar[today]
        if use_stop and b[2]<=stop:
            exit_price=min(buy_px,stop) if j==entry_j else min(b[0],stop)
            reason="stop_same_day" if j==entry_j else "stop_gap" if b[0]<stop else "stop"
            exit_date=today
            break
        if use_review and j>entry_j:
            prev=calendar[j-1]
            if prev in d["idx"]:
                feat=features(v["ticker"],d,prev,rate)
                if feat and (feat["crash"] or feat["trend"]<0):
                    exit_price=b[0];exit_date=today;reason="trend_crash_review_next_open"
                    break
        if j==end:
            exit_price=b[3];exit_date=today;reason="time"
    if exit_date is None:return None # no invented exit for discontinued quote
    fxsell=rate(d["currency"],exit_date)
    if not fxsell:return None
    proceeds=synthetic*exit_price*(1-slippage)*fxsell-BROKER_EUR
    return {"ticker":v["ticker"],"buy_day":buy_day,"exit_day":exit_date,
       "stake":stake,"spent":spent,"proceeds":proceeds,"pnl":proceeds-spent,
       "model":model,"exit_reason":reason,
       "entry_units":units,"exposure_days":max(0,entry_j-day_idx),
       "fill_price_adj":buy_px,"exit_price_adj":exit_price,
       "risk_rule_stop_adj":stop if use_stop else None}

def benchmark_20(day_idx,calendar,market,rate,stake,slippage=SLIP):
    next_day=calendar[day_idx+1]
    exit_day=calendar[day_idx+HOLD_DAYS]
    a=market["bars"].get(next_day)
    b=market["bars"].get(exit_day)
    if a is None or b is None:return None
    fx0=rate(market["currency"],next_day)
    fx1=rate(market["currency"],exit_day)
    if not fx0 or not fx1:return None
    # Synthetic benchmark units: fractional for tracking, 1EUR per side.
    ask=a[0]*fx0*(1+slippage)
    units=(stake-BROKER_EUR)/ask
    pnl=units*b[3]*fx1*(1-slippage)-BROKER_EUR-stake
    return pnl/stake

def matched_benchmark(tr,benchmark,rate,slippage=SLIP):
    start=benchmark["bars"].get(tr["buy_day"])
    end=benchmark["bars"].get(tr["exit_day"])
    if not start or not end:return None
    a=rate(benchmark["currency"],tr["buy_day"])
    b=rate(benchmark["currency"],tr["exit_day"])
    if not a or not b:return None
    invested=tr["spent"]
    if invested<=BROKER_EUR:return None
    n=(invested-BROKER_EUR)/(start[0]*a*(1+slippage))
    return n*end[3]*b*(1-slippage)-BROKER_EUR-invested

def drawdown(vals):
    peak=1.0;capital=1.0;worst=0.0
    for v in vals:
        capital*=1+v
        peak=max(peak,capital)
        worst=min(worst,capital/peak-1)
    return worst*100

def bootstrap(excess,seed=SEED,block=BLOCK_LENGTH,n=BOOTSTRAP):
    if len(excess)<10:return None
    rnd=random.Random(seed)
    means=[];size=len(excess)
    for _ in range(n):
        obs=[]
        while len(obs)<size:
            i=rnd.randrange(size)
            obs.extend(excess[(i+k)%size] for k in range(block))
        means.append(statistics.mean(obs[:size])*100)
    means.sort()
    return [round(means[int(.025*n)],4),round(means[int(.975*n)],4)]

def newey_west(excess,lags=3):
    n=len(excess)
    if n<10:return {"p":None,"z":None}
    mu=statistics.mean(excess)
    deviations=[x-mu for x in excess]
    gamma0=sum(x*x for x in deviations)/n
    variance=gamma0
    for lag in range(1,min(lags,n-1)+1):
        cov=sum(deviations[t]*deviations[t-lag] for t in range(lag,n))/n
        variance+=2*(1-lag/(lags+1))*cov
    se=math.sqrt(max(variance,0)/n)
    z=mu/se if se>0 else 0
    return {"p":round(math.erfc(abs(z)/math.sqrt(2)),6),"z":round(z,3)}

def summarize(name,indices,calendar,ranks,hists,fx,slippage=SLIP):
    cash=START_CASH;matched=START_CASH
    portfolio=[]
    trades=[]
    benchmark=hists[BENCH]
    for i in indices:
        d=calendar[i]
        picks=ranks[d]["filtered" if name.startswith("filtered") else "unfiltered"]
        stake=cash/MAX_POSITIONS
        group=[trade(s,name,i,calendar,hists[s["ticker"]],fx,stake,slippage) for s in picks]
        group=[t for t in group if t]
        pnl=sum(t["pnl"] for t in group)
        matched_pnl=sum(matched_benchmark(t,benchmark,fx,slippage) or 0 for t in group)
        # Matched benchmark tracked in scaled fraction of portfolio value at this
        # cohort's beginning to keep compared exposure/cash opportunity equal.
        ratio=matched/cash if cash>0 else 1
        matched+=matched_pnl*ratio
        new_cap=cash+pnl
        portfolio.append({"date":d,"start_eur":round(cash,2),"end_eur":round(new_cap,2),
            "block_return":pnl/cash,"matched_return":matched_pnl/cash,
            "selected":len(picks),"filled":len(group),
            "stop_count":sum(t["exit_reason"].startswith("stop") for t in group),
            "trend_exit_count":sum(t["exit_reason"]=="trend_crash_review_next_open" for t in group)})
        cash=new_cap
        trades.extend(group)
    returns=[r["block_return"] for r in portfolio]
    paired=[r["matched_return"] for r in portfolio]
    differences=[x-y for x,y in zip(returns,paired)]
    yrs=(date.fromisoformat(portfolio[-1]["date"])-date.fromisoformat(portfolio[0]["date"])).days/365.2425 if len(portfolio)>1 else 1
    out={
      "capital_final_eur":round(cash,2),
      "return_pct":round(100*(cash/START_CASH-1),3),
      "cagr_pct":round(100*((cash/START_CASH)**(1/yrs)-1),3) if cash>0 else -100,
      "max_period_end_drawdown_pct":round(drawdown(returns),3),
      "matched_ACWI_final_eur":round(matched,2),
      "excess_vs_matched_ACWI_eur":round(cash-matched,2),
      "mean_20day_pct":round(statistics.mean(returns)*100,4),
      "mean_20day_excess_matched_pct":round(statistics.mean(differences)*100,4),
      "excess_matched_bootstrap_95pct_mean20d":bootstrap(differences,seed=SEED+len(name)),
      "matched_newey_west":newey_west(differences),
      "invested_trade_count":len(trades),
      "filled_pct":round(100*sum(r["filled"] for r in portfolio)/max(1,sum(r["selected"] for r in portfolio)),2),
      "fees_eur":2*len(trades),"stop_exits":sum(t["exit_reason"].startswith("stop") for t in trades),
      "trend_crash_review_exits":sum(t["exit_reason"]=="trend_crash_review_next_open" for t in trades),
      "periods":len(indices),"period_outperformance_matched_pct":
            round(100*sum(x>y for x,y in zip(returns,paired))/len(returns),2),
      "mean_deployed_fraction_at_open":round(statistics.mean(r["filled"]/MAX_POSITIONS for r in portfolio),4)
    }
    return out,portfolio,trades

def direct_pair(a,b,model):
    delta=[r["block_return"]-s["block_return"] for r,s in zip(a,b)]
    return {"compared":"paired period returns, "+model,
        "n":len(delta),"average_20d_ppts":round(statistics.mean(delta)*100,4),
        "moving_block_95pct_ppts":bootstrap(delta,seed=SEED+42),
        "nw":newey_west(delta),
        "better_period_pct":round(100*sum(x>0 for x in delta)/len(delta),2)}

def main():
    start=time.monotonic()
    print("RESEARCH_LOCKED_POLICY",json.dumps({
      "signal_start":SIGNALS_FROM,"end":LATEST_SIGNAL,"stop":STOP_ATR,"limit":ENTRY_ATR,
      "days":HOLD_DAYS,"pending":PENDING_DAYS,"market":"ACWI",
      "fee_EUR_side":BROKER_EUR,"slippage_side":SLIP,"models":MODELS
    }),flush=True)
    universe=fixed_universe()
    print("UNIVERSE_CURRENT_SURVIVORS",len(universe),flush=True)
    raw={}
    errors={}
    with ThreadPoolExecutor(max_workers=9) as pool:
        tasks={pool.submit(get_price,t):t for t in list(dict.fromkeys(universe+[BENCH]))}
        for ix,fut in enumerate(as_completed(tasks),1):
            try:t,h,e=fut.result()
            except Exception as ex:t,h,e=tasks[fut],None,str(ex)[:150]
            if h:raw[t]=prepare(h)
            else:errors[t]=e
            if ix%50==0:print("HISTORY",ix,"of",len(tasks),"accepted",len(raw),flush=True)
    if BENCH not in raw or len(raw)<MIN_HISTORIES:
        raise RuntimeError("Insufficient histories: "+str(len(raw))+", ACWI: "+str(BENCH in raw))
    foreign=sum(t!=BENCH and "." in t for t in raw)
    if foreign<MIN_NONUS:raise RuntimeError("Too few non-US listings: "+str(foreign))
    fx,fx_details=fx_rates(set(h["currency"] for h in raw.values()))
    # Keep only FX-confirmed histories to prevent country coverage exaggeration.
    usable={}
    for t,h in raw.items():
        sample=fx(h["currency"],"2024-06-20")
        if sample:usable[t]=h
        else:errors[t]="Historical FX unavailable for "+h["currency"]
    if BENCH not in usable:raise RuntimeError("ACWI FX missing")
    benchmark=usable[BENCH]
    calendar=[d for d in benchmark["days"] if SIGNALS_FROM<=d<=DATE_END]
    chron=[i for i in range(0,len(calendar)-HOLD_DAYS,REBALANCE_STRIDE)
           if calendar[i]<=LATEST_SIGNAL]
    if len(chron)<45:raise RuntimeError("Too few chronological 20d blocks")
    signal_dates={calendar[i] for i in chron}
    # Random overlapping cohorts are supplemental only and do not contribute to
    # the compounded portfolio returns or statistical p-values.
    rng=random.Random(SEED)
    eligible=[i for i in range(len(calendar)-HOLD_DAYS) if calendar[i]<=LATEST_SIGNAL]
    randomized=sorted(rng.sample(eligible,min(len(eligible),RANDOM_DATES)))
    signal_dates|={calendar[i] for i in randomized}
    ranks={}
    eligible_counts=[]
    for day in sorted(signal_dates):
        benchmark_features=features(BENCH,benchmark,day,fx,market=True)
        market_ok=bool(benchmark_features and not benchmark_features["crash"] and benchmark_features["trend"]>=0)
        candidates=[]
        for t,h in usable.items():
            if t==BENCH:continue
            result=features(t,h,day,fx)
            if result:candidates.append(result)
        eligible_counts.append(len(candidates))
        ranks[day]={"unfiltered":pick(candidates.copy(),False,market_ok),
                    "filtered":pick(candidates.copy(),True,market_ok),
                    "market_ok":market_ok,"eligible_count":len(candidates)}
    if statistics.median(eligible_counts)<35:raise RuntimeError("Historical universe too small for ranking")
    curves={};trades_out={};complete={}
    for name in MODELS:
        result,curve,trades=summarize(name,chron,calendar,ranks,usable,fx)
        complete[name]=result;curves[name]=curve
        trades_out[name]=trades
        print("MODEL",name,"end",result["capital_final_eur"],"matched",result["matched_ACWI_final_eur"],
              "trades",result["invested_trade_count"],"stops",result["stop_exits"],flush=True)
    train=[i for i in chron if calendar[min(i+HOLD_DAYS,len(calendar)-1)]<TEST_FROM]
    later=[i for i in chron if calendar[i]>=TEST_FROM]
    sub={}
    for label,chosen in (("earlier",train),("later",later)):
        sub[label]={}
        if len(chosen)<10:continue
        for name in MODELS:
            summary,_,_=summarize(name,chosen,calendar,ranks,usable,fx)
            sub[label][name]=summary
    paired={}
    pairs=[
      ("momentum_limit","momentum_market","ATR buy-limit vs market entry, same unfiltered momentum picks"),
      ("momentum_limit_stop","momentum_limit","ATR initial stop increment, same momentum entries"),
      ("filtered_market","momentum_market","Trend/market/crash entry and exit filters, market entries"),
      ("filtered_limit","filtered_market","1 ATR entry limit increment with trend/crash filters"),
      ("filtered_limit_stop","filtered_limit","2.5 ATR protective stop increment with trend/crash filters"),
      ("filtered_limit_stop","momentum_market","Full complex current proposed rules vs simple momentum"),
      ("filtered_limit_stop","momentum_limit_stop","Trend/market/crash filter increment on original ATR signals"),
      ("filtered_market_stop","filtered_market","Initial 2.5 ATR stop at market entry")
    ]
    for a,b,label in pairs:
        paired[a+" VS "+b]=direct_pair(curves[a],curves[b],label)
    # Fully invested passive ACWI: rebalance positions in this experiment at
    # every 20-day block; fee/slippage each entry and exit; truly passive ETF
    # buy-and-hold would have *lower* trading costs than this comparator.
    acwi_cap=START_CASH;acwi_path=[]
    for i in chron:
        r=benchmark_20(i,calendar,benchmark,fx,acwi_cap)
        if r is None:raise RuntimeError("ACWI block missing "+calendar[i])
        acwi_cap*=1+r
        acwi_path.append(r)
    # Separate one-time buy and hold ACWI price path (dividend adjusted) as
    # stricter longer-horizon passive comparator, no spurious monthly orders.
    start_d=calendar[chron[0]+1];end_d=calendar[chron[-1]+HOLD_DAYS]
    o=benchmark["bars"][start_d][0];c=benchmark["bars"][end_d][3]
    initial_eur=o*fx(benchmark["currency"],start_d)*(1+SLIP)
    qty=(START_CASH-BROKER_EUR)/initial_eur
    acwi_hold=qty*c*fx(benchmark["currency"],end_d)*(1-SLIP)-BROKER_EUR
    # Sensitivity without *reoptimising* signals: same exact stock universe/
    # selection/rules, only alternative execution slippage.
    slippages={}
    for sl in (0.0,.001,.003):
        for name in ("filtered_market","filtered_limit","filtered_limit_stop"):
            x,_,_=summarize(name,chron,calendar,ranks,usable,fx,slippage=sl)
            slippages[f"{name}|slippage_{sl}"]=x["capital_final_eur"]
    report={
       "date":"2026-10-31",
       "run_kind":"research_not_production",
       "test_design":"fixed rules; 20-session nonoverlapping sequential cohorts, 10 equal-capital seats, empty pending seats in cash",
       "params":{"seed":SEED,"limit_atr":ENTRY_ATR,"stop_atr":STOP_ATR,
         "entry_window_sessions":PENDING_DAYS,"max_hold_sessions":HOLD_DAYS,
         "fee_eur_per_order":BROKER_EUR,"slippage_per_side":SLIP,
         "market_proxy":BENCH,"trend_window":200,"momentum_start_lag":252,
         "momentum_end_lag":42,"correction_21d":-.08,"correction_252peak":-.15,
         "crash_21d":-.15,"crash_252peak":-.25},
       "period":{"start":SIGNALS_FROM,"last_signal":LATEST_SIGNAL,
           "last_trade_exit":end_d,"chronological_blocks":len(chron),
           "earlier_blocks":len(train),"later_blocks":len(later),"not_truly_unseen":True},
       "sample":{"current_surviving_universe_tickers":len(universe),
         "stock_histories_ok":len(usable)-1,"historical_foreign_listings":foreign,
         "FX":fx_details,
         "median_eligible_per_signal":statistics.median(eligible_counts),
         "min_eligible_per_signal":min(eligible_counts),
         "max_eligible_per_signal":max(eligible_counts),
         "stock_quote_errors":errors},
       "models":complete,
       "matched_pairs":paired,
       "subperiods":sub,
       "passive_ACWI":{
         "one_time_buy_and_hold_end_eur":round(acwi_hold,2),
         "one_time_buy_and_hold_return_pct":round((acwi_hold/START_CASH-1)*100,3),
         "every_20d_repurchase_end_eur":round(acwi_cap,2),
         "every_20d_repurchase_return_pct":round((acwi_cap/START_CASH-1)*100,3)
       },
       "slippage_sensitivity":slippages,
       "research_cautions":[
         "2026 survivors ONLY; historical bankruptcies, delistings, changing broker universe omitted",
         "Sample of world tickers selected today; no academically valid full global stock universe",
         "Yahoo adjusted OHLC can be revised later, and is not a point-in-time security master",
         "5-session pending limit and 20-session max hold are assumptions not actually specified in app",
         "Displayed app ATR levels are illustrative. Exit reviews are not automated actions in app",
         "A backtest assuming automatic exit after warnings cannot be called returns of existing app",
         "Daily OHLC cannot order events within day; same-day purchase/stop handled conservatively",
         "Adjusted OHLC synthetic share units approximate splits/dividend reinvestment, not exact live orders",
         "EUR historical reference FX, not broker quoted bid/ask at transaction instant",
         "No Austrian KESt, no trading tax, market impact, fractional stock corporate-action settlement",
         "Transaction fees 1 EUR per side and assumed 0.1pct slippage per side",
         "No independent genuinely unseen period; 2024–26 labeled later only",
         "Rolling/random samples overlapping; significance uses chronological 20-session blocks",
         "At most 10 equal seats per block, cash on nonfilled orders; no interest on cash"
       ],
       "cost_research":"0.0%, 0.1%, 0.3% per side slippage; broker commission always 1 EUR/side",
       "statistical_method":"paired per-20-session excess returns; 3-block circular bootstrap 2500 resamples and HAC Newey-West 3 lags. No multiple-testing discovery claim.",
       "elapsed_seconds":round(time.monotonic()-start,1),
       "sources":{"prices":"Yahoo Finance historical charts with current adjusted OHLC",
         "FX":"Frankfurter 2020-2026, EUR base","universe":"Nasdaq Trader current and Adanos current listing universe",
         "broker":"EUR1/order and 0.1% assumed slippage; not verified real historical Trade Republic availability"}
    }
    OUT.joinpath("current_trading_rules_report.json").write_text(json.dumps(report,ensure_ascii=False,indent=2))
    OUT.joinpath("curve_20d_blocks.json").write_text(json.dumps(curves,ensure_ascii=False,indent=2))
    OUT.joinpath("trade_details.json").write_text(json.dumps(trades_out,ensure_ascii=False,indent=2))
    compact={n:{k:v[k] for k in ("capital_final_eur","return_pct","cagr_pct","matched_ACWI_final_eur","mean_20day_excess_matched_pct","excess_matched_bootstrap_95pct_mean20d","matched_newey_west","invested_trade_count","stop_exits")} for n,v in complete.items()}
    print("CURRENT_RULES_RESULTS="+json.dumps({
        "sample":{k:report["sample"][k] for k in ("current_surviving_universe_tickers","stock_histories_ok","historical_foreign_listings","median_eligible_per_signal")},
        "period":report["period"],"models":compact,"matched_pairs":paired,
        "passive_ACWI":report["passive_ACWI"],
        "slippage_sensitivity":slippages,
        "elapsed_seconds":report["elapsed_seconds"]
    },separators=(",",":")),flush=True)
if __name__=="__main__":main()
