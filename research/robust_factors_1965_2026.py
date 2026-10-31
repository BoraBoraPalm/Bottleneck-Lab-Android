#!/usr/bin/env python3
"""Long-horizon, reproducible academic factor-portfolio stress test (NOT live TR trading).

Uses monthly, historically reconstituted CRSP/Fama-French US factor portfolios,
not today-surviving ticker lists. Defines candidate strategies *before download*,
tests all (does not optimize weights), includes EUR FX conversion where available,
Newey-West HAC and 12-month circular block bootstrap of excess returns.
The portfolio data are retroactively revised and cannot represent a genuinely
unseen forward holdout or direct executable security at Trade Republic.
"""
import bisect,csv,io,json,math,random,re,statistics,time,urllib.request,zipfile
from collections import OrderedDict
from datetime import datetime,timezone
from pathlib import Path

ROOT="https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/ftp/"
DATASETS=OrderedDict([
 ("FF5","F-F_Research_Data_5_Factors_2x3_CSV.zip"),
 ("VALUE","6_Portfolios_2x3_CSV.zip"),
 ("QUALITY","6_Portfolios_ME_OP_2x3_CSV.zip"),
 ("INVEST","6_Portfolios_ME_INV_2x3_CSV.zip"),
 ("MOMENTUM","10_Portfolios_Prior_12_2_CSV.zip")
])
FX_URL="https://api.frankfurter.dev/v2/rates?from=1999-01-01&to=2026-10-31&base=USD&quotes=EUR"
SEED=20261031
OUT=Path("research/factor_robustness")
OUT.mkdir(parents=True,exist_ok=True)
# The only candidate set used: fixed a priori before seeing market data.
POLS=OrderedDict([
 ("Market",{"MKT":1.}),
 ("Large Value",{"VAL":1.}),
 ("Large Quality",{"QUAL":1.}),
 ("Large Conservative Investment",{"INV":1.}),
 ("Momentum Winners",{"MOM":1.}),
 ("Equal Q+V+M",{"QUAL":1/3,"VAL":1/3,"MOM":1/3}),
 ("50% Market + QVM",{"MKT":.5,"QUAL":1/6,"VAL":1/6,"MOM":1/6}),
 ("50% Market + Quality/Value",{"MKT":.5,"QUAL":.25,"VAL":.25}),
 ("50% Market + Quality/Momentum",{"MKT":.5,"QUAL":.25,"MOM":.25}),
 ("50% Market + Quality/Value/Conservative",{"MKT":.5,"QUAL":1/6,"VAL":1/6,"INV":1/6}),
 ("80% Market + Momentum",{"MKT":.8,"MOM":.2}),
 ("80% Market + Quality",{"MKT":.8,"QUAL":.2})
])
# Locked cost sensitivities; these are annual hypothetical factor-implementation
# headwinds, NOT executable €1 per individual stock trading.
HEADWINDS=(0.0,0.01,0.02)
START_EUR=2000
RANDOM_BLOCK_MONTHS=12
BOOT=2000

def download(url,max_bytes=5500000,timeout=30):
    req=urllib.request.Request(url,headers={"User-Agent":"Mozilla/5.0 (research; academic reproducibility)","Accept":"*/*"})
    with urllib.request.urlopen(req,timeout=timeout) as resp:
        if resp.status!=200:raise ValueError("HTTP "+str(resp.status))
        blob=resp.read(max_bytes+1)
    if len(blob)>max_bytes:raise ValueError("Oversized response "+url)
    return blob

def parse_french_zip(blob,label):
    z=zipfile.ZipFile(io.BytesIO(blob))
    names=[x for x in z.namelist() if x.lower().endswith((".csv",".txt"))]
    if len(names)!=1:raise ValueError(label+" unexpected zip entries "+str(z.namelist()))
    lines=z.read(names[0]).decode("latin-1").splitlines()
    # first data block is VW monthly returns, before annual/equal-weight sections.
    start=next((i for i,s in enumerate(lines) if re.match(r"^\s*\d{6}\s*,",s)),None)
    if start is None:raise ValueError("Monthly data block missing "+label)
    header_index=next((j for j in range(start-1,max(-1,start-12),-1)
            if lines[j].count(",")>=3),None)
    if header_index is None:raise ValueError("Header missing "+label)
    headers=[x.strip() for x in next(csv.reader([lines[header_index]]))]
    if headers and headers[0].strip() and re.match(r"^\d{6}$",headers[0]):
        raise ValueError("Header accidentally data")
    history={}
    for s in lines[start:]:
        if not re.match(r"^\s*\d{6}\s*,",s):break
        parts=[x.strip() for x in next(csv.reader([s]))]
        if len(parts)!=len(headers):raise ValueError(label+" inconsistent field count")
        ym=parts[0]
        values={}
        for k,v in zip(headers[1:],parts[1:]):
            try:x=float(v)
            except ValueError:continue
            if not math.isfinite(x) or x<=-99 or x>=2000:continue
            values[k]=x/100
        history[ym]=values
    if len(history)<450:raise ValueError(label+" too few months: "+str(len(history)))
    return history,headers

def choose_header(headers,key):
    opts={h.upper().replace(" ","").replace("-",""):h for h in headers[1:]}
    targets={
      "MKT":["MKTRF"],
      "RF":["RF"],
      "VAL":["BIGHIBM","BIGBM3"],
      "QUAL":["BIGHIOP","BIGOP3"],
      "INV":["BIGLOINV","BIGINV1"],
      "MOM":["HIPRIOR","HI12_2","PRIOR10","HIPRIOR12_2"]
    }
    for t in targets[key]:
        if t in opts:return opts[t]
    if key=="MOM":
        for h in headers[1:]:
            hnorm=h.upper().replace(" ","")
            if "HI" in hnorm and ("PRIOR" in hnorm or "MOM" in hnorm):return h
    raise ValueError(f"Missing {key} among actual headers {headers}")

def load_academic():
    data={}
    details={}
    for label,file in DATASETS.items():
        blob=download(ROOT+file)
        parsed,header=parse_french_zip(blob,label)
        data[label]=parsed
        details[label]={"url":ROOT+file,"rows":len(parsed),"columns":header}
        print("DATASET",label,"months",len(parsed),"headers",header[:12],flush=True)
    common=sorted(set.intersection(*(set(x) for x in data.values())))
    keys={
        "MKT":choose_header(details["FF5"]["columns"],"MKT"),
        "RF":choose_header(details["FF5"]["columns"],"RF"),
        "VAL":choose_header(details["VALUE"]["columns"],"VAL"),
        "QUAL":choose_header(details["QUALITY"]["columns"],"QUAL"),
        "INV":choose_header(details["INVEST"]["columns"],"INV"),
        "MOM":choose_header(details["MOMENTUM"]["columns"],"MOM")
    }
    calendar={}
    for month in common:
        try:
            row={"MKT":data["FF5"][month][keys["MKT"]]+data["FF5"][month][keys["RF"]],
                 "VAL":data["VALUE"][month][keys["VAL"]],
                 "QUAL":data["QUALITY"][month][keys["QUAL"]],
                 "INV":data["INVEST"][month][keys["INV"]],
                 "MOM":data["MOMENTUM"][month][keys["MOM"]]}
        except KeyError:continue
        if not all(math.isfinite(x) and x>-.99 for x in row.values()):continue
        calendar[month]=row
    if len(calendar)<450:raise ValueError("Insufficient intersected months "+str(len(calendar)))
    return calendar,details,keys

def fx_monthly():
    try:
        blob=download(FX_URL,max_bytes=2000000,timeout=30)
        parsed=json.loads(blob)
        if not isinstance(parsed,list):raise ValueError("FX not a list")
        data={r["date"]:float(r["rate"]) for r in parsed if r.get("base")=="USD"
              and r.get("quote")=="EUR" and float(r.get("rate",0))>0}
        if len(data)<5000:raise ValueError("FX data sparse "+str(len(data)))
        keys=sorted(data)
        results={}
        for y in range(2000,2027):
            for m in range(1,13):
                if y==2026 and m>10:break
                date=f"{y:04d}-{m:02d}-{31 if m in (1,3,5,7,8,10,12) else 30 if m in (4,6,9,11) else 29}"
                p=bisect.bisect_right(keys,date)-1
                if p>=0:results[f"{y:04d}{m:02d}"]=data[keys[p]]
        print("EUR FX",len(data),"daily points",len(results),"monthly",flush=True)
        return results,None
    except Exception as e:
        return {},str(e)

def get_rows(cal,fx,eur=False):
    months=sorted(cal)
    if eur:
        months=[d for d in months if int(d[:4])>=START_EUR and d in fx]
    rows=[]
    previous_fx=None
    for m in months:
        x=cal[m].copy()
        if eur:
            rate=fx[m]
            if previous_fx is None:previous_fx=rate;continue
            xr=rate/previous_fx;previous_fx=rate
            x={k:(1+v)*xr-1 for k,v in x.items()}
            # Euro-denominated cash has no USD currency exposure.
            x["CASH"]=0.0
        else:
            x["CASH"]=0.0
        rows.append((m,x))
    return rows

def raw_return(policy,r):
    return sum(w*r[k] for k,w in policy.items())

def stats_for(vals):
    if not vals:return {}
    n=len(vals)
    wealth=1.;peak=1.;dd=0.
    for v in vals:
        wealth*=1+v
        peak=max(peak,wealth)
        dd=min(dd,wealth/peak-1)
    ann=wealth**(12/n)-1 if wealth>0 else -1.
    vol=statistics.stdev(vals)*math.sqrt(12) if n>1 else 0
    return {"months":n,"cum_pct":round((wealth-1)*100,3),
            "CAGR_pct":round(ann*100,3),"vol_pct":round(vol*100,3),
            "max_month_end_drawdown_pct":round(dd*100,3)}

def newey_west_monthly(diff,lags=12):
    """HAC variance of sample mean; uses truncation at lags and Bartlett kernel."""
    n=len(diff)
    if n<36:raise ValueError("Insufficient months for HAC")
    mu=statistics.mean(diff)
    x=[v-mu for v in diff]
    cov0=sum(v*v for v in x)/n
    variance=cov0
    for lag in range(1,min(lags,n-1)+1):
        cov=sum(x[t]*x[t-lag] for t in range(lag,n))/n
        variance+=2*(1-lag/(lags+1))*cov
    sem=math.sqrt(max(variance,0)/n)
    z=mu/sem if sem>1e-12 else 0
    p=math.erfc(abs(z)/math.sqrt(2))
    return {"annual_excess_pct":round(mu*1200,3),
            "HAC_z":round(z,3),"HAC_two_sided_p":round(p,6),"monthly_se_pct":round(sem*100,4)}

def block_bootstrap(diff,seed=SEED,block=12,count=BOOT):
    rng=random.Random(seed)
    n=len(diff)
    means=[]
    for _ in range(count):
        items=[]
        while len(items)<n:
            start=rng.randrange(n)
            items.extend(diff[(start+j)%n] for j in range(block))
        means.append(sum(items[:n])/n*1200)
    means.sort()
    return [round(means[int(.025*(count-1))],3),round(means[int(.975*(count-1))],3)]

def rolls(diff,n=60):
    if len(diff)<n:return {}
    beats=[]
    for i in range(n-1,len(diff)):
        # Compare 5-year compounded holdings, not a sum of returns.
        strat=bench=1.
        for j in range(i-n+1,i+1):
            # diff are arithmetic excess returns, 5y log compounded difference
            pass
        beats.append(sum(diff[i-n+1:i+1])>0)
    return {"n_overlapping_5y_windows":len(beats),
            "fraction_positive_arithmetic_5y_excess_pct":round(100*sum(beats)/len(beats),2)}

def test_set(rows,label,annual_cost=0):
    # Fixed monthly-weight academic portfolio proxies. Annual "cost" is *extra*
    # implementation haircut only for factor-exposure components; benchmark has
    # no assumed transaction costs. Lower bound, not individual-stock TR execution.
    results={}
    market=[r["MKT"] for _,r in rows]
    for name,weights in POLS.items():
        vals=[]
        for _,r in rows:
            gross=raw_return(weights,r)
            factor_weight=sum(w for k,w in weights.items() if k!="MKT")
            haircut=annual_cost*factor_weight/12
            vals.append((1+gross)*(1-haircut)-1)
        diff=[x-y for x,y in zip(vals,market)]
        s=stats_for(vals)
        nw=newey_west_monthly(diff)
        ci=block_bootstrap(diff,seed=SEED+len(name),block=RANDOM_BLOCK_MONTHS,count=BOOT)
        # Widened discipline: guard against selecting over 11 positive-looking tests.
        p_correct=min(1,nw["HAC_two_sided_p"]*(len(POLS)-1)) if name!="Market" else 1.
        windows={}
        for months in (36,60,120):
            comp=[]
            for end in range(months,len(vals)+1):
                a=bb=1
                for k in range(end-months,end):
                    a*=1+vals[k];bb*=1+market[k]
                comp.append(a>bb)
            windows[str(months)+"m"]={"windows":len(comp),
                "fraction_outperform_pct":round(100*sum(comp)/len(comp),2)} if comp else {}
        results[name]={**s,**nw,"annual_excess_bootstrap_95pct":ci,
            "bonferroni_corrected_p":round(p_correct,6),
            "rolling_outperformance":windows}
    return {"window":label,"months":len(rows),
            "first_month":rows[0][0],"last_month":rows[-1][0],
            "annual_factor_cost_haircut":annual_cost,
            "benchmark":stats_for(market),"strategies":results}

def main():
    started=time.time()
    cal,sources,keys=load_academic()
    fx,fx_error=fx_monthly()
    usd=get_rows(cal,fx,eur=False)
    # First period 1963/07; split is reporting only, NOT genuinely untouched because
    # all these factors were discovered with historical results already published.
    subperiods={
        "USD full after 1965":[x for x in usd if x[0]>="196501"],
        "USD 1965–1999":[x for x in usd if "196501"<=x[0]<="199912"],
        "USD 2000–2014":[x for x in usd if "200001"<=x[0]<="201412"],
        "USD 2015–2026":[x for x in usd if "201501"<=x[0]<="202609"],
    }
    if fx and len(fx)>250:
        eur=get_rows(cal,fx,eur=True)
        subperiods["EUR 2000–2026"]=[x for x in eur if x[0]<="202609"]
        subperiods["EUR 2015–2026"]=[x for x in eur if x[0]>="201501" and x[0]<="202609"]
    results={}
    for title,rows in subperiods.items():
        if len(rows)<60:continue
        for haircut in HEADWINDS:
            key=title+" | extra cost "+str(haircut*100)+"pct/yr"
            results[key]=test_set(rows,title,haircut)
            chosen=results[key]["strategies"]
            print("FACTOR_WINDOW",title,"cost",haircut,
                  "months",len(rows),"QVM_CAGR",chosen["Equal Q+V+M"]["CAGR_pct"],
                  "market",results[key]["benchmark"]["CAGR_pct"],flush=True)
    select=[(k,v) for k,v in results.items() if "EUR 2000–2026" in k and "cost 1.0" in k]
    chosen=select[0][1]["strategies"] if select else {}
    full=results.get("USD full after 1965 | extra cost 1.0pct/yr")
    # Do NOT automatically select a "winner"; publish all candidates.
    output={
        "goal":"Try fixed, academically motivated factor exposure candidates; no search-until-winner",
        "source":"Kenneth French Data Library: monthly historically reconstituted CRSP portfolios, as revised today",
        "sources":sources,"matched_portfolio_columns":keys,"fx_url":FX_URL,"fx_error":fx_error,
        "candidate_count_including_benchmark":len(POLS),
        "fixed_candidates":POLS,"headwinds_extra_annual":HEADWINDS,
        "first_year":min(cal),"last_year":max(cal),
        "selection_statement":"No statistical significance guarantee; Bonferroni applied across 11 pre-defined candidate strategies; rolling windows overlap, not independent",
        "significance":"Newey-West HAC 12 monthly lags normal approx two-sided; moving circular 12-month block bootstrap; Bonferroni across 11 tested candidates",
        "limitations":[
            "Academic factor portfolio indices are NOT directly tradeable assets or TR stock fills",
            "The reported factors use revised historical CRSP data and are already known in scientific literature",
            "Individual stock trading fees/spreads and portfolio turnover are not captured; 1-2pct extra annual costs only are illustrative",
            "EUR converted equity indices assume fully unhedged USD exposure; no Austrian taxation",
            "Some factor portfolios contain small stocks and incur capacity and rebalancing costs",
            "EUR FX file converted at monthly official reference not broker FX bid/ask",
            "The 2015-2026 period was NOT truly intellectually hidden; past published studies saw it",
            "Past outperformance fraction does not imply probability of future superiority",
            "Index-level benchmark Mkt-RF + RF is US stock market, not Gerd Kommer world ETF"
        ],
        "results":results,"elapsed_sec":round(time.time()-started,1)
    }
    (OUT/"full_factor_study.json").write_text(json.dumps(output,indent=2,ensure_ascii=False))
    labels=["window","cost_per_year_extra","strategy","months","strategy_CAGR_pct","benchmark_CAGR_pct",
            "annual_excess_mean_pct","HAC_z","HAC_p","bonferroni_p","bootstrap_low_pct","bootstrap_high_pct",
            "roll5y_win_pct","max_drawdown_pct"]
    with (OUT/"factor_study_summary.csv").open("w",encoding="utf-8",newline="") as f:
        w=csv.DictWriter(f,fieldnames=labels);w.writeheader()
        for title,v in results.items():
            for name,s in v["strategies"].items():
                ci=s["annual_excess_bootstrap_95pct"]
                w.writerow({"window":v["window"],"cost_per_year_extra":v["annual_factor_cost_haircut"],
                    "strategy":name,"months":v["months"],"strategy_CAGR_pct":s["CAGR_pct"],
                    "benchmark_CAGR_pct":v["benchmark"]["CAGR_pct"],
                    "annual_excess_mean_pct":s["annual_excess_pct"],"HAC_z":s["HAC_z"],
                    "HAC_p":s["HAC_two_sided_p"],"bonferroni_p":s["bonferroni_corrected_p"],
                    "bootstrap_low_pct":ci[0],"bootstrap_high_pct":ci[1],
                    "roll5y_win_pct":s["rolling_outperformance"].get("60m",{}).get("fraction_outperform_pct"),
                    "max_drawdown_pct":s["max_month_end_drawdown_pct"]})
    brief={"USD_full":full["strategies"] if full else {},
           "EUR_after_2000_1pct":chosen,
           "data":{"total_months":len(cal),"fx_valid":bool(fx),
                   "series_columns":keys,"begin":min(cal),"end":max(cal)}}
    print("FACTOR_STUDY_FINAL="+json.dumps(brief,separators=(",",":")),flush=True)
if __name__=="__main__":main()
