#!/usr/bin/env python3
"""Pre-specified threshold sensitivity test. Does NOT modify the production app.
Run 20 fixed entry/stop pairs on 2021-2024 training data and evaluate
the preselected training winner once on 2024-2026 untouched chronological OOS.
The 2026 surviving universe introduces survivorship bias; never call this
a point-in-time, all-market or Trade-Republic-specific validation.
"""
import csv
import json
import math
import random
import statistics
import time
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date, datetime, timezone
from pathlib import Path
import backtest_5y as b

# Locked before the data are fetched.
ENTRIES=(0.0,0.5,1.0,1.5,2.0)
STOPS=(1.0,1.5,2.5,4.0)
BASELINE=(1.0,2.5)
TRAIN_END="2024-11-01"  # training positions must EXIT strictly before this date
TEST_START="2024-11-01" # OOS signals first occur on/after this date
MIN_TRAIN_FILL_PCT=20.0
OUT=Path("research/limits_results")
OUT.mkdir(parents=True,exist_ok=True)

def round4(x):
    return round(x,4)

def periods(days):
    first=next(i for i,d in enumerate(days) if d>=b.START.isoformat())
    # Preset non-overlapping blocks from the same anchor as the initial test.
    all_idx=[i for i in range(first,len(days)-b.MAX_HORIZON,b.MAX_HORIZON)
             if date.fromisoformat(days[i])<=b.LAST_SIGNAL]
    train=[i for i in all_idx if days[i+b.MAX_HORIZON]<TRAIN_END]
    test=[i for i in all_idx if days[i]>=TEST_START]
    if not (len(train)>=30 and len(test)>=12):
        raise RuntimeError(f"Insufficient train/test blocks: {len(train)}, {len(test)}")
    return train,test

def run_blocks(ids,days,ranks,hists,fx):
    money=10000.
    match=10000.
    full_spy=10000.
    trial=[]
    trade_count=filled=selected=stops=0
    maxdrawdown=0.
    high=10000.
    for i in ids:
        c=b.cohort(i,days,ranks,hists,fx,money)
        matched=b.cohort(i,days,ranks,hists,fx,match)
        spy_pnl,_,_=b.benchmark_cohort(i,days,hists["SPY"],fx,full_spy)
        money+=c["strategy_pnl_eur"]
        match+=matched["matched_spy_pnl_eur"]
        full_spy+=spy_pnl
        high=max(high,money)
        maxdrawdown=min(maxdrawdown,money/high-1)
        trade_count+=len(c["trades"])
        filled+=c["filled"]
        selected+=c["selected"]
        stops+=sum(1 for t in c["trades"] if t["exit_reason"].startswith("stop"))
        trial.append({"signal_date":days[i],"strategy_equity":money,
                      "matched_spy_equity":match,"always_spy_equity":full_spy,
                      "strategy_return":c["strategy_return_pct"],
                      "matched_return":c["matched_spy_return_pct"],
                      "strategy_minus_matched":c["matched_excess_pct"],
                      "filled":c["filled"]})
    excess=[row["strategy_minus_matched"] for row in trial]
    return {"periods":len(ids),"trades":trade_count,
            "fill_pct":round4(100*filled/max(1,selected)),
            "stop_exits":stops,
            "strategy_end_eur":round4(money),
            "strategy_net_pnl_eur":round4(money-10000),
            "strategy_return_pct":round4((money/10000-1)*100),
            "matched_spy_end_eur":round4(match),
            "matched_spy_pnl_eur":round4(match-10000),
            "matched_spy_return_pct":round4((match/10000-1)*100),
            "excess_vs_matched_eur":round4(money-match),
            "spy_full_end_eur":round4(full_spy),
            "mean_block_excess_pct":round4(statistics.mean(excess)),
            "block_excess_95pct_bootstrap":b.block_bootstrap(excess,seed=b.SEED+11),
            "max_period_end_drawdown_pct":round4(maxdrawdown*100),
            "fee_total_eur":2*trade_count},trial

def run_random(ids,days,ranks,hists,fx):
    cohorts=[b.cohort(i,days,ranks,hists,fx,10000) for i in ids]
    if not cohorts:
        return {"n":0}
    trades=[t for x in cohorts for t in x["trades"]]
    return {
        "n":len(cohorts),"filled":len(trades),
        "fill_pct":round4(100*len(trades)/max(1,sum(x["selected"] for x in cohorts))),
        "mean_20d_strategy_pct":round4(statistics.mean(x["strategy_return_pct"] for x in cohorts)),
        "mean_20d_excess_vs_matched_spy_pct":round4(statistics.mean(x["matched_excess_pct"] for x in cohorts)),
        "mean_20d_excess_vs_full_spy_pct":round4(statistics.mean(x["excess_return_pct"] for x in cohorts)),
        "two_way_fees_eur":2*len(trades)
    }

def main():
    start=time.time()
    print("LOCKED_PARAMETERS entries",ENTRIES,"stops",STOPS,
          "train until",TRAIN_END,"test from",TEST_START,flush=True)
    universe=b.directory()
    collected={}
    failed={}
    with ThreadPoolExecutor(max_workers=b.WORKERS) as pool:
        futures={pool.submit(b.get_yahoo,t):t for t in universe+["SPY"]}
        for n,f in enumerate(as_completed(futures),1):
            ticker=futures[f]
            try:bars,src,err=f.result()
            except Exception as ex:bars,src,err=None,None,str(ex)
            if bars:collected[ticker]=(bars,src)
            else:failed[ticker]=err
            if n%45==0:print("Collected",n,"/",len(futures),"succeeded",len(collected),flush=True)
    if "SPY" not in collected or len(collected)<150:
        raise RuntimeError("Insufficient recent-survivor historical universe: "+str(len(collected)))
    hists=b.make_dataset(collected)
    days=[d for d in hists["SPY"]["dates"] if b.START.isoformat()<=d<=b.DATA_END.isoformat()]
    fx,n_fx=b.fx_history()
    print("Building all strictly past-only historical ranks...",flush=True)
    ranks=b.precompute_signal_ranks(hists,days)
    train_blocks,test_blocks=periods(days)
    valid_random=[i for i,d in enumerate(days[:-b.MAX_HORIZON]) if date.fromisoformat(d)<=b.LAST_SIGNAL]
    random_ids=sorted(random.Random(b.SEED).sample(valid_random,320))
    train_random=[i for i in random_ids if days[i+b.MAX_HORIZON]<TRAIN_END]
    test_random=[i for i in random_ids if days[i]>=TEST_START]
    print("TRAIN blocks",len(train_blocks),"TEST blocks",len(test_blocks),
          "random total",len(random_ids),"train",len(train_random),"test",len(test_random),flush=True)

    rows=[]
    chronological={}
    for entry in ENTRIES:
        for stop in STOPS:
            b.ENTRY_LIMIT_ATR=entry
            b.STOP_ATR=stop
            train,train_curve=run_blocks(train_blocks,days,ranks,hists,fx)
            test,test_curve=run_blocks(test_blocks,days,ranks,hists,fx)
            random_train=run_random(train_random,days,ranks,hists,fx)
            random_test=run_random(test_random,days,ranks,hists,fx)
            record={"buy_atr":entry,"stop_atr":stop,
                    "train":train,"test":test,"train_random":random_train,
                    "test_random":random_test}
            rows.append(record)
            chronological[f"{entry}/{stop}"]={"train":train_curve,"test":test_curve}
            print("LIMIT",entry,"STOP",stop,
                  "train net",train["strategy_net_pnl_eur"],"test net",test["strategy_net_pnl_eur"],
                  "test matched excess",test["excess_vs_matched_eur"],
                  "test fill",test["fill_pct"],flush=True)

    # Only TRAIN data selects winner. Selection criterion defined a priori:
    # train excess versus same-date, same-cash SPY; min 20% fills.
    qualified=[v for v in rows if v["train"]["fill_pct"]>=MIN_TRAIN_FILL_PCT]
    if not qualified:raise RuntimeError("No qualifying historical training configurations")
    selected=max(qualified,key=lambda r:(
        r["train"]["excess_vs_matched_eur"],
        r["train"]["strategy_net_pnl_eur"],
        -r["train"]["max_period_end_drawdown_pct"]))
    base=next(x for x in rows if (x["buy_atr"],x["stop_atr"])==BASELINE)
    # Critical: do not select the "best" OOS config; display as a warning only.
    retrospect=max(rows,key=lambda r:r["test"]["strategy_net_pnl_eur"])

    summary={
      "test": "Predefined 5x4 ATR boundary grid, train 2021–2024, OOS 2024–2026",
      "universe":"Current surviving 2026 US tickers only; severe survivorship and universe-selection bias",
      "model_same_as_current_app":"60d momentum/ATR ranks; buy limit below signal close, fixed ATR stop, 5-session entry window, 20-session holding; EUR FX as of trade dates",
      "transaction_costs":"EUR 1 buy + EUR 1 sell; 0.1% adverse price slippage each side",
      "train_cutoff_exit_strictly_before":TRAIN_END,
      "untouched_test_from":TEST_START,
      "train_blocks":len(train_blocks),"test_blocks":len(test_blocks),
      "random_seed":b.SEED,"random_dates":len(random_ids),
      "random_train":len(train_random),"random_test":len(test_random),
      "known_universe":len(universe),"usable_histories_excl_SPY":len(collected)-1,
      "missing_histories":failed,"n_historical_usdeur_days":n_fx,
      "locked_grid":{"buy_limit_ATR":ENTRIES,"stop_distance_ATR":STOPS,
                     "selection_metric":"train EUR strategy terminal minus matched-SPY terminal, min 20% fill"},
      "original":{"buy_atr":base["buy_atr"],"stop_atr":base["stop_atr"],"train":base["train"],"test":base["test"],
                  "test_random":base["test_random"]},
      "chosen_without_test_peeking":{"buy_atr":selected["buy_atr"],"stop_atr":selected["stop_atr"],
                                     "train":selected["train"],"test":selected["test"],
                                     "test_random":selected["test_random"]},
      "test_best_only_in_hindsight_not_actionable":{
          "buy_atr":retrospect["buy_atr"],"stop_atr":retrospect["stop_atr"],
          "test":retrospect["test"]},
      "limitations":[
       "2026 surviving US listings are not historical listings, so results are NOT unbiased",
       "historical Trade Republic Austria tradability is unknown, filter cannot be backtested",
       "Yahoo chart historical source not a tick-level executable bid-ask feed; stops approximated by OHLC",
       "individual stock dividends omitted, matched SPY dividends approximated",
       "random dates overlap; bootstrap interval on short chronological blocks is only approximate",
       "parameter selection within training uses multiple comparisons; holdout is one historical regime",
       "cash does not earn interest; Austrian taxes and FX bid-ask not included"],
      "created_utc":datetime.now(timezone.utc).isoformat(),
      "duration_seconds":round(time.time()-start,2)
    }
    (OUT/"threshold_summary.json").write_text(json.dumps(summary,indent=2,ensure_ascii=False))
    (OUT/"all_20_variants.json").write_text(json.dumps(rows,indent=2,ensure_ascii=False))
    keys=["buy_atr","stop_atr","train_end_eur","train_excess_eur",
          "test_end_eur","test_return_pct","test_spy_matched_eur","test_excess_eur",
          "test_fills","test_fill_pct","test_maxdrawdown_pct",
          "train_random_mean_pct","test_random_mean_pct"]
    with (OUT/"grid_summary.csv").open("w",newline="",encoding="utf-8") as f:
        wr=csv.DictWriter(f,fieldnames=keys);wr.writeheader()
        for x in rows:
            tr=x["train"];te=x["test"]
            wr.writerow({"buy_atr":x["buy_atr"],"stop_atr":x["stop_atr"],
                         "train_end_eur":tr["strategy_end_eur"],"train_excess_eur":tr["excess_vs_matched_eur"],
                         "test_end_eur":te["strategy_end_eur"],"test_return_pct":te["strategy_return_pct"],
                         "test_spy_matched_eur":te["matched_spy_end_eur"],
                         "test_excess_eur":te["excess_vs_matched_eur"],
                         "test_fills":te["trades"],"test_fill_pct":te["fill_pct"],
                         "test_maxdrawdown_pct":te["max_period_end_drawdown_pct"],
                         "train_random_mean_pct":x["train_random"]["mean_20d_strategy_pct"],
                         "test_random_mean_pct":x["test_random"]["mean_20d_strategy_pct"]})
    (OUT/"chronological_curves.json").write_text(json.dumps(chronological,separators=(",",":")))
    print("SENSITIVITY_FINAL="+json.dumps({"original":summary["original"],"train_chosen":summary["chosen_without_test_peeking"],
           "hindsight_best":summary["test_best_only_in_hindsight_not_actionable"],
           "n_histories":summary["usable_histories_excl_SPY"],
           "n_train_blocks":len(train_blocks),"n_test_blocks":len(test_blocks),
           "n_train_random":len(train_random),"n_test_random":len(test_random),
           "seconds":summary["duration_seconds"]},separators=(",",":")),flush=True)

if __name__=="__main__":main()
