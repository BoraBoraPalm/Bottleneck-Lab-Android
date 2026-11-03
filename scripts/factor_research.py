"""Literature-inspired observable factors; no fitted returns or buy probabilities.

Quality uses gross profits/assets; investment uses negative annual asset growth;
value uses dated common-equity book/market from an attributed provider. Earnings
momentum is our seasonal net-income model, not an EPS/consensus PEAD replication.
"""
import math
import re
import statistics
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timezone

VERSION = 1
RISK_BASIS = "Yahoo adjusted log returns; 252 sessions; annualised sqrt(252)"
FORMS = ("10-K", "10-K/A", "10-Q", "10-Q/A", "8-K", "8-K/A")
INCOME_TAGS = ("NetIncomeLoss", "ProfitLoss")
TICKER = re.compile(r"^[A-Z][A-Z0-9-]{0,9}$")


def number(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v)


def today(asof=None):
    return asof or datetime.now(timezone.utc).date()


def period(start, end, filed, asof):
    try:
        a, b, f = (date.fromisoformat(v) for v in (start, end, filed))
        return 70 <= (b-a).days <= 105 and b <= f <= asof
    except (TypeError, ValueError):
        return False


def sec_earnings_history(facts, asof=None):
    choices = []
    for tag in INCOME_TAGS:
        found = {}
        for r in facts.get("facts", {}).get("us-gaap", {}).get(tag, {}).get("units", {}).get("USD", []):
            if r.get("form") not in FORMS or not number(r.get("val")):
                continue
            if not period(r.get("start"), r.get("end"), r.get("filed"), today(asof)):
                continue
            item = {"start": r["start"], "end": r["end"], "filed": r["filed"],
                    "net_income": r["val"], "tag": tag, "derived": False}
            if item["end"] not in found or item["filed"] > found[item["end"]]["filed"]:
                found[item["end"]] = item
        if found:
            choices.append(sorted(found.values(), key=lambda x: x["end"]))
    rows = max(choices, key=lambda x: (x[-1]["end"], len(x))) if choices else []
    return {"source": "SEC EDGAR discrete quarterly net income", "currency": "USD", "rows": rows[-20:]}


def relay_earnings_history(payload, ticker, asof=None):
    out = {"source": "TGMCharts (SEC EDGAR quarterly net income)", "currency": "USD", "rows": []}
    if (payload.get("symbol", "").upper() != ticker or payload.get("period") != "quarterly"
            or payload.get("currency") != "USD" or payload.get("status")):
        return out
    found = {}
    latest = None
    for r in payload.get("rows") or []:
        if r.get("fiscalPeriod") not in ("Q1", "Q2", "Q3", "Q4") or r.get("form") not in FORMS:
            continue
        if not period(r.get("periodStart"), r.get("periodEnd"), r.get("filed"), today(asof)):
            continue
        latest = max(latest or r["periodEnd"], r["periodEnd"])
        v = (r.get("metrics") or {}).get("netIncome")
        p = (r.get("provenance") or {}).get("netIncome") or {}
        if (not number(v) or p.get("tag") not in INCOME_TAGS or p.get("form") not in FORMS
                or not period(r["periodStart"], r["periodEnd"], p.get("filed"), today(asof))):
            continue
        derived = p.get("derived")
        if derived and (derived != "ytd-differencing" or len(p.get("inputs") or []) != 2
                        or not all(isinstance(x, str) and x for x in p["inputs"])):
            continue
        item = {"start": r["periodStart"], "end": r["periodEnd"],
                "filed": max(r["filed"], p["filed"]), "net_income": v,
                "tag": p["tag"], "derived": bool(derived)}
        if item["end"] not in found or item["filed"] > found[item["end"]]["filed"]:
            found[item["end"]] = item
    out["rows"] = sorted(found.values(), key=lambda x: x["end"])[-20:]
    out["latest_report_end"] = latest
    return out


def long_risk_metrics(bars):
    if len(bars) < 253:
        return {}
    prices = [b[5] if len(b) >= 6 else None for b in bars[-253:]]
    if any(not number(v) or v <= 0 for v in prices):
        return {}
    returns = [math.log(b/a) for a, b in zip(prices, prices[1:])]
    if not all(math.isfinite(v) for v in returns):
        return {}
    return {"volatility_252d": round(statistics.stdev(returns)*math.sqrt(252), 8), "long_risk_basis": RISK_BASIS}


def parse_valuation(payload, ticker, asof=None):
    """Dated provider ratios for classified issuer common stock, never inferred EPS."""
    allowed = {"operating", "bank", "insurer", "capital_markets", "reit_equity", "reit_mortgage", "real_estate_operating"}
    classification = payload.get("classification") or {}
    if (payload.get("symbol", "").upper() != ticker or payload.get("currency") != "USD"
            or classification.get("type") not in allowed):
        return None
    price = payload.get("price") or {}
    try:
        close_date = date.fromisoformat(price["lastCloseDate"])
        updated = date.fromisoformat((payload.get("asOf") or {})["dataUpdatedAt"][:10])
        if not 0 <= (today(asof)-close_date).days <= 7 or not close_date <= updated <= today(asof):
            return None
    except (KeyError, TypeError, ValueError):
        return None
    if not number(price.get("lastClose")) or price["lastClose"] <= 0:
        return None
    valuation = payload.get("valuation") or {}
    pb = valuation.get("pbRatio")
    return {"source": "TGMCharts summary · common-equity P/B; TTM context", "price_date": close_date.isoformat(),
            "updated": updated.isoformat(), "close": price["lastClose"], "currency": "USD",
            "pb": pb if number(pb) and pb > 0 else None,
            "pe": valuation.get("peRatio") if number(valuation.get("peRatio")) else None,
            "earnings_yield": valuation["earningsYieldPercent"]/100 if number(valuation.get("earningsYieldPercent")) else None,
            "fcf_yield": valuation["fcfYieldPercent"]/100 if number(valuation.get("fcfYieldPercent")) else None,
            "classification": classification}


def _record(asof, source, reason="Die nötigen Daten fehlen."):
    return {"value": None, "state": "unknown", "status": "missing", "asof": asof.isoformat(),
            "source": source, "reason": reason, "metrics": {}}


def _ok(record, value, state, reason, metrics):
    record.update(value=round(value, 8), state=state, status="ok", reason=reason, metrics=metrics)
    return record


def _percent(v):
    return f"{100*v:.1f}".replace(".", ",")+" %"


def _annual_is_current(f, asof):
    try:
        end, filed = (date.fromisoformat(f[key]) for key in ("fy_end", "filed"))
        return end <= filed <= asof and (asof-end).days <= 550
    except (KeyError, TypeError, ValueError):
        return False


def factors_for_stock(stock, asof=None):
    now = today(asof)
    f = stock.get("fundamentals") or {}
    records = {key: _record(now, f.get("source", "SEC EDGAR")) for key in ("quality", "value", "earnings", "investment")}
    try:
        price_date = date.fromisoformat(stock.get("price_date", ""))
        if not 0 <= (now-price_date).days <= 7:
            return records
        effective = min(now, price_date)
    except (TypeError, ValueError):
        return records
    annual = _annual_is_current(f, effective) and f.get("currency") == "USD"
    financial = (re.search(r"financ|bank|insurance|versicherung|finanz|reit", (stock.get("stock_sector") or "")+" "+(stock.get("name") or ""), re.I)
                 or ((stock.get("valuation_data") or {}).get("classification") or {}).get("type")
                 in {"bank", "insurer", "capital_markets", "reit_equity", "reit_mortgage"})
    if annual:
        for key in records:
            records[key].update(report_end=f["fy_end"], filed=f["filed"])
        gp, assets = f.get("gross_profit"), f.get("assets")
        if financial:
            records["quality"]["reason"] = "Gross-Profit/Assets benötigt für diese Branche eine eigene Definition."
        elif number(gp) and number(assets) and assets > 0:
            ratio = gp/assets
            state = "green" if ratio >= .3 else "yellow" if ratio >= .15 else "orange" if ratio >= 0 else "red"
            _ok(records["quality"], ratio, state, "Bruttogewinn / Bilanzsumme: "+_percent(ratio)+".",
                {"gross_profit_to_assets": ratio, "cashflow_to_assets": f.get("cashflow_to_assets")})
        prior = f.get("prior_assets")
        try:
            assets_comparable=350 <= (date.fromisoformat(f["fy_end"])-date.fromisoformat(f.get("prior_assets_end",""))).days <= 385
        except (ValueError,TypeError):assets_comparable=False
        if assets_comparable and number(assets) and assets > 0 and number(prior) and prior > 0:
            change = assets/prior-1
            # Same direction as the rank (Fama/French CMA, Cooper/Gulen/Schill):
            # lower asset growth = more conservative, so colour and rank agree.
            state = "green" if change <= .05 else "yellow" if change <= .15 else "orange" if change <= .3 else "red"
            reason = "Bilanzsumme zum Vorjahr: "+_percent(change)+"."
            if change < -.2:
                reason += " Starke Schrumpfung: Verkäufe, Abspaltungen oder Sondereffekte zusätzlich prüfen."
            elif change < 0:
                reason += " Schrumpfung/Sondereffekte zusätzlich prüfen."
            _ok(records["investment"], -change, state, reason, {"asset_growth": change})
        v = stock.get("valuation_data") or {}
        try:
            valuation_current=date.fromisoformat(v["price_date"])<=date.fromisoformat(v["updated"])<=now
        except (KeyError,TypeError,ValueError):valuation_current=False
        if (v.get("price_date") == stock.get("price_date") and v.get("currency") == stock.get("currency") == "USD"
                and valuation_current and v.get("source")
                and number(stock.get("close")) and stock["close"] > 0 and number(v.get("close"))
                and abs(v["close"]/stock["close"]-1) <= .02 and number(v.get("pb")) and v["pb"] > 0):
            ratio = 1/v["pb"]
            state = "green" if ratio >= .5 else "yellow" if ratio >= .25 else "orange" if ratio >= .125 else "red"
            pb_text=f"{v['pb']:.2f}".replace(".",",")
            _ok(records["value"], ratio, state, f"Kurs/Buchwert {pb_text}×; kleinere Werte passen besser.",
                {"book_to_market": ratio, "pb": v["pb"], "pe": v.get("pe"), "earnings_yield": v.get("earnings_yield"), "fcf_yield": v.get("fcf_yield")})
            records["value"].update(source=v["source"], provider_date=v["price_date"], provider_updated=v["updated"])
        else:
            records["value"]["reason"] = "Datiertes, vergleichbares Kurs/Buchwert-Verhältnis fehlt."
    else:
        for key in ("quality", "value", "investment"):
            records[key]["reason"] = "Aktueller USD-Jahresbericht mit passenden Angaben fehlt."
    records["earnings"] = earnings_momentum(stock, effective, now)
    return records


def earnings_window(history, asof):
    """A continuous, same-tag window; never bridge a missing fiscal quarter."""
    if history.get("currency") != "USD":
        return []
    rows = [r for r in history.get("rows", []) if number(r.get("net_income"))
            and period(r.get("start"), r.get("end"), r.get("filed"), asof)]
    rows.sort(key=lambda x: x["end"])
    if len(rows) < 13:
        return []
    rows = rows[-13:]
    if (rows[-1]["end"] != (history.get("latest_report_end") or rows[-1]["end"])
            or len({r.get("tag") for r in rows}) != 1 or rows[0].get("tag") not in INCOME_TAGS):
        return []
    if any(abs((date.fromisoformat(b["start"])-date.fromisoformat(a["end"])).days-1) > 3
           for a, b in zip(rows, rows[1:])):
        return []
    if any(not 350 <= (date.fromisoformat(rows[i]["end"])-date.fromisoformat(rows[i-4]["end"])).days <= 385
           for i in range(4,13)):
        return []
    return rows


def earnings_momentum(stock, effective, now):
    q = (stock.get("fundamentals") or {}).get("quarterly") or {}
    history = q.get("earnings") or {}
    out = _record(now, history.get("source", "SEC EDGAR net income"), "Mindestens 13 lückenlose Quartalsgewinne derselben Basis fehlen.")
    rows = earnings_window(history, effective)
    if not rows:
        return out
    latest_end = max([r.get("end", "") for r in q.get("rows", [])]+[rows[-1]["end"]])
    if rows[-1]["end"] != latest_end:
        return out
    last = rows[-1]
    if (effective-date.fromisoformat(last["end"])).days > 180 or (effective-date.fromisoformat(last["filed"])).days > 120:
        out["reason"] = "Die jüngste Gewinnmeldung ist für dieses Modell zu alt."
        return out
    changes = [rows[i]["net_income"]-rows[i-4]["net_income"] for i in range(4, 13)]
    previous = changes[:-1]
    sigma = statistics.stdev(previous)
    if sigma <= 1e-9:
        out["reason"] = "Die vorherigen Gewinnänderungen haben keine belastbare Streuung."
        return out
    expected = rows[-5]["net_income"]+statistics.mean(previous)
    sue = (last["net_income"]-expected)/sigma
    state = "green" if sue >= 1 else "yellow" if sue >= 0 else "orange" if sue >= -1 else "red"
    sue_text=f"{sue:+.2f}".replace(".",",")
    _ok(out, sue, state, f"Quartalsgewinn {sue_text} Standardabweichungen vom Modellwert; kein Analystenkonsens.",
        {"earnings_deviation": sue, "net_income_actual": last["net_income"], "net_income_expected_model": expected,
         "sigma": sigma, "quarters": 13, "derived_quarters": sum(bool(r.get("derived")) for r in rows)})
    out.update(report_end=last["end"], filed=max(r["filed"] for r in rows), event_filed=last["filed"],
               model="Own seasonal net-income model plus drift; prior 8 YoY changes; sample standard deviation; not EPS SUE")
    return out


def enrich_factors(stocks, prior, fetch, maximum=60, asof=None):
    now = today(asof)
    previous = {s.get("ticker"): s for s in prior.get("stocks", [])}
    targets = []
    for s in stocks:
        old = previous.get(s.get("ticker"), {})
        cached = old.get("valuation_data")
        if isinstance(cached, dict):
            s["valuation_data"] = cached
        if (s.get("currency") != "USD" or not TICKER.fullmatch(s.get("ticker", ""))
                or not s.get("fundamentals") or not s.get("eligible_liquid_ranking")):
            continue
        if cached and cached.get("price_date") == s.get("price_date"):
            continue
        attempted = old.get("valuation_checked_at")
        s["valuation_checked_at"] = attempted
        if attempted == now.isoformat():
            continue
        targets.append(s)
    targets.sort(key=lambda s: (s["ticker"] not in {"MSFT", "AAPL", "GOOG", "GOOGL", "META", "AMZN", "TSLA", "BRK-B"}, s["ticker"]))
    targets = targets[:max(0, maximum)]
    def load(s):
        try:
            return parse_valuation(fetch("https://tgmcharts.com/api/v1/summary/"+s["ticker"], timeout=14, max_bytes=50000), s["ticker"], now)
        except Exception:
            return None
    with ThreadPoolExecutor(max_workers=3) as pool:
        for s, valuation in zip(targets, pool.map(load, targets)):
            s["valuation_checked_at"] = now.isoformat()
            if valuation:
                s["valuation_data"] = valuation
    counts = {key: 0 for key in ("quality", "value", "earnings", "investment")}
    for s in stocks:
        factors = factors_for_stock(s, now)
        s["factor_research"] = {"version": VERSION, **factors}
        for key in counts:
            counts[key] += factors[key]["status"] == "ok"
    return {"available": counts, "valuation_requests": len(targets),
            "limitations": "Observable factor definitions; own fit thresholds. Not a replicated portfolio or validated return forecast. Earnings is a net-income model, not EPS SUE or analyst consensus."}
