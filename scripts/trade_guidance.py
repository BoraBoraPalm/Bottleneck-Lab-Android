"""Transparent, conservative entry/exit *review* guidance, never broker orders.

The aim is to support a decision, not predict profits or assert a backtested
strategy. Rules intentionally simple, fixed and public:
- Last adjusted close above 200-day adjusted simple moving average.
- Long-term 12-2-month price momentum positive.
- Severe correction: adjusted close >=15% below 21-session-ago close OR
  >=25% below the 252-session peak (both conservative chosen risk warnings).
- An extra 8% / 15% milder decline flags attention.
- 2.5 ATR below the *current reference close* is a hypothetical fresh
  purchase risk budget, NOT a stop for an existing holding. ATR reflects
  the most recent 14 true ranges on corporate-action adjusted OHLC.
"""
import math
from datetime import date,datetime,timezone

CRASH_21=-0.15
CRASH_PEAK=-0.25
WARN_21=-0.08
WARN_PEAK=-0.15
ATR_MULT=2.5

def valid_number(v):
    try:
        num=float(v)
        return num if math.isfinite(num) and num>0 else None
    except (ValueError,TypeError):
        return None

def price_context(bars):
    """Calculate only from dates <= last downloaded trade, no future fields."""
    if len(bars)<253:return {}
    prices=[]
    adjusted_ohlc=[]
    for b in bars:
        if len(b)<6:return {}
        raw=valid_number(b[3])
        adj=valid_number(b[5])
        hi=valid_number(b[1])
        lo=valid_number(b[2])
        if None in (raw,adj,hi,lo) or hi<lo:return {}
        factor=adj/raw
        prices.append(adj)
        adjusted_ohlc.append((hi*factor,lo*factor,adj))
    last=prices[-1]
    sma=sum(prices[-200:])/200
    if sma<=0:return {}
    ret21=last/prices[-22]-1
    peak=max(prices[-252:])
    drawdown=last/peak-1
    changes=[]
    for i in range(len(adjusted_ohlc)-14,len(adjusted_ohlc)):
        hi,lo,_=adjusted_ohlc[i]
        prev=adjusted_ohlc[i-1][2]
        changes.append(max(hi-lo,abs(hi-prev),abs(lo-prev)))
    atr_adjusted=sum(changes)/len(changes)
    raw=valid_number(bars[-1][3])
    if raw is None:return {}
    atr_raw=atr_adjusted/last*raw
    if not math.isfinite(atr_raw) or atr_raw<=0:return {}
    crash=(ret21<=CRASH_21 or drawdown<=CRASH_PEAK)
    warning=(ret21<=WARN_21 or drawdown<=WARN_PEAK)
    return {
        "sma200_ratio":round(last/sma-1,7),
        "sma200_native":round(sma/last*raw,6),
        "crash_21_level_native":round(.85*prices[-22]/last*raw,6),
        "crash_peak_level_native":round(.75*peak/last*raw,6),
        "return_21d":round(ret21,7),
        "drawdown_252d":round(drawdown,7),
        "atr14_native":round(atr_raw,6),
        "crash_warning":crash,
        "correction_warning":warning,
        "risk_reference_native":round(max(0,raw-ATR_MULT*atr_raw),6),
        "context_basis":"Yahoo adjusted OHLC, signal after close"
    }

def assign_decision(stock,market_context=None):
    """Two distinct informational statuses: new entry and existing holding.

    Market data absence never generates an optimistic definitive BUY signal.
    For an actual position, the user's *own* entry and protective order remain
    unknown. Never claim that risk_reference protects an existing position.
    """
    m=stock.get("momentum_12_2")
    trend=stock.get("sma200_ratio")
    r21=stock.get("return_21d")
    dd=stock.get("drawdown_252d")
    price=stock.get("reference_close_eur")
    fx=stock.get("eur_per_unit")
    ref=stock.get("risk_reference_native")
    if not all(isinstance(v,(int,float)) and math.isfinite(v)
               for v in (m,trend,r21,dd,price,fx,ref)):
        stock["entry_review"]="insufficient_data"
        stock["exit_review"]="insufficient_data"
        return
    crash=stock.get("crash_warning") is True
    correction=stock.get("correction_warning") is True
    bearish=trend<0
    # A last close more than four calendar days old is not a current actionable
    # review. This tolerates a normal weekend, but fails closed on stale feeds.
    try:
        signal_date=date.fromisoformat(stock.get("price_date",""))
        days_old=(datetime.now(timezone.utc).date()-signal_date).days
    except (TypeError,ValueError):
        days_old=999
    market_risk=(market_context or {}).get("risk")
    if crash:
        entry="avoid_crash"
        exit_status="review_exit_crash"
    elif bearish:
        entry="wait_downtrend"
        exit_status="review_exit_trend"
    elif m<=0:
        entry="wait_momentum"
        exit_status="hold_review"
    elif correction:
        entry="wait_correction"
        exit_status="hold_review"
    elif market_risk in ("crash","downtrend"):
        entry="wait_market"
        exit_status="hold_review"
    elif market_risk is None:
        entry="market_unverified"
        exit_status="hold_review"
    else:
        entry="entry_review"
        exit_status="hold_review"
    if days_old<0 or days_old>4:
        entry="stale_quote"
        exit_status="insufficient_data"
    stock["entry_review"]=entry
    stock["exit_review"]=exit_status
    stock["risk_reference_eur"]=round(ref*fx,4)
    # Strictly a reference ceiling: no buy at a higher limit than last close,
    # next-day executable EUR quote must be checked in the broker.
    stock["entry_reference_eur"]=round(price,4)
    # Historical-style display: 1 x daily ATR below the last close as the
    # hypothetical limit; the initial protective level is another 2.5 x ATR
    # below that limit. These are illustrations, NOT proven optimal levels.
    # Never calculate them from a stale quote or unverifiable price history.
    native_close=stock.get("close")
    native_atr=stock.get("atr14_native")
    if (entry!="stale_quote" and isinstance(native_close,(int,float))
            and isinstance(native_atr,(int,float))
            and math.isfinite(native_close) and math.isfinite(native_atr)
            and native_close>0 and native_atr>0
            and stock.get("context_basis")=="Yahoo adjusted OHLC"):
        buy=native_close-native_atr
        stop=buy-2.5*native_atr
        if stop>0 and buy>0:
            stock["model_buy_limit_eur"]=round(buy*fx,4)
            stock["model_initial_stop_eur"]=round(stop*fx,4)
            stock["model_limit_rule"]="Last close - 1 ATR(14); initial stop = limit - 2.5 ATR(14)"

    for native,converted in (
       ("sma200_native","sma200_level_eur"),
       ("crash_21_level_native","crash_21_level_eur"),
       ("crash_peak_level_native","crash_peak_level_eur")
    ):
        level=stock.get(native)
        if isinstance(level,(int,float)) and math.isfinite(level) and level>0:
            stock[converted]=round(level*fx,4)


def market_risk_from_quote(market_quote):
    if not market_quote or not isinstance(market_quote,dict):
        return {"risk":None,"name":"ACWI ETF – global stock market proxy",
                "description":"No reliable international market trend available"}
    try:
        market_date=date.fromisoformat(market_quote.get("price_date",""))
        age=(datetime.now(timezone.utc).date()-market_date).days
    except (TypeError,ValueError):
        age=999
    if age<0 or age>4:
        return {"risk":None,"name":"ACWI ETF – global stock market proxy",
                "description":"Market close older than four days; no fresh global risk signal"}
    crash=market_quote.get("crash_warning")
    trend=market_quote.get("sma200_ratio")
    if not isinstance(trend,(int,float)) or crash is None:
        return {"risk":None,"name":"ACWI ETF – global stock market proxy",
                "description":"Insufficient adjusted price history"}
    risk="crash" if crash else "downtrend" if trend<0 else "normal"
    return {
        "risk":risk,"name":"ACWI ETF – global stock market proxy (US listing)",
        "trend200_pct":round(trend*100,2),
        "drop21_pct":round(100*market_quote["return_21d"],2),
        "date":market_quote.get("price_date"),
        "description":"US-listed global ETF as market proxy, not a total-world market indicator or actionable broker quote"
    }
