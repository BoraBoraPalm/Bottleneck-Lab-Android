#!/usr/bin/env python3
"""POINT-IN-TIME FINANCIAL DATA PROTOTYPE, not unbiased investable-universe backtest.

Caution:
 - All stock symbols come from the CURRENT 2026 QVM-supported universe => severe
   survivorship/coverage selection. This is NOT a proof of alpha or a historic TR universe.
 - SEC facts can only enter a signal when their 10-K/10-K/A "filed" date <= decision date.
 - Prices/signals from strictly preceding closes; entry only following trading day.
 - Compare fixed (not selected on outcome) QVM 1/3 weights to 12-2 momentum and
   original 60-day price score, on exactly the same PIT-QVM eligible stock subset.
 - All executions use EUR with dated historical FX, €1 buy + €1 sell and 0.1%
   unfavorable slippage each side; ordinary equity P&L is price-only.
 - No production app files modified; independent research artifact only.
"""
import json
import math
import random
import statistics
import time
import urllib.parse
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime,date,timedelta,timezone
from pathlib import Path
import backtest_5y as b
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
import multifactor as m

OUT=Path("research/pit_results")
OUT.mkdir(parents=True,exist_ok=True)
PAGES="https://boraborapalm.github.io/Bottleneck-Lab-Android/snapshot.json"
SEC_TICKERS="https://www.sec.gov/files/company_tickers.json"
MAX_UNIVERSE=65
MIN_QVM=8
MIN_LIQ_USD=5_000_000
MIN_PRICE=5
PERIOD_FROM="2021-11-01"
LAST_SIGNAL="2026-09-25"
FIXED_SEED=20261031
N_RANDOM=320

def historical_price(symbol):
    begin=int(datetime(2020,5,20,tzinfo=timezone.utc).timestamp())
    end=int(datetime(2026,11,1,tzinfo=timezone.utc).timestamp())
    last=""
    for host in ("query1.finance.yahoo.com","query2.finance.yahoo.com"):
        try:
            url=f"https://{host}/v8/finance/chart/{urllib.parse.quote(symbol,safe='')}?period1={begin}&period2={end}&interval=1d"
            js=json.loads(b.download(url,timeout=20,max_bytes=2500000))
            r=js["chart"]["result"][0]
            if r.get("meta",{}).get("currency") not in ("USD",None):raise ValueError("Non-USD")
            q=r["indicators"]["quote"][0]
            adjustment=r["indicators"].get("adjclose",[{}])[0].get("adjclose",[])
            out={}
            for i,stamp in enumerate(r.get("timestamp",[])):
                try:
                    d=datetime.fromtimestamp(stamp,timezone.utc).date().isoformat()
                    if not ("2020-06-01"<=d<="2026-10-31"):continue
                    op,hi,lo,cl,vol=(float(q[k][i]) for k in ("open","high","low","close","volume"))
                    if not all(math.isfinite(v) for v in (op,hi,lo,cl,vol)) or min(op,hi,lo,cl)<=0 or hi<lo or vol<0:continue
                    adj=float(adjustment[i]) if i<len(adjustment) and adjustment[i] is not None else cl
                    out[d]=[op,hi,lo,cl,vol,adj]
                except (ValueError,KeyError,IndexError,TypeError):continue
            if len(out)<260:raise ValueError("Only "+str(len(out))+" bars")
            return out,None
        except Exception as e:last=str(e)[:150]
    return None,last

def collect():
    snap=json.loads(b.download(PAGES+"?t="+str(int(time.time())),timeout=18,max_bytes=3000000))
    pilot=[x for x in snap.get("stocks",[]) if x.get("multifactor") and x.get("currency")=="USD"
        and x.get("eligible_for_ranking")]
    names=list(dict.fromkeys(x["ticker"] for x in sorted(pilot,key=lambda s:s["ticker"])))[:MAX_UNIVERSE]
    if len(names)<15:raise RuntimeError("Too few current QVM stocks for meaningful diagnostic")
    # The published source URLs already contain the CIK, avoiding a redundant
    # SEC map request. Never infer a CIK from a ticker or company name.
    cikmap={}
    for row in pilot:
        if row["ticker"] not in names:continue
        source=(row.get("fundamentals") or {}).get("source_url","")
        match=__import__("re").search(r"/CIK(\d{10})\.json$",source)
        if match:cikmap[row["ticker"]]=int(match.group(1))
    print("CIK mappings from recorded SEC source",len(cikmap),"of",len(names),flush=True)
    names=[x for x in names if x in cikmap]
    b.HTTP_HEADERS["User-Agent"]="BottleneckLabResearch/0.6 (+https://github.com/BoraBoraPalm/Bottleneck-Lab-Android)"
    data={}
    failures={}
    def get(t):
        bars,err=historical_price(t)
        if not bars:return t,None,None,err
        if t=="SPY":return t,bars,None,None
        url=f"https://data.sec.gov/api/xbrl/companyfacts/CIK{int(cikmap[t]):010d}.json"
        issue=None
        for attempt in range(3):
            try:
                sec=json.loads(b.download(url,timeout=25,max_bytes=20000000))
                return t,bars,sec,None
            except Exception as e:
                issue=e
                time.sleep(2*(attempt+1))
        return t,None,None,str(issue)[:140]
    with ThreadPoolExecutor(max_workers=3) as pool:
        tasks=[pool.submit(get,t) for t in names+["SPY"]]
        for fut in as_completed(tasks):
            t,bars,sec,error=fut.result()
            if bars and (sec or t=="SPY"):data[t]=(bars,sec)
            else:failures[t]=error
    if "SPY" not in data or len(data)<15:raise RuntimeError("Insufficient point-in-time market/SEC history: "+str(len(data)))
    histories=b.make_dataset({t:(bars,"Yahoo") for t,(bars,sec) in data.items()})
    facts={t:sec for t,(bars,sec) in data.items() if sec}
    return histories,facts,failures,len(pilot)

def signal_ranks(i,days,histories,facts):
    day=days[i]
    day_asof=date.fromisoformat(day)
    current=[]
    for t,fact in facts.items():
        h=histories[t]
        base=b.signals_on(t,h["bars"],h["index"],day)
        if not base:continue
        idx=h["index"][day]
        bars=h["bars"]
        if idx<252:continue
        mom=m.momentum_12_2([x[3] for x in bars[:idx+1]])
        if mom is None:continue
        financial=m.sec_fundamentals(fact,day_asof)
        if not financial:continue
        row={"ticker":t,"currency":"USD","close":base[2],
             "momentum_12_2":mom,"eligible_for_ranking":True,
             "fundamentals":financial}
        if not m.metrics_for_row(row,day_asof):continue
        current.append((row,base))
    stocks=[r for r,base in current]
    coverage=len(stocks)
    if coverage<MIN_QVM:return None,coverage
    result=m.assign_multifactor(stocks,as_of=day_asof,min_eligible=MIN_QVM)
    if result["status"]!="experimental":return None,coverage
    qvm=sorted(((r["multifactor"]["score"],r["ticker"]) for r in stocks if r.get("multifactor")),reverse=True)[:10]
    longmom=sorted(((r["momentum_12_2"],r["ticker"]) for r in stocks),reverse=True)[:10]
    by_ticker={x[0]["ticker"]:x[1] for x in current}
    baseline=sorted((base for r,base in current),key=lambda x:(-x[0],x[1]))[:10]
    def trades(names):
        return [by_ticker[t] for _,t in names]
    return {"qvm":trades(qvm),"momentum12_2":trades(longmom),"legacy60d":baseline},coverage

def portfolio(ids,days,rank_map,histories,fx):
    keys=("qvm","momentum12_2","legacy60d")
    caps={k:10000.0 for k in keys}
    matched={k:10000.0 for k in keys}
    by_model={k:{"trades":0,"stop_trades":0,"fees":0,"positive_periods":0} for k in keys}
    trace=[]
    for i in ids:
        date_label=days[i]
        rankings=rank_map[date_label]
        one={"date":date_label}
        for k in keys:
            capital=caps[k]
            trades=[b.trade(signal,i,days,histories[signal[1]],fx,capital/10)
                    for signal in rankings[k]]
            trades=[x for x in trades if x]
            pnl=sum(x["pnl_eur"] for x in trades)
            matched_pnl=sum(b.exposure_matched_spy_trade(t,histories["SPY"],fx) for t in trades)
            caps[k]+=pnl
            matched[k]+=matched_pnl
            by_model[k]["trades"]+=len(trades)
            by_model[k]["fees"]+=2*len(trades)
            by_model[k]["stop_trades"]+=sum(1 for t in trades if t["exit_reason"].startswith("stop"))
            by_model[k]["positive_periods"]+=int(pnl>0)
            one[k+"_end"]=round(caps[k],4)
            one[k+"_filled"]=len(trades)
        trace.append(one)
    summary={k:{"end_eur":round(caps[k],2),"net_eur":round(caps[k]-10000,2),
                "total_return_pct":round((caps[k]/10000-1)*100,3),
                "matched_spy_eur":round(matched[k],2),
                "excess_vs_matched_spy_eur":round(caps[k]-matched[k],2),
                "periods":len(ids),**by_model[k]} for k in keys}
    return summary,trace

def random_dates(ids,days,rank_map,histories,fx):
    rows=[]
    for i in ids:
        ranks=rank_map[days[i]]
        item={"date":days[i],"coverage":len(ranks["qvm"])}
        for k in ("qvm","momentum12_2","legacy60d"):
            orders=[b.trade(x,i,days,histories[x[1]],fx,1000) for x in ranks[k]]
            orders=[x for x in orders if x]
            item[k+"_return_pct"]=100*sum(x["pnl_eur"] for x in orders)/10000
            item[k+"_trades"]=len(orders)
        rows.append(item)
    return rows

def main():
    begun=time.time()
    histories,facts,failures,n_pilot=collect()
    days=[d for d in histories["SPY"]["dates"] if PERIOD_FROM<=d<="2026-10-31"]
    eligible=[i for i,d in enumerate(days[:-b.MAX_HORIZON]) if d<=LAST_SIGNAL]
    chosen=sorted(random.Random(FIXED_SEED).sample(eligible,N_RANDOM))
    first=next(i for i,d in enumerate(days) if d>=PERIOD_FROM)
    chronology=[i for i in range(first,len(days)-b.MAX_HORIZON,b.MAX_HORIZON) if days[i]<=LAST_SIGNAL]
    all_idx=sorted(set(chosen+chronology))
    fx,fx_count=b.fx_history()
    coverage={}
    ranks={}
    for i in all_idx:
        result,n=signal_ranks(i,days,histories,facts)
        coverage[days[i]]=n
        if result:ranks[days[i]]=result
    valid_random=[i for i in chosen if days[i] in ranks]
    valid_chron=[i for i in chronology if days[i] in ranks]
    # No compounding across gaps (each model holds cash); calculate portfolio for
    # valid dates only, report skipped periods and resulting selection effect.
    chronic,curve=portfolio(valid_chron,days,ranks,histories,fx)
    random_rows=random_dates(valid_random,days,ranks,histories,fx)
    train=[i for i in valid_chron if days[i+b.MAX_HORIZON]<"2024-11-01"]
    test=[i for i in valid_chron if days[i]>="2024-11-01"]
    train_summary,_=portfolio(train,days,ranks,histories,fx) if train else ({},[])
    test_summary,_=portfolio(test,days,ranks,histories,fx) if test else ({},[])
    out={
      "status":"exploratory_not_investable_backtest",
      "universe":"ONLY stocks passing v5 QVM today, not historical point-in-time market/Trade Republic; severe survivor/coverage bias",
      "asof_controls":"SEC 10-K/10-K/A filed <= each signal date; annual periods aligned; historical price data truncated at signal date",
      "fixed_weights":{"quality":1/3,"value":1/3,"momentum12_2":1/3},
      "time_windows":{"from":PERIOD_FROM,"to":LAST_SIGNAL,"train_through":"2024-10-31","test_from":"2024-11-01"},
      "transaction_costs":"EUR 1 buy + EUR 1 sell; 0.1% slippage each side; dated USDEUR; price-only individual-stock P&L",
      "tickers_current_pilot":n_pilot,"tickers_with_historical_quotes_and_SEC":len(facts),
      "missing":failures,"fx_days":fx_count,
      "random_dates_requested":N_RANDOM,"random_dates_with_min_eight_historically_documented_firms":len(valid_random),
      "chronological_periods_requested":len(chronology),"periods_with_full_info":len(valid_chron),
      "coverage_by_signal_date":coverage,
      "all_valid_periods":chronic,"train":train_summary,"later_test":test_summary,
      "random_conditional_average_pct":({k:round(statistics.mean(x[k+"_return_pct"] for x in random_rows),4)
          for k in ("qvm","momentum12_2","legacy60d")} if random_rows else {}),
      "limitations":[
          "Current universe of 2026 surviving companies only — cannot establish alpha",
          "Non-uniform historical factor coverage and selection of evaluable dates biases estimates",
          "SEC-XBRL annual shares and GAAP tags are approximate valuation inputs",
          "No real historical Trade Republic orderability, sector control or bid/ask quotes",
          "No individual-stock dividends; matched benchmark has adjusted-close factor",
          "Overlap among randomized dates; random aggregates are NOT account returns",
          "No independent alternative historical security master",
          "Not sufficient to switch the app's default strategy"
      ],
      "created":datetime.now(timezone.utc).isoformat(),"seconds":round(time.time()-begun,2)
    }
    (OUT/"pit_qvm_report.json").write_text(json.dumps(out,ensure_ascii=False,indent=2))
    (OUT/"pit_qvm_chronological.json").write_text(json.dumps(curve,ensure_ascii=False,indent=2))
    (OUT/"pit_qvm_random_320_requested.json").write_text(json.dumps(random_rows,ensure_ascii=False,indent=2))
    print("QVM_PIT_RESULTS="+json.dumps({k:out[k] for k in (
        "tickers_with_historical_quotes_and_SEC","random_dates_requested",
        "random_dates_with_min_eight_historically_documented_firms",
        "chronological_periods_requested","periods_with_full_info",
        "all_valid_periods","train","later_test","random_conditional_average_pct","seconds")},
        separators=(",",":")),flush=True)

if __name__=="__main__":main()
