#!/usr/bin/env python3
"""Research-only historical counterfactual for Bottleneck Lab's CURRENT price strategy.

Non-negotiable limitations:
- 2026 *surviving* US listings and current curated tickers: cannot claim
  point-in-time investable market/broker universe. Not fully survivorship-bias-free.
- Market data downloaded now but ALL decision inputs strictly <= historical signal day.
- Signals match existing app: score=clamp(50+180*60d momentum - 80*(ATR14/close),0,100).
  Buy limit = decision close - ATR14; stop = buy - 2.5*ATR14.
- Entry follows signal day (never at that signal-day close); five-session limit window;
  stop assumed executable at/below stop with adverse slippage/gap; max exit signal+20 sessions.
- EUR conversion uses historical FX on each fill/exit (not present-day rates).
- Each one-way order costs EUR1. No taxes, financing, interest, or dividends on stocks.
- Random dates are separate *overlapping cohort experiments*, NOT one compounded account.
- Additional non-overlapping chronological test assesses implementable capital.
- No model tuning against results; fixed seed specified BEFORE data retrieval.
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
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

START=date(2021,11,1)
LAST_SIGNAL=date(2026,9,25)
DATA_START=date(2021,6,1)
DATA_END=date(2026,10,31)
SEED=20261031
RANDOM_DATES=320
COHORT_EUR=10000.0
N_STOCKS=10
ENTRY_LIMIT_ATR=1.0
STOP_ATR=2.5
ENTRY_WINDOW=5
MAX_HORIZON=20
FEE_EUR_PER_SIDE=1.0
SLIP_RATE=.001
BENCHMARK="SPY"
MAX_UNIVERSE=225
WORKERS=8
OUT=Path("research/results")
OUT.mkdir(parents=True,exist_ok=True)
HTTP_HEADERS={"User-Agent":"Mozilla/5.0","Accept":"application/json,text/csv,text/plain,*/*"}
CURATED="NEX.PA VRT MU FCX CEG XYL ROK RTX ETN AMAT SCCO NRG WTRG EMR LMT GEV NVT LRCX BHP VST AWK HON NOC DELL KLAC RIO NEE ECL PH GD HUBB SMCI ASML TECK DUK IEX CAT HII ANET TSM AA SO PNR DE LHX PWR CSCO AVGO MP EXC AOS FANUY AXON HPE MRVL ALB EIX WTS ZBRA PANW ABB APH NVDA LAC FSLR BMI SYM CRWD GLW AMD CCJ GXO FTNT EQIX QCOM UUUU BWXT UPS DLR ADI WCC MPWR BE POWL TER OKLO GNRC ONTO CRDO SNDK".split()
# US-listed subset only so all trade instruments share USD->EUR reference FX.
CURATED=[s for s in CURATED if "." not in s and s not in {"ABB"}]
DEFINITION_SOURCE="https://github.com/BoraBoraPalm/Bottleneck-Lab-Android/blob/master/scripts/build_snapshot.py"
NASDAQ="https://www.nasdaqtrader.com/dynamic/SymDir/nasdaqlisted.txt"
OTHER="https://www.nasdaqtrader.com/dynamic/SymDir/otherlisted.txt"
FX_URL="https://api.frankfurter.dev/v2/rates?from=2021-06-01&to=2026-10-31&base=USD&quotes=EUR"

def download(url, timeout=20, max_bytes=4000000):
    req=urllib.request.Request(url,headers=HTTP_HEADERS)
    with urllib.request.urlopen(req,timeout=timeout) as r:
        if r.status != 200:raise ValueError("HTTP "+str(r.status))
        body=r.read(max_bytes+1)
    if len(body)>max_bytes:raise ValueError("Too large")
    return body

def directory():
    all_names=set(CURATED)
    for url,is_nasdaq in [(NASDAQ,True),(OTHER,False)]:
        raw=download(url,timeout=20).decode("utf-8-sig","replace")
        rows=csv.DictReader(io.StringIO(raw),delimiter="|")
        found=0
        for r in rows:
            t=(r.get("Symbol") if is_nasdaq else r.get("ACT Symbol")) or ""
            t=t.strip()
            name=(r.get("Security Name") or "").lower()
            if not t.isalpha() or len(t)>5 or len(t)<1:continue
            if r.get("ETF")=="Y" or r.get("Test Issue")=="Y":continue
            if not is_nasdaq and r.get("Exchange") not in ("N","A","V"):continue
            if any(x in name for x in ("warrant","preferred","depositary shares","right to","units represent","etf","etn","notes due","etf trust","mutual fund")):continue
            all_names.add(t);found+=1
        print("Directory",url,found,flush=True)
    extras=sorted((x for x in all_names if x not in CURATED),key=lambda x:hashlib.sha256((str(SEED)+":"+x).encode()).hexdigest())
    universe=list(dict.fromkeys(CURATED+extras[:max(0,MAX_UNIVERSE-len(CURATED))]))
    print("Universe",len(universe),"curated",len(CURATED),", hash-sampled",len(universe)-len(CURATED),flush=True)
    return universe

def get_yahoo(t):
    last=""
    now=int(datetime(2026,11,1,tzinfo=timezone.utc).timestamp())
    begin=int(datetime(2021,5,25,tzinfo=timezone.utc).timestamp())
    for host in ("query1.finance.yahoo.com","query2.finance.yahoo.com"):
        try:
            url=f"https://{host}/v8/finance/chart/{urllib.parse.quote(t,safe='')}?period1={begin}&period2={now}&interval=1d"
            obj=json.loads(download(url,timeout=17,max_bytes=1250000))
            result=obj["chart"]["result"][0]
            if result.get("meta",{}).get("currency") not in ("USD",None):
                raise ValueError("Non-USD exchange quote")
            q=result["indicators"]["quote"][0]
            adj=result["indicators"].get("adjclose",[{}])[0].get("adjclose",[])
            bars={}
            for i,tm in enumerate(result.get("timestamp",[])):
                try:
                    d=datetime.fromtimestamp(tm,timezone.utc).date()
                    if d<DATA_START or d>DATA_END:continue
                    o,h,l,c,v=(float(q[k][i]) for k in ("open","high","low","close","volume"))
                    if not all(math.isfinite(x) for x in (o,h,l,c,v)) or min(o,h,l,c)<=0 or h<l or v<0:continue
                    ad=float(adj[i]) if i<len(adj) and adj[i] is not None else c
                    bars[d.isoformat()]=[o,h,l,c,v,ad]
                except (ValueError,TypeError,KeyError,IndexError):continue
            if len(bars)<90:raise ValueError(f"Short data: {len(bars)}")
            return bars,"Yahoo",None
        except Exception as e:
            last=str(e)[:140]
    # historical Stooq fallback, no verified adjusted closes/dividends
    try:
        args=urllib.parse.urlencode({"s":t.lower()+".us","d1":"20210525","d2":"20261031","i":"d"})
        raw=download("https://stooq.com/q/d/l/?"+args,timeout=20,max_bytes=300000).decode("utf-8-sig","replace")
        bars={}
        for r in csv.DictReader(io.StringIO(raw)):
            try:
                d=r["Date"]
                if d<"2021-06-01" or d>"2026-10-31":continue
                o,h,l,c,v=[float(r[k]) for k in ("Open","High","Low","Close","Volume")]
                if min(o,h,l,c)<=0 or v<0 or h<l:continue
                bars[d]=[o,h,l,c,v,c]
            except (KeyError,ValueError,TypeError):continue
        if len(bars)<90:raise ValueError(f"Short Stooq: {len(bars)}")
        return bars,"Stooq",None
    except Exception as e:
        return None,None,f"Yahoo {last}; Stooq {str(e)[:90]}"

def fx_history():
    obj=json.loads(download(FX_URL,timeout=25,max_bytes=700000))
    if not isinstance(obj,list):raise RuntimeError("Expected Frankfurter v2 list of dated rates")
    fx={}
    for r in obj:
        if r.get("base")=="USD" and r.get("quote")=="EUR":
            try:
                d=r["date"];x=float(r["rate"])
                if x>0 and math.isfinite(x):fx[d]=x
            except (KeyError,ValueError,TypeError):pass
    if len(fx)<1050:raise RuntimeError(f"Historical EUR/USD FX has only {len(fx)} points")
    dates=sorted(fx)
    def rate(d):
        i=bisect_right(dates,d)-1
        if i<0:raise RuntimeError("No FX rate before "+d)
        return fx[dates[i]]
    return rate,len(fx)

def signals_on(ticker,hist,index,day):
    """All features strictly from daily bars dated <= decision day."""
    if day not in index:return None
    i=index[day]
    if i<60:return None
    bars=hist
    # No future data requirement beyond the signal itself.
    v=bars[i];prev60=bars[i-60]
    c=v[3];momentum=c/prev60[3]-1
    trs=[max(bars[j][1]-bars[j][2],abs(bars[j][1]-bars[j-1][3]),abs(bars[j][2]-bars[j-1][3]))
         for j in range(i-13,i+1)]
    atr=sum(trs)/14
    avg_usd_turnover=sum(bars[j][3]*bars[j][4] for j in range(i-19,i+1))/20
    if c<5 or avg_usd_turnover<5000000 or atr<=0 or not math.isfinite(momentum):return None
    score=round(max(0,min(100,50+180*momentum-80*(atr/c))),1)
    return (score,ticker,c,atr,momentum,avg_usd_turnover)

def day_maps(series):
    return {"dates":sorted(series),"bars":[series[d] for d in sorted(series)]}

def make_dataset(raw):
    histories={}
    for ticker,(bars,src) in raw.items():
        h=day_maps(bars)
        h["index"]={d:i for i,d in enumerate(h["dates"])}
        h["source"]=src
        histories[ticker]=h
    return histories

def precompute_signal_ranks(histories,calendar):
    """No use of 2026 scores to choose historical winners, only historical prior bars."""
    daily={}
    for d in calendar:
        rows=[]
        for t,h in histories.items():
            x=signals_on(t,h["bars"],h["index"],d)
            if x:rows.append(x)
        rows.sort(key=lambda r:(-r[0],r[1]))
        daily[d]=rows[:N_STOCKS]
    return daily

def trade(signal,signal_idx,days,h,fx,stake,slip=SLIP_RATE):
    """One EUR-funded daily stock order. Conservative same-bar stop convention."""
    score,ticker,close,atr,mom,adv=signal
    limit=close-ENTRY_LIMIT_ATR*atr
    stop=limit-STOP_ATR*atr
    if stop<=0 or limit<=0:return None
    end=min(signal_idx+MAX_HORIZON,len(days)-1)
    if signal_idx+1>end:return None
    bought=False
    fill=None
    for j in range(signal_idx+1,min(signal_idx+ENTRY_WINDOW,end)+1):
        d=days[j]
        if d not in h["index"]:continue
        b=h["bars"][h["index"][d]]
        open_,high,low,close_,volume,adj=b
        if not bought:
            if low>limit:continue
            # If open already crossed limit, a limit order is marketable at open.
            raw_buy=min(open_,limit)
            fx_buy=fx(d)
            ask_eur=raw_buy*(1+slip)*fx_buy
            quantity=math.floor((stake-FEE_EUR_PER_SIDE)/ask_eur)
            if quantity<=0:return None
            spent=quantity*ask_eur+FEE_EUR_PER_SIDE
            fill={"buy_date":d,"buy_usd":raw_buy,"buy_eur":ask_eur,
                  "shares":quantity,"spent":spent,"buy_fee":FEE_EUR_PER_SIDE}
            bought=True
        # If daily low hits a stop on the entry date, pessimistically assume stop
        # happens AFTER purchase regardless of the unknown intraday sequence.
        if bought:
            # Gap exit only makes sense for subsequent days; on buy day set worst
            # modeled stop if stop reached; avoids impossible pre-entry sells.
            if low<=stop:
                px=min(open_,stop) if d!=fill["buy_date"] else stop
                sell_eur=px*(1-slip)*fx(d)
                proceeds=quantity*sell_eur-FEE_EUR_PER_SIDE
                out={**fill,"ticker":ticker,"signal_date":days[signal_idx],
                     "signal_score":score,"exit_date":d,"exit_reason":"stop",
                     "stop_price_usd":stop,"limit_price_usd":limit,
                     "sell_eur":sell_eur,"sell_fee":FEE_EUR_PER_SIDE,
                     "proceeds":proceeds,"pnl_eur":proceeds-spent,
                     "return_on_allocated":(proceeds-spent)/stake}
                return out
    if not bought:return None
    # Continue tracking stop from first available bar AFTER the buy day.
    buy_j=days.index(fill["buy_date"])
    for j in range(buy_j+1,end+1):
        d=days[j]
        if d not in h["index"]:continue
        o,high,low,c,vol,adj=h["bars"][h["index"][d]]
        if low<=stop:
            px=min(o,stop)
            kind="stop_gap" if o<stop else "stop"
        elif j==end:
            px=c
            kind="time_exit"
        else:
            continue
        proceeds=fill["shares"]*px*(1-slip)*fx(d)-FEE_EUR_PER_SIDE
        return {**fill,"ticker":ticker,"signal_date":days[signal_idx],
                "signal_score":score,"exit_date":d,"exit_reason":kind,
                "stop_price_usd":stop,"limit_price_usd":limit,
                "sell_eur":px*(1-slip)*fx(d),"sell_fee":FEE_EUR_PER_SIDE,
                "proceeds":proceeds,"pnl_eur":proceeds-fill["spent"],
                "return_on_allocated":(proceeds-fill["spent"])/stake}
    return None # Do not invent a sell price when a quoted ticker vanished.

def benchmark_cohort(day_idx,days,h_spy,fx,capital,slip=SLIP_RATE):
    entry_day=days[day_idx+1];exit_day=days[day_idx+MAX_HORIZON]
    open_=h_spy["bars"][h_spy["index"][entry_day]][0]
    end_b=h_spy["bars"][h_spy["index"][exit_day]]
    px=end_b[3]
    buy=open_*fx(entry_day)*(1+slip)
    qty=math.floor((capital-1)/buy)
    if qty<=0:raise ValueError("Cannot buy benchmark")
    # Reinvest SPY dividend distributions via adjusted-close factor, if from
    # Yahoo on both dates; otherwise use price-only. Approximation for entry at open.
    ent=h_spy["bars"][h_spy["index"][entry_day]]
    ratio_entry=ent[5]/ent[3] if ent[3]>0 else 1
    ratio_exit=end_b[5]/end_b[3] if end_b[3]>0 else 1
    divmult=ratio_exit/ratio_entry
    terminal_eur=qty*px*divmult*fx(exit_day)*(1-slip)-1
    profit=terminal_eur-(qty*buy+1)
    return profit,qty,divmult

def cohort(day_idx,days,ranks,hists,fx,capital,slip=SLIP_RATE):
    d=days[day_idx]
    ranked=ranks[d]
    trades=[];missing=[]
    for x in ranked:
        t=x[1]
        tr=trade(x,day_idx,days,hists[t],fx,capital/N_STOCKS,slip)
        if tr:trades.append(tr)
        else:missing.append(t)
    pnl=sum(t["pnl_eur"] for t in trades)
    bench,_,_ = benchmark_cohort(day_idx,days,hists["SPY"],fx,capital,slip)
    return {"signal_date":d,"initial_eur":capital,"strategy_pnl_eur":pnl,
            "strategy_return_pct":pnl/capital*100,"benchmark_pnl_eur":bench,
            "benchmark_return_pct":bench/capital*100,"excess_return_pct":(pnl-bench)/capital*100,
            "selected":len(ranked),"filled":len(trades),"unfilled":len(missing),
            "trades":trades}

def pct(x):return round(x,4)
def summarize(cohorts):
    rets=[x["strategy_return_pct"] for x in cohorts]
    bench=[x["benchmark_return_pct"] for x in cohorts]
    excess=[x["excess_return_pct"] for x in cohorts]
    trades=[t for x in cohorts for t in x["trades"]]
    return {
        "n_decision_dates":len(cohorts),"sample_trades":len(trades),
        "limit_order_fill_rate_pct":pct(100*len(trades)/max(1,sum(c["selected"] for c in cohorts))),
        "mean_20d_strategy_pct":pct(statistics.mean(rets)),
        "median_20d_strategy_pct":pct(statistics.median(rets)),
        "mean_20d_spy_pct":pct(statistics.mean(bench)),
        "mean_20d_excess_pct":pct(statistics.mean(excess)),
        "strategy_positive_cohorts_pct":pct(100*sum(x>0 for x in rets)/len(rets)),
        "trades_won_pct":pct(100*sum(t["pnl_eur"]>0 for t in trades)/max(1,len(trades))),
        "total_trade_pnl_eur_across_INDEPENDENT_cohorts":pct(sum(t["pnl_eur"] for t in trades)),
        "total_fees_eur_across_independent_cohorts":pct(len(trades)*2),
        "stop_trades":sum(t["exit_reason"].startswith("stop") for t in trades),
        "avg_trade_profit_eur":pct(statistics.mean(t["pnl_eur"] for t in trades)) if trades else None,
        "cohort_5pct_return":pct(sorted(rets)[int(len(rets)*.05)]),
        "cohort_95pct_return":pct(sorted(rets)[min(len(rets)-1,int(len(rets)*.95))])
    }

def percentile(vals,p):
    vals=sorted(vals)
    z=(len(vals)-1)*p
    i=int(z);f=z-i
    return vals[i]*(1-f)+vals[min(len(vals)-1,i+1)]*f

def block_bootstrap(excess,seed=SEED,n=3000):
    # NONOVERLAPPING chronological blocks, NOT overlapping 320 cohorts:
    # Bootstrap period excess returns, approximate, no independence guarantee.
    rg=random.Random(seed+81)
    means=[]
    for _ in range(n):
        xs=[excess[rg.randrange(len(excess))] for _ in excess]
        means.append(statistics.mean(xs))
    return [pct(percentile(means,.025)),pct(percentile(means,.975))]

def capital_path(days,ranks,hists,fx):
    # Non-overlap: new cohort starts every 20 sessions, invest up to 10 positions
    # per cohort; final profits/cash released before next cohort.
    first=next(i for i,d in enumerate(days) if d>=START.isoformat())
    capital=10000.;benchmark_cap=10000.
    rows=[];all_trades=[]
    for i in range(first,len(days)-MAX_HORIZON,MAX_HORIZON):
        d=days[i]
        if date.fromisoformat(d)>LAST_SIGNAL:break
        group=cohort(i,days,ranks,hists,fx,capital)
        # benchmark returns percentage for same calendar period, but calculated
        # on benchmark_cap, avoids sharing strategy capital between portfolios.
        b_pnl,_,_=benchmark_cohort(i,days,hists["SPY"],fx,benchmark_cap)
        capital+=group["strategy_pnl_eur"]
        benchmark_cap+=b_pnl
        all_trades.extend(group["trades"])
        rows.append({"date":d,"strategy_equity_eur":pct(capital),
            "benchmark_equity_eur":pct(benchmark_cap),"strategy_period_return_pct":group["strategy_return_pct"],
            "benchmark_period_return_pct":pct(b_pnl/(benchmark_cap-b_pnl)*100),
            "fills":len(group["trades"]),"selected":group["selected"]})
    peak=10000
    mdd=0
    for r in rows:
        peak=max(peak,r["strategy_equity_eur"])
        mdd=min(mdd,r["strategy_equity_eur"]/peak-1)
    annual_years=(date.fromisoformat(rows[-1]["date"])-date.fromisoformat(rows[0]["date"])).days/365.2425 if len(rows)>1 else 1
    nret=[r["strategy_period_return_pct"] for r in rows]
    bex=[r["benchmark_period_return_pct"] for r in rows]
    exces=[a-b for a,b in zip(nret,bex)]
    return rows,all_trades,{
        "initial_capital_eur":10000,
        "final_capital_eur":pct(capital),
        "absolute_pnl_eur":pct(capital-10000),
        "total_return_pct":pct((capital/10000-1)*100),
        "annualised_pct_approx":pct((capital/10000)**(1/annual_years)*100-100) if capital>0 else -100,
        "spy_initial_eur":10000,
        "spy_final_eur":pct(benchmark_cap),
        "spy_pnl_eur":pct(benchmark_cap-10000),
        "spy_total_return_pct":pct((benchmark_cap/10000-1)*100),
        "n_nonoverlapping_periods":len(rows),
        "trade_count":len(all_trades),
        "total_commissions_eur":pct(2*len(all_trades)),
        "max_block_end_drawdown_pct":pct(mdd*100),
        "mean_20d_excess_pct":pct(statistics.mean(exces)),
        "bootstrap_95pct_mean_20d_excess_pct":block_bootstrap(exces),
        "periods_outperform_spy_pct":pct(100*sum(a>b for a,b in zip(nret,bex))/len(rows))
    }

def csv_save(path,rows,keys):
    with open(path,"w",newline="",encoding="utf-8") as f:
        w=csv.DictWriter(f,fieldnames=keys,extrasaction="ignore");w.writeheader();w.writerows(rows)

def main():
    t0=time.time()
    universe=directory()
    collected={}
    failed={}
    with ThreadPoolExecutor(max_workers=WORKERS) as pool:
        tasks={pool.submit(get_yahoo,t):t for t in universe+["SPY"]}
        for i,f in enumerate(as_completed(tasks)):
            t=tasks[f]
            try:bars,src,err=f.result()
            except Exception as e:bars,src,err=None,None,str(e)
            if bars:collected[t]=(bars,src)
            else:failed[t]=err
            if (i+1)%35==0:print("Price downloads",i+1,"/",len(tasks),"success",len(collected),flush=True)
    if "SPY" not in collected:raise RuntimeError("SPY benchmark missing")
    if len(collected)<70:raise RuntimeError(f"Only {len(collected)} of {len(universe)} stocks retrieved, insufficient sample.")
    hists=make_dataset(collected)
    days=[d for d in hists["SPY"]["dates"] if START.isoformat()<=d<=DATA_END.isoformat()]
    # Stop signal days before last trading period by 20 sessions.
    eligible=[i for i,d in enumerate(days[:-MAX_HORIZON]) if date.fromisoformat(d)<=LAST_SIGNAL]
    if len(eligible)<300:raise RuntimeError("Too few trade days")
    rng=random.Random(SEED)
    chosen=sorted(rng.sample(eligible,RANDOM_DATES))
    print("Chosen",len(chosen),"random dates",days[chosen[0]],days[chosen[-1]],flush=True)
    fx,n_fx=fx_history()
    ranks=precompute_signal_ranks(hists,days)
    cohorts=[cohort(i,days,ranks,hists,fx,COHORT_EUR) for i in chosen]
    if any(x["selected"]<3 for x in cohorts):
        print("WARNING: Some dates have <3 eligible names; record as limitation",flush=True)
    sample_stats=summarize(cohorts)
    path,trades,portfolio=capital_path(days,ranks,hists,fx)
    fail_source=dict(Counter(h["source"] for h in hists.values()))
    sensitivity={}
    for sl in (0,.0025):
        sensitivity[str(round(sl*100,2))+"pct_per_side"] = summarize([cohort(i,days,ranks,hists,fx,COHORT_EUR,slip=sl) for i in chosen])
    data={
      "strategy":"Actual v4 60d momentum/ATR price-only ranking; 1 ATR buy limit, 2.5 ATR stop, 5-session GTC limit, 20-session horizon",
      "five_year_window":["2021-11-01","2026-10-30"],
      "last_signal_day":LAST_SIGNAL.isoformat(),
      "fixed_random_seed":SEED,
      "sampled_dates":RANDOM_DATES,
      "universe_construction":"2026 active US exchange directories plus current curated US subset, hash-random supplementary stocks; SURVIVORSHIP BIAS, NOT point-in-time",
      "available_now_tickers":len(universe),
      "historical_price_success":len(collected)-1,
      "historical_price_failed_count":len(failed),
      "historical_price_failed_symbols":failed,
      "historical_sources":fail_source,
      "historical_fx_days":n_fx,
      "currency":"EUR via date-specific USD/EUR history",
      "capital_eur_each_random_experiment":COHORT_EUR,
      "transaction_costs_eur":{"buy":FEE_EUR_PER_SIDE,"sell":FEE_EUR_PER_SIDE},
      "adverse_slippage_per_side_pct":100*SLIP_RATE,
      "dividend_approach":"Individual-stock price-only P&L excludes dividends. SPY uses adjusted-close factor for approximate total-return benchmark; market price fills unadjusted.",
      "random_decision_date_results":sample_stats,
      "nonoverlapping_capital_path":portfolio,
      "sensitivity_random_dates":sensitivity,
      "interpretation":"Neither a point-in-time broker/universe replication nor a statistically credible claim of excess return due to survivorship bias and absent de-listed stocks.",
      "test_last_run_utc":datetime.now(timezone.utc).isoformat(),
      "elapsed_seconds":round(time.time()-t0,1)
    }
    with open(OUT/"report.json","w",encoding="utf-8") as f:json.dump(data,f,ensure_ascii=False,indent=2)
    group_rows=[]
    keys=["signal_date","initial_eur","strategy_pnl_eur","strategy_return_pct","benchmark_pnl_eur","benchmark_return_pct","excess_return_pct","selected","filled","unfilled"]
    for c in cohorts:group_rows.append({k:round(v,4) if isinstance(v,float) else v for k,v in c.items() if k!="trades"})
    csv_save(OUT/"random_320_cohorts.csv",group_rows,keys)
    all_entries=[t for c in cohorts for t in c["trades"]]
    csv_save(OUT/"random_all_trades.csv",all_entries,list(all_entries[0]) if all_entries else [])
    csv_save(OUT/"chronological_equity.csv",path,list(path[0]))
    csv_save(OUT/"chronological_trades.csv",trades,list(trades[0]) if trades else [])
    # Reproducible selection of sample dates and source provenance.
    with open(OUT/"data_coverage.json","w") as f:
        json.dump({"chosen_universe":universe,"found_history":sorted(collected),"failed":failed,
                   "dates":sorted(days[i] for i in chosen)},f,indent=2)
    print("RESULTS_JSON="+json.dumps({"random":sample_stats,"chronological":portfolio,"source":fail_source,
                                  "failed":len(failed),"runtime_s":round(time.time()-t0,1)},separators=(",",":")),flush=True)
if __name__=="__main__":main()
