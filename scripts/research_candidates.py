"""Current, explicitly experimental stock candidates for the independent research tab.

No forward-return promises; no artificial missing fundamentals. Candidate lists
do not modify the legacy trading ranks. News is thematic context only, not proof
that a specific company profits from a supply shortage.

Quality+Momentum is ranked independently of Value using reported US GAAP profits
/ assets and 12-2 month returns, with minimum data and freshness requirements.
"""
import math
from datetime import datetime, date, timezone
from multifactor import _rank_scores,number

THEMES={
    "Stromnetze":"Netzengpässe/Transformatoren",
    "Rechenzentren":"Rechenleistung, Stromversorgung und Kühlung",
    "Halbleiter":"Speicher/Advanced Packaging",
    "Energie":"Stromerzeugung und Infrastruktur",
    "Rohstoffe":"Metallangebot und Raffination",
    "Wasser":"Wasseraufbereitung und Infrastruktur",
    "Verteidigung":"Fertigung und Kapazität",
    "Automation & Logistik":"Produktions- und Lieferkettenkapazität",
}
THEME_GROUP=set(THEMES)
MAX_ITEMS=10
MIN_QM_COMPANIES=8

def day(value):
    try:return date.fromisoformat(str(value)[:10])
    except (ValueError,TypeError):return None

def suitable(r,today):
    if r.get("eligible_for_ranking") is not True:return False
    if r.get("currency")!="USD":return False
    if not number(r.get("eur_per_unit")) or number(r.get("eur_per_unit"))<=0:return False
    price=number(r.get("close"));atr=number(r.get("atr"))
    if price is None or atr is None or price<=0 or atr<=0:return False
    priced=day(r.get("price_date"));checked=day(r.get("last_checked_at"))
    if priced is None or checked is None:return False
    # No silent week-old data in *current* candidate claims.
    if (today-priced).days>7 or (today-checked).days>7:return False
    return True

def quality_inputs(row,today):
    f=row.get("fundamentals")
    if not isinstance(f,dict):return None
    fiscal=day(f.get("fiscal_year_end"));filing=day(f.get("filed"))
    if fiscal is None or filing is None:return None
    if filing>today or fiscal>today or (today-fiscal).days>610:return None
    assets=number(f.get("assets_usd"))
    if assets is None or assets<=0:return None
    parts={}
    for key,field in (("gross_profit_assets","gross_profit_usd"),
                      ("cashflow_assets","op_cashflow_usd"),
                      ("earnings_assets","net_income_usd")):
        x=number(f.get(field))
        if x is not None:parts[key]=x/assets
    debt=number(f.get("debt_usd"))
    if debt is not None:parts["low_debt_assets"]=-debt/assets
    if len(parts)<2:return None
    return parts

def qm_rank(stocks,today):
    candidates={}
    for r in stocks:
        if not suitable(r,today):continue
        momentum=number(r.get("momentum_12_2"))
        if momentum is None:continue
        quality=quality_inputs(r,today)
        if quality is None:continue
        candidates[r["ticker"]]={"momentum":momentum,"quality":quality}
    if len(candidates)<MIN_QM_COMPANIES:return {},len(candidates)
    mom_rank=_rank_scores([(t,x["momentum"]) for t,x in candidates.items()])
    qmetrics=("gross_profit_assets","cashflow_assets","earnings_assets","low_debt_assets")
    qranks={key:_rank_scores([(t,x["quality"][key]) for t,x in candidates.items() if key in x["quality"]])
            for key in qmetrics}
    out={}
    for ticker,c in candidates.items():
        qvals=[qranks[k][ticker] for k in qmetrics if ticker in qranks[k]]
        if len(qvals)<2:continue
        q=sum(qvals)/len(qvals)
        m=mom_rank[ticker]
        out[ticker]={
            "score":round(100*(q+m)/2,2),
            "quality_score":round(100*q,2),
            "momentum_score":round(100*m,2),
            "quality_components":len(qvals),
            "cohort_size":len(candidates)
        }
    return out,len(candidates)

def row_entry(row,score,parts=None,thematic=None,news=None):
    f=row.get("fundamentals") or {}
    doc= f.get("source_url") if isinstance(f,dict) else None
    if not isinstance(doc,str) or not doc.startswith("https://data.sec.gov/"):doc=None
    price=number(row.get("close"));atr=number(row.get("atr"));fx=number(row.get("eur_per_unit"))
    data={
        "ticker":row["ticker"],
        "name":str(row.get("name") or row["ticker"])[:120],
        "theme":str(row.get("theme") or "Nicht klassifiziert"),
        "currency":row.get("currency"),
        "price_date":row.get("price_date"),
        "last_checked_at":row.get("last_checked_at"),
        "original_close":price,
        "close_eur":round(price*fx,4),
        "fx_date":row.get("fx_date"),
        "price_source":row.get("source"),
        "atr_eur":round(atr*fx,4),
        # Explicitly illustrative existing model parameters; NOT research-validated.
        "illustrative_buy_eur":round((price-atr)*fx,4),
        "illustrative_stop_eur":round((price-atr-2.5*atr)*fx,4),
        "tr_at_listed":row.get("tr_at_listed") is True,
        "tr_verification":row.get("tr_verification","unverified"),
        "tr_isin":row.get("tr_isin") if row.get("tr_at_listed") is True else None,
        "score":round(score,2),
        "momentum_12_2_pct":round(100*number(row.get("momentum_12_2")),2) if number(row.get("momentum_12_2")) is not None else None,
        "sec_filing_date":f.get("filed") if isinstance(f,dict) else None,
        "sec_fiscal_year_end":f.get("fiscal_year_end") if isinstance(f,dict) else None,
        "sec_source_url":doc,
        "missing_quality_facts":doc is None,
        "category_confidence":"thematic_hypothesis_only" if thematic else None,
        "research_validated":False
    }
    if parts:data["factors"]=parts
    if thematic:
        data["thematic_hypothesis"]=THEMES.get(row.get("theme"),str(row.get("theme") or ""))
        data["theme_evidence_level"]="sector_news_only" if news else "curated_theme_only"
        data["theme_news"]=(news or [])[:2]
    return data

def current_candidates(stocks,news,generated_at,required_min=MIN_QM_COMPANIES):
    today=day(generated_at) or datetime.now(timezone.utc).date()
    valid=[r for r in stocks if suitable(r,today)]
    qm,cohort=qm_rank(valid,today)
    qvm={
        r["ticker"]:r["multifactor"] for r in valid
        if isinstance(r.get("multifactor"),dict) and quality_inputs(r,today) is not None and
           all(number(r["multifactor"].get(k)) is not None for k in
               ("score","momentum_score","quality_score","value_score"))
           and day(r["multifactor"].get("filing_date")) is not None
           and day(r["multifactor"].get("filing_date"))<=today
           and r["multifactor"].get("filing_date")==r["fundamentals"].get("filed")
    }
    by_ticker={r["ticker"]:r for r in valid}
    qm_order=sorted(qm,key=lambda t:(-qm[t]["score"],t))
    qvm_order=sorted(qvm,key=lambda t:(-qvm[t]["score"],t))
    qm_top=qm_order[:MAX_ITEMS] if cohort>=required_min else []
    qvm_top=qvm_order[:MAX_ITEMS] if len(qvm)>=required_min else []
    qm_list=[row_entry(by_ticker[t],qm[t]["score"],
            {"quality":qm[t]["quality_score"],"momentum":qm[t]["momentum_score"],
             "quality_components":qm[t]["quality_components"],"cohort":qm[t]["cohort_size"]})
             for t in qm_top]
    qvm_list=[row_entry(by_ticker[t],qvm[t]["score"],
              {"quality":qvm[t]["quality_score"],"momentum":qvm[t]["momentum_score"],
               "value":qvm[t]["value_score"],"cohort":qvm[t].get("cohort_size")})
              for t in qvm_top]

    # Sector hypotheses are allowed to enter a watchlist, but never gain
    # an invented company-specific shortage score. They are simply the
    # existing 12-2 return metric ranked within manually curated themes.
    theme_news={}
    for entry in news or []:
        if not isinstance(entry,dict):continue
        topic=entry.get("topic")
        url=entry.get("url","")
        if topic not in THEME_GROUP or not isinstance(url,str) or not url.startswith("https://"):continue
        theme_news.setdefault(topic,[]).append({
            "title":str(entry.get("title") or "")[:220],
            "url":url,
            "published":str(entry.get("published") or "")[:60]
        })
    theme=[r for r in valid
           if r.get("theme_source")=="Curated" and r.get("theme") in THEME_GROUP
           and number(r.get("momentum_12_2")) is not None]
    theme.sort(key=lambda r:(-r["momentum_12_2"],r["ticker"]))
    theme_list=[row_entry(r,100*r["momentum_12_2"],thematic=True,
                           news=theme_news.get(r["theme"],[]))
                 for r in theme[:MAX_ITEMS]]

    ranks={}
    for kind,names in (("quality_momentum",qm_top),("quality_value_momentum",qvm_top),
                       ("bottleneck_hypotheses",[x["ticker"] for x in theme_list])):
        for i,t in enumerate(names,1):ranks.setdefault(t,{})[kind]=i
    overlap=[]
    for ticker,entry in ranks.items():
        if len(entry)<2:continue
        item=row_entry(by_ticker[t], qm.get(t,{}).get("score",qvm.get(t,{}).get("score",0)))
        item["appears_in"]=entry
        overlap.append(item)
    overlap.sort(key=lambda r:(-len(r["appears_in"]),sum(r["appears_in"].values()),r["ticker"]))
    return {
      "version":1,
      "as_of":generated_at,
      "eligible_recent_usd_quotes":len(valid),
      "quality_momentum_coverage":cohort,
      "qvm_coverage":len(qvm),
      "thematic_hypothesis_coverage":len(theme),
      "max_per_list":MAX_ITEMS,
      "methodology":{
        "quality_momentum":"Equal 50/50 quality and 12-2 momentum percentiles, only if annual SEC data and 12-2 prices exist",
        "quality_value_momentum":"Existing QVM pilot 1/3 each; same market price and annual financial facts; restricted US SEC coverage",
        "bottleneck_hypotheses":"Hand-curated sector classification and rank by 12-2 momentum ONLY; RSS news is sector-wide context, NOT causal firm evidence",
        "overlap":"Stocks present in at least two of the above top-10 research lists",
        "entry_exit":"Illustrative old ATR settings: buy=close-1 ATR, stop=buy-2.5 ATR; not validated for QVM",
        "sources":["Snapshot daily quotes","SEC EDGAR 10-K","Official TR Austria instrument list (ISIN match)","Thematic Google News RSS"],
        "performance_status":"No proven investable outperformance; sector hypotheses unverified"
      },
      "lists":{
          "quality_momentum":qm_list,
          "quality_value_momentum":qvm_list,
          "bottleneck_hypotheses":theme_list,
          "overlap":overlap
      },
      "disclaimers":{
          "broker":"TR-AT ISIN inclusion is not current orderability",
          "currency":"Daily reference FX conversion, not Trade Republic EUR bid/ask",
          "universe":"Partial and coverage-biased US stocks, plus curated themes; missing facts excluded, not assigned scores",
          "engpass":"No independently verified company-specific shortage evidence; ranks are hypotheses, not shortage return forecasts"
      }
    }
