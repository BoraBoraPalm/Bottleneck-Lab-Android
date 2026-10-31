"""Experimental early-growth research screen, not a multibagger probability.

Quarterly YoY comparisons use discrete, dated USD statements. Annual and YTD
flows never masquerade as quarters. No analyst estimates or business moat is
inferred from price, themes, market cap, or missing data.
"""
import math
import re
from datetime import date, datetime, timezone

FORMS = ("10-K", "10-K/A", "10-Q", "10-Q/A")
REVENUE_TAGS = ("Revenues", "RevenueFromContractWithCustomerExcludingAssessedTax",
                "RevenueFromContractWithCustomerIncludingAssessedTax", "SalesRevenueNet",
                "SalesRevenueGoodsNet", "SalesRevenueServicesNet")
INCOME_TAGS = ("NetIncomeLoss", "ProfitLoss")
MAX_QUARTER_AGE = 180
MAX_ANNUAL_AGE = 550


def number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def _today(asof):
    return asof or datetime.now(timezone.utc).date()


def _period(start, end, filed, asof):
    try:
        a, b, f = (date.fromisoformat(v) for v in (start, end, filed))
        return 70 <= (b-a).days <= 105 and b <= f <= asof
    except (ValueError, TypeError):
        return False


def sec_quarters(facts, asof=None):
    """One consistent revenue tag per series; latest known filing per period.

    SEC does not always disclose Q4 discretely. We do not subtract unrelated
    annual/YTD restatements; the attributed relay can supply disclosed derived
    quarters instead. A tag's older, narrower series cannot mask a newer tag.
    """
    today = _today(asof)
    gaap = facts.get("facts", {}).get("us-gaap", {})

    def observations(tag):
        result = {}
        for row in gaap.get(tag, {}).get("units", {}).get("USD", []):
            if row.get("form") not in FORMS or not number(row.get("val")):
                continue
            if not _period(row.get("start"), row.get("end"), row.get("filed"), today):
                continue
            key = (row["start"], row["end"])
            if key not in result or row["filed"] > result[key]["filed"]:
                result[key] = row
        return result

    income = [observations(tag) for tag in INCOME_TAGS]
    choices = []
    for tag in REVENUE_TAGS:
        rows = []
        for key, row in observations(tag).items():
            if row["val"] <= 0:
                continue
            net = next((series[key] for series in income if key in series), None)
            rows.append({"start": row["start"], "end": row["end"],
                         "filed": max(row["filed"], net["filed"] if net else row["filed"]),
                         "revenue": row["val"], "net_income": net["val"] if net else None,
                         "revenue_tag": tag, "derived": False})
        rows.sort(key=lambda x: x["end"])
        if rows:
            choices.append(rows)
    rows = max(choices, key=lambda x: (x[-1]["end"], len(x))) if choices else []
    return {"source": "SEC EDGAR 10-K/10-Q XBRL (US-GAAP)", "currency": "USD", "rows": rows[-16:]}


def relay_quarters(payload, ticker, asof=None):
    """Validate documented TGMCharts rows and each used value's provenance."""
    today = _today(asof)
    result = {"source": "TGMCharts (SEC EDGAR 10-K/10-Q XBRL)", "currency": "USD", "rows": []}
    if (payload.get("symbol", "").upper() != ticker or payload.get("period") != "quarterly"
            or payload.get("currency") != "USD" or payload.get("status")):
        return result
    found = {}
    for row in payload.get("rows") or []:
        if row.get("form") not in FORMS or row.get("fiscalPeriod") not in ("Q1", "Q2", "Q3", "Q4"):
            continue
        if not _period(row.get("periodStart"), row.get("periodEnd"), row.get("filed"), today):
            continue

        def value(key):
            val = (row.get("metrics") or {}).get(key)
            p = (row.get("provenance") or {}).get(key) or {}
            try:
                filed = date.fromisoformat(p["filed"])
                end = date.fromisoformat(row["periodEnd"])
                if not end <= filed <= today or p.get("form") not in FORMS or not p.get("tag"):
                    return None
                derived = p.get("derived")
                if derived and (derived != "ytd-differencing" or len(p.get("inputs") or []) != 2
                                or not all(isinstance(x, str) and x for x in p["inputs"])):
                    return None
            except (KeyError, TypeError, ValueError):
                return None
            return val if number(val) else None

        revenue = value("revenue")
        if revenue is None or revenue <= 0:
            continue
        net = value("netIncome")
        prov = row["provenance"]["revenue"]
        filed = max(row["filed"], prov["filed"],
                    row["provenance"]["netIncome"]["filed"] if net is not None else row["filed"])
        item = {"start": row["periodStart"], "end": row["periodEnd"], "filed": filed,
                "revenue": revenue, "net_income": net, "revenue_tag": prov["tag"],
                "derived": bool(prov.get("derived"))}
        if item["end"] not in found or filed > found[item["end"]]["filed"]:
            found[item["end"]] = item
    result["rows"] = sorted(found.values(), key=lambda x: x["end"])[-16:]
    return result


def comparable_quarters(quarterly, asof=None):
    """The latest three consecutive quarters, each with a same-tag YoY pair.

    Never skip a missing latest comparison to make an old acceleration appear
    current. Fiscal calendars may use 52/53-week years.
    """
    today = _today(asof)
    if not isinstance(quarterly, dict) or quarterly.get("currency") != "USD":
        return []
    rows = [r for r in quarterly.get("rows", []) if isinstance(r, dict)
            and _period(r.get("start"), r.get("end"), r.get("filed"), today)
            and number(r.get("revenue")) and r["revenue"] > 0]
    rows.sort(key=lambda x: x["end"])
    recent = rows[-3:]
    if len(recent) != 3 or any(not 70 <= (date.fromisoformat(b["end"])-date.fromisoformat(a["end"])).days <= 110
                               or abs((date.fromisoformat(b["start"])-date.fromisoformat(a["end"])).days-1) > 3
                               for a, b in zip(recent, recent[1:])):
        return []
    output = []
    for current in recent:
        end = date.fromisoformat(current["end"])
        duration = (end-date.fromisoformat(current["start"])).days
        previous = [r for r in rows if 350 <= (end-date.fromisoformat(r["end"])).days <= 385
                    and abs((date.fromisoformat(r["end"])-date.fromisoformat(r["start"])).days-duration) <= 14
                    and r.get("revenue_tag") and r.get("revenue_tag") == current.get("revenue_tag")]
        if not previous:
            return []
        prior = min(previous, key=lambda r: abs((end-date.fromisoformat(r["end"])).days-365))
        margin = current["net_income"]/current["revenue"] if number(current.get("net_income")) else None
        prior_margin = prior["net_income"]/prior["revenue"] if number(prior.get("net_income")) else None
        output.append({"end": current["end"], "prior_end": prior["end"],
                       "filed": max(current["filed"], prior["filed"]),
                       "revenue_growth_yoy": round(current["revenue"]/prior["revenue"]-1, 7),
                       "net_margin": round(margin, 7) if margin is not None else None,
                       "prior_net_margin": round(prior_margin, 7) if prior_margin is not None else None,
                       "derived": bool(current.get("derived") or prior.get("derived"))})
    return output


def price_metrics(bars):
    """Six-month adjusted returns/highs and split-resistant traded-value ratio."""
    if len(bars) < 127:
        return {}
    recent = bars[-127:]
    if any(len(b) < 6 or not number(b[5]) or b[5] <= 0 for b in recent):
        return {}
    prices = [b[5] for b in recent]
    turnover = [b[3]*b[4] if number(b[3]) and b[3] > 0 and number(b[4]) and b[4] > 0 else None
                for b in recent[-21:]]
    earlier = [v for v in turnover[:-1] if v is not None]
    ratio = turnover[-1]/(sum(earlier)/len(earlier)) if turnover[-1] is not None and len(earlier) >= 15 else None
    return {"return_63d": round(prices[-1]/prices[-64]-1, 7),
            "return_126d": round(prices[-1]/prices[-127]-1, 7),
            "breakout_63d_ratio": round(prices[-1]/max(prices[-64:-1])-1, 7),
            "turnover_ratio_20d": round(ratio, 6) if ratio is not None else None,
            "growth_price_basis": "Yahoo adjusted closes; native price x share volume; 127 sessions"}


def _scale(value, low, high):
    return 100*max(0, min(1, (value-low)/(high-low)))


def growth_screen(stock, benchmark, asof=None):
    """Fixed research heuristics with independent components and explicit gaps."""
    today = _today(asof)
    out = {"score": None, "growth_score": None, "quality_score": None, "confirmation_score": None,
           "status": "missing_quarters", "quarters": [],
           "unchecked": ["earnings_surprises", "valuation", "competitive_moat", "share_dilution"]}
    fund = stock.get("fundamentals") or {}
    quarterly = fund.get("quarterly") or {}
    out["source"] = quarterly.get("source")
    # Do not combine statements released after the stock's last observed close.
    try:
        price_date = date.fromisoformat(stock.get("price_date", ""))
        evaluation = min(today, price_date)
    except (ValueError, TypeError):
        out["status"] = "missing_price"
        return out
    quarters = comparable_quarters(quarterly, evaluation)
    if not quarters:
        return out
    out["quarters"] = quarters
    last = quarters[-1]
    if (evaluation-date.fromisoformat(last["end"])).days > MAX_QUARTER_AGE:
        out["status"] = "stale_quarters"
        return out
    growth = [q["revenue_growth_yoy"] for q in quarters]
    acceleration = growth[-1]-growth[-2]
    out["revenue_acceleration"] = round(acceleration, 7)
    out["growth_score"] = round(.5*_scale(growth[-1], 0, .6)
                               + .3*_scale(sum(growth)/3, 0, .4)
                               + .2*_scale(acceleration, 0, .2), 2)
    # Generic cash-flow rules are inappropriate for financial issuers and REITs.
    if re.search(r"financ|bank|insurance|versicherung|finanz|reit", (stock.get("stock_sector") or "")+" "+(stock.get("name") or ""), re.I):
        out["status"] = "sector_specific"
        return out
    try:
        annual_end = date.fromisoformat(fund["fy_end"])
        filed = date.fromisoformat(fund["filed"])
        if not annual_end <= filed <= evaluation or (evaluation-annual_end).days > MAX_ANNUAL_AGE:
            out["status"] = "stale_financials"
            return out
    except (KeyError, TypeError, ValueError):
        out["status"] = "missing_quality"
        return out
    margin, prior_margin, cash = last["net_margin"], last["prior_net_margin"], fund.get("operating_cashflow_margin")
    if not all(number(x) for x in (margin, prior_margin, cash)):
        out["status"] = "missing_quality"
        return out
    improvement = margin-prior_margin
    out["net_margin_change_yoy"] = round(improvement, 7)
    out["annual_cashflow_margin"] = cash
    out["annual_end"] = fund["fy_end"]
    out["quality_score"] = round(.4*_scale(margin, -.1, .2)
                                + .2*_scale(improvement, -.05, .1)
                                + .4*_scale(cash, 0, .25), 2)
    out["status"] = "missing_price"
    if (not 0 <= (today-price_date).days <= 7 or stock.get("source") != "Yahoo Finance"
            or not str(stock.get("growth_price_basis") or "").startswith("Yahoo adjusted closes")
            or not isinstance(benchmark, dict) or benchmark.get("date") != stock.get("price_date")
            or not str(benchmark.get("growth_price_basis") or "").startswith("Yahoo adjusted closes")):
        return out
    keys = ("return_63d", "return_126d", "breakout_63d_ratio", "turnover_ratio_20d")
    values = [stock.get(k) for k in keys]
    market = [benchmark.get(k) for k in keys[:2]]
    if (not all(number(x) for x in values+market) or any(v <= -1 for v in market+values[:2])
            or stock["turnover_ratio_20d"] <= 0):
        return out
    rs63 = (1+stock["return_63d"])/(1+market[0])-1
    rs126 = (1+stock["return_126d"])/(1+market[1])-1
    out.update({"relative_63d": round(rs63, 7), "relative_126d": round(rs126, 7),
                "breakout_63d_ratio": stock["breakout_63d_ratio"],
                "turnover_ratio_20d": stock["turnover_ratio_20d"], "benchmark": "ACWI", "price_date": stock["price_date"]})
    out["confirmation_score"] = round(.35*_scale(rs63, -.1, .3) + .25*_scale(rs126, -.1, .5)
                                     + .25*_scale(stock["breakout_63d_ratio"], -.15, .05)
                                     + .15*_scale(stock["turnover_ratio_20d"], .7, 2), 2)
    out["status"] = "criteria_not_met"
    # Positive operating cash flow narrows the screen; it deliberately omits
    # pre-revenue and cash-burning ventures rather than guessing their runway.
    if (growth[-1] < .20 or (growth[0]+growth[1])/2 < .10 or acceleration < .02-1e-9
            or cash <= 0 or (margin < 0 and improvement < .03)
            or stock["return_63d"] <= 0 or rs63 <= 0 or stock["breakout_63d_ratio"] < -.15):
        return out
    out["score"] = round(.45*out["growth_score"] + .30*out["quality_score"] + .25*out["confirmation_score"], 2)
    out["status"] = "qualified"
    return out


def enrich_growth(stocks, benchmark, asof=None):
    checked = qualified = 0
    for stock in stocks:
        radar = growth_screen(stock, benchmark, asof)
        stock["growth_radar"] = radar
        stock["growth_score"] = radar["score"]
        checked += bool(radar["quarters"])
        qualified += radar["status"] == "qualified"
    return {"name": "Frühwachstum / Multibagger-Kandidaten", "with_comparable_quarters": checked,
            "qualified_candidates": qualified, "weights": {"growth": .45, "quality": .30, "confirmation": .25},
            "source": "SEC EDGAR discrete 10-K/10-Q USD quarters, direct or attributed TGMCharts relay; Yahoo adjusted prices; ACWI",
            "limitations": "Experimental fixed rules, not validated as an investment strategy or a probability. Mostly US coverage. No estimates, valuation, moat or dilution assessment. Positive annual operating cash flow required."}
