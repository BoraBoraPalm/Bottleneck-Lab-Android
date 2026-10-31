#!/usr/bin/env python3
"""Compare 12-2 month price momentum with deployed 60d score, SAME 225 surviving
US stock universe, same selected trading dates, fills, €1+€1 costs and FX.
NOT survivorship-bias-free. Does not alter production app.
"""
import json
import math
import random
import statistics
import time
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date,datetime,timezone
from pathlib import Path
import backtest_5y as b
from evaluate_qvm_pit import historical_price
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
from multifactor import momentum_12_2

OUT=Path("research/momentum_results")
OUT.mkdir(parents=True,exist_ok=True)
MODELS=("legacy_60d","momentum_12_2")
SEED=b.SEED
RANDOM_COUNT=320

def rank_day(day,histories):
    old=[];long=[]
    for t,h in histories.items():
        if t=="SPY":continue
        signal=b.signals_on(t,h["bars"],h["index"],day)
        if signal is None:continue
        old.append(signal)
        idx=h["index"][day]
        raw=momentum_12_2([v[3] for v in h["bars"][:idx+1]])
        if raw is not None:
            # Same liquidity and bid/ask model; ONLY signal ranking changes.
            long.append((raw,t,signal[2],signal[3],signal[4],signal[5]))
    old.sort(key=lambda x:(-x[0],x[1]))
    long.sort(key=lambda x:(-x[0],x[1]))
    return {"legacy_60d":old[:10],"momentum_12_2":long[:10],"long_eligible":len(long),"legacy_eligible":len(old)}

def periods(indices,dates,history,fx):
    caps={k:10000. for k in MODELS}
    matched={k:10000. for k in MODELS}
    ntrades={k:0 for k in MODELS}
    detail=[]
    for i in indices:
        signal=history[dates[i]]
        row={"date":dates[i],"long_eligible":signal["long_eligible"]}
        for k in MODELS:
            group=signal[k]
            trades=[]
            for x in group:
                tr=b.trade(x,i,dates,histories[x[1]],fx,caps[k]/10)
                if tr:trades.append(tr)
            pnl=sum(x["pnl_eur"] for x in trades)
            benchmark=sum(b.exposure_matched_spy_trade(tr,histories["SPY"],fx) for tr in trades)
            caps[k]+=pnl;matched[k]+=benchmark
            ntrades[k]+=len(trades)
            row[k+"_end"]=round(caps[k],2)
            row[k+"_trade_count"]=len(trades)
        detail.append(row)
    res={k:{"end_eur":round(caps[k],2),"net_eur":round(caps[k]-10000,2),
             "return_pct":round((caps[k]/10000-1)*100,3),
             "matched_spy_end_eur":round(matched[k],2),
             "excess_eur":round(caps[k]-matched[k],2),
             "executed_trades":ntrades[k],
             "total_eur_fees":ntrades[k]*2} for k in MODELS}
    return res,detail

def random_checks(ids,days,ranks,histories,fx):
    stats={k:{"pnl_pct":[],"filled":0,"expected":0} for k in MODELS}
    for i in ids:
        for k in MODELS:
            rank=ranks[days[i]][k]
            trades=[b.trade(x,i,days,histories[x[1]],fx,1000) for x in rank]
            trades=[tr for tr in trades if tr]
            stats[k]["pnl_pct"].append(100*sum(t["pnl_eur"] for t in trades)/10000)
            stats[k]["filled"]+=len(trades)
            stats[k]["expected"]+=len(rank)
    return {k:{"random_days":len(ids),
               "mean_20d_pct":round(statistics.mean(v["pnl_pct"]),4),
               "median_20d_pct":round(statistics.median(v["pnl_pct"]),4),
               "fill_pct":round(100*v["filled"]/max(1,v["expected"]),3),
               "executed_trade_observations":v["filled"]}
            for k,v in stats.items()}

def main():
    global histories
    start=time.monotonic()
    universe=b.directory()
    data={}
    failed={}
    with ThreadPoolExecutor(max_workers=8) as pool:
        jobs={pool.submit(historical_price,t):t for t in universe+["SPY"]}
        for fut in as_completed(jobs):
            t=jobs[fut]
            try:prices,error=fut.result()
            except Exception as e:prices,error=None,str(e)
            if prices:data[t]=(prices,"Yahoo")
            else:failed[t]=error
    if len(data)<130 or "SPY" not in data:raise RuntimeError("Insufficient historical prices")
    histories=b.make_dataset(data)
    days=[d for d in histories["SPY"]["dates"] if b.START.isoformat()<=d<=b.DATA_END.isoformat()]
    end=min(len(days)-b.MAX_HORIZON,len(days))
    elig=[i for i in range(end) if days[i]<=b.LAST_SIGNAL.isoformat()]
    selected=sorted(random.Random(SEED).sample(elig,RANDOM_COUNT))
    chron=[i for i in range(0,end,b.MAX_HORIZON) if days[i]<=b.LAST_SIGNAL.isoformat()]
    all_idx=sorted(set(selected+chron))
    ranks={days[i]:rank_day(days[i],histories) for i in all_idx}
    fx,nfx=b.fx_history()
    full,curve=periods(chron,days,ranks,fx)
    train=[i for i in chron if days[i+b.MAX_HORIZON]<"2024-11-01"]
    test=[i for i in chron if days[i]>="2024-11-01"]
    tr,_=periods(train,days,ranks,fx)
    te,_=periods(test,days,ranks,fx)
    random_out=random_checks(selected,days,ranks,histories,fx)
    out={"universe":"2026 surviving US listings, not unbiased historical market",
         "factors_compared":["Current capped 60d moment/ATR score","Standard 12-2 month return rank"],
         "equal_conditions":"10 positions, identical liquidity requirement, EUR FX at each trade, 1EUR buy/1EUR sell, 0.1pct each side adverse slippage, 5-day limit entry and 20-day exit",
         "random_dates":RANDOM_COUNT,
         "price_histories":len(data)-1,"price_missing":failed,"fx_days":nfx,
         "chronological":full,"train_2021_to_2024":tr,"test_2024_to_2026":te,
         "random_samples":random_out,
         "caveats":["Survivorship bias", "No actual historical TR orderability", "No stock dividends", "Fixed EUR brokerage costs but unknown real bid/ask","Daily OHLC approximation to stops"],
         "seconds":round(time.monotonic()-start,1)}
    (OUT/"momentum_model_comparison.json").write_text(json.dumps(out,indent=2,ensure_ascii=False))
    (OUT/"chronological_curve.json").write_text(json.dumps(curve,indent=2))
    print("MOMENTUM_COMPARE="+json.dumps(out,separators=(",",":")),flush=True)
if __name__=="__main__":main()
