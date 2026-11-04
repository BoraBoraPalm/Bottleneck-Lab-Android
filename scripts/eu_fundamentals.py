"""Annual IFRS fundamentals of EU/EEA issuers from official ESEF reports.

Since 2021, issuers on EU regulated markets publish their annual financial
report in ESEF (inline XBRL, IFRS taxonomy). filings.xbrl.org (XBRL
International) collects these reports and offers xBRL-JSON conversions;
GLEIF maps the stock's ISIN to the issuer's LEI. Only undimensioned facts of
that LEI are used: annual durations (335–385 days) ending on the report's
period end and balance-sheet instants at that date. Missing values stay
missing, nothing is estimated. Ratios use the same definitions as the SEC
path; absolute amounts stay in the reporting currency.
"""
import gzip
import json
import math
import re
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timedelta, timezone
from urllib.request import Request, urlopen

from sander_fundamentals import _derived_metrics

GLEIF = "https://api.gleif.org/api/v1/lei-records?filter%5Bisin%5D="
FILINGS = "https://filings.xbrl.org/api/entities/{lei}/filings?page%5Bsize%5D=50"
SITE = "https://filings.xbrl.org"
USER_AGENT = "Bottleneck Lab nonprofit research (github.com/BoraBoraPalm/Bottleneck-Lab-Android)"
SOURCE = "ESEF-Jahresfinanzbericht (IFRS) · filings.xbrl.org"
VERSION = 1
DEFAULT_MAX = 25
REFRESH_DAYS = 21      # re-check a verified report after three weeks
KEEP_DAYS = 60         # keep a verified report this long if re-checks fail
RETRY_DAYS = 3         # wait after an unsuccessful lookup
MAX_REPORT_AGE = 550   # same staleness limit as the display
MAX_REPORT_BYTES = 60_000_000
EEA = {"AT", "BE", "BG", "HR", "CY", "CZ", "DK", "EE", "FI", "FR", "DE", "GR", "HU", "IE", "IT",
       "LV", "LT", "LU", "MT", "NL", "PL", "PT", "RO", "SK", "SI", "ES", "SE", "NO", "IS", "LI"}
ISIN = re.compile(r"^[A-Z]{2}[A-Z0-9]{9}[0-9]$")
LEI = re.compile(r"^[A-Z0-9]{18}[0-9]{2}$")
IFRS_NAMESPACE = re.compile(r"^https?://xbrl\.ifrs\.org/taxonomy/\d{4}-\d{2}-\d{2}/ifrs-full/?$")
# First matching concept wins. Net income and equity attributable to the
# parent match the SEC fields NetIncomeLoss and StockholdersEquity.
DURATION = {
    "revenue": ("Revenue", "RevenueFromContractsWithCustomers"),
    "net_income": ("ProfitLossAttributableToOwnersOfParent", "ProfitLoss"),
    "operating_cashflow": ("CashFlowsFromUsedInOperatingActivities",),
    "capex": ("PurchaseOfPropertyPlantAndEquipmentClassifiedAsInvestingActivities",),
    "gross_profit": ("GrossProfit",),
}
INSTANT = {
    "assets": ("Assets",),
    "equity": ("EquityAttributableToOwnersOfParent", "Equity"),
    "liabilities": ("Liabilities",),
    "current_assets": ("CurrentAssets",),
    "current_liabilities": ("CurrentLiabilities",),
}
PLAIN_DIMENSIONS = {"concept", "entity", "period", "unit", "language"}


def fetch_json(url, timeout=30, max_bytes=8_000_000):
    req = Request(url, headers={"User-Agent": USER_AGENT, "Accept-Encoding": "gzip",
                                "Accept": "application/vnd.api+json, application/json"})
    with urlopen(req, timeout=timeout) as resp:
        if resp.status != 200:
            raise RuntimeError("HTTP " + str(resp.status))
        raw = resp.read(max_bytes + 1)
        encoding = resp.headers.get("Content-Encoding", "")
    if len(raw) > max_bytes:
        raise RuntimeError("Response too large")
    if encoding == "gzip" or raw[:2] == b"\x1f\x8b":
        raw = gzip.decompress(raw)
        if len(raw) > MAX_REPORT_BYTES:
            raise RuntimeError("Response too large")
    return json.loads(raw)


def today_utc():
    return datetime.now(timezone.utc).date()


def eea_isin(isin):
    value = str(isin or "").strip().upper()
    return value if ISIN.fullmatch(value) and value[:2] in EEA else None


def lei_for_isin(isin, fetch=fetch_json):
    payload = fetch(GLEIF + isin, timeout=20, max_bytes=2_000_000)
    leis = {str((row.get("attributes") or {}).get("lei") or row.get("id") or "").upper()
            for row in payload.get("data") or [] if isinstance(row, dict)}
    leis = {value for value in leis if LEI.fullmatch(value)}
    # An ISIN must map to exactly one issuer; anything else stays unknown.
    return leis.pop() if len(leis) == 1 else None


def latest_filing(lei, fetch=fetch_json, today=None):
    today = today or today_utc()
    payload = fetch(FILINGS.format(lei=lei), timeout=30, max_bytes=4_000_000)
    choices = []
    for row in payload.get("data") or []:
        a = (row or {}).get("attributes") or {}
        try:
            end = date.fromisoformat(a["period_end"])
            added = date.fromisoformat(str(a.get("date_added") or a.get("processed") or "")[:10])
        except (KeyError, TypeError, ValueError):
            continue
        url = a.get("json_url")
        if not isinstance(url, str) or not url.startswith("/") or end > today or added > today:
            continue
        choices.append((end, -(a.get("error_count") or 0), added, a))
    if not choices:
        return None
    end, _, added, attributes = max(choices, key=lambda c: (c[0], c[1], c[2]))
    return {"period_end": end, "added": added, "json_url": attributes["json_url"],
            "viewer_url": attributes.get("viewer_url"), "fxo_id": attributes.get("fxo_id"),
            "country": attributes.get("country")}


def _date_part(text):
    match = re.fullmatch(r"(\d{4}-\d{2}-\d{2})(?:T(\d{2}):(\d{2}):(\d{2}))?", text.strip())
    if not match:
        raise ValueError("period")
    day = date.fromisoformat(match.group(1))
    return day, match.group(2) is not None and match.groups()[1:] == ("00", "00", "00")


def _end_date(text):
    # xBRL-JSON: "YYYY-MM-DDT00:00:00" is the end of the previous day.
    day, midnight = _date_part(text)
    return day - timedelta(days=1) if midnight else day


def _period(text):
    if "/" in text:
        start, end = text.split("/", 1)
        return _date_part(start)[0], _end_date(end)
    return None, _end_date(text)


def _number(value):
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def report_facts(report, lei):
    """Undimensioned IFRS monetary facts of the LEI: {(concept, start, end, unit): value}."""
    namespaces = ((report.get("documentInfo") or {}).get("namespaces") or {})
    prefixes = {p for p, uri in namespaces.items() if isinstance(uri, str) and IFRS_NAMESPACE.match(uri)}
    wanted = {c for names in list(DURATION.values()) + list(INSTANT.values()) for c in names}
    grouped = {}
    for fact in (report.get("facts") or {}).values():
        dims = (fact or {}).get("dimensions") or {}
        if not isinstance(dims, dict) or set(dims) - PLAIN_DIMENSIONS:
            continue
        prefix, _, local = str(dims.get("concept") or "").partition(":")
        unit = str(dims.get("unit") or "")
        if prefix not in prefixes or local not in wanted or not re.fullmatch(r"iso4217:[A-Z]{3}", unit):
            continue
        if str(dims.get("entity") or "").rpartition(":")[2].upper() != lei:
            continue
        value = _number(fact.get("value"))
        try:
            start, end = _period(str(dims.get("period") or ""))
        except ValueError:
            continue
        if value is None:
            continue
        decimals = fact.get("decimals")
        precision = decimals if isinstance(decimals, int) else 99
        grouped.setdefault((local, start, end, unit[-3:]), []).append((precision, value))
    facts = {}
    for key, values in grouped.items():
        best = max(p for p, _ in values)
        chosen = {v for p, v in values if p == best}
        if len(chosen) == 1:  # conflicting duplicates stay unknown
            facts[key] = chosen.pop()
    return facts


def annual_from_report(report, lei, filing, today=None):
    today = today or today_utc()
    end = filing["period_end"]
    if (today - end).days > MAX_REPORT_AGE:
        return None
    facts = report_facts(report, lei)
    currencies = sorted({k[3] for k in facts if k[0] in DURATION["revenue"] + INSTANT["assets"]})
    if len(currencies) != 1:
        return None
    currency = currencies[0]

    def duration(names, year_end):
        for name in names:
            for (local, start, stop, unit), value in facts.items():
                if (local == name and unit == currency and start and stop == year_end
                        and 335 <= (stop - start).days + 1 <= 385):
                    return value
        return None

    def instant(names, day):
        for name in names:
            value = facts.get((name, None, day, currency))
            if value is not None:
                return value
        return None

    prior_end = next((stop for (local, start, stop, unit) in facts
                      if local in DURATION["revenue"] and unit == currency and start
                      and 358 <= (end - stop).days <= 372), None)
    annual = {key: duration(names, end) for key, names in DURATION.items()}
    annual.update({key: instant(names, end) for key, names in INSTANT.items()})
    if annual["revenue"] is None and annual["assets"] is None:
        return None
    if annual["capex"] is not None:
        annual["capex"] = abs(annual["capex"])  # IFRS reports payments as positive outflows
    if prior_end:
        annual["prior_revenue"] = duration(DURATION["revenue"], prior_end)
        annual["prior_net_income"] = duration(DURATION["net_income"], prior_end)
    prior_assets_end = next((stop for (local, start, stop, unit) in facts
                             if local in INSTANT["assets"] and unit == currency and start is None
                             and 350 <= (end - stop).days <= 385), None)
    if prior_assets_end:
        annual["prior_assets"] = instant(INSTANT["assets"], prior_assets_end)
        annual["prior_assets_end"] = prior_assets_end.isoformat()
    annual = {k: v for k, v in annual.items() if v is not None}
    annual.update(fy_end=end.isoformat(), filed=filing["added"].isoformat(),
                  balance_filed=filing["added"].isoformat(),
                  base_year_end=prior_end.isoformat() if prior_end else None)
    annual = _derived_metrics(annual)
    viewer = filing.get("viewer_url")
    annual.update(currency=currency, source=SOURCE, provider="filings.xbrl.org", lei=lei,
                  report_url=SITE + viewer if isinstance(viewer, str) and viewer.startswith("/") else None,
                  esef_version=VERSION, quarterly={})
    return annual


def load_annual(isin, lei=None, fetch=fetch_json, today=None):
    lei = lei or lei_for_isin(isin, fetch)
    if not lei:
        return None, None
    filing = latest_filing(lei, fetch, today)
    if not filing:
        return lei, None
    report = fetch(SITE + filing["json_url"], timeout=60, max_bytes=MAX_REPORT_BYTES)
    return lei, annual_from_report(report, lei, filing, today)


def _age(value, today):
    try:
        return (today - date.fromisoformat(str(value))).days
    except (TypeError, ValueError):
        return None


def enrich_eu_fundamentals(stocks, prior, fetch=fetch_json, maximum=DEFAULT_MAX, tr_isins=None, today=None):
    """Attach ESEF annual data to EU/EEA stocks; bounded requests per run."""
    today = today or today_utc()
    old = {s.get("ticker"): s for s in (prior or {}).get("stocks", []) if isinstance(s, dict)}
    candidates = []
    for stock in stocks:
        isin = eea_isin(stock.get("reference_isin"))
        if not isin or str(stock.get("ticker", "")).find(".") < 0:
            continue
        previous = old.get(stock.get("ticker"), {})
        for key in ("lei", "eu_fundamentals_checked_at"):
            if previous.get(key):
                stock[key] = previous[key]
        cached = previous.get("fundamentals")
        age = _age((cached or {}).get("checked_at"), today) if isinstance(cached, dict) else None
        if (isinstance(cached, dict) and cached.get("provider") == "filings.xbrl.org"
                and age is not None and 0 <= age <= KEEP_DAYS):
            stock["fundamentals"] = cached
        candidates.append((stock, isin))

    def due(item):
        stock, _ = item
        fund = stock.get("fundamentals") or {}
        age = _age(fund.get("checked_at"), today) if fund else None
        if age is not None and 0 <= age < REFRESH_DAYS:
            return False
        attempted = _age(stock.get("eu_fundamentals_checked_at"), today)
        return not (attempted is not None and 0 <= attempted < RETRY_DAYS)

    listed = tr_isins or set()
    queue = sorted((c for c in candidates if due(c)), key=lambda c: (
        bool(c[0].get("fundamentals")),                       # no data first
        not c[0].get("eligible_liquid_ranking"),              # tradable liquid names first
        c[1] not in listed,                                   # Trade Republic AT list first
        -(c[0].get("avg_turnover_20d_eur") or 0), c[0]["ticker"]))[:max(0, maximum)]

    def work(item):
        stock, isin = item
        try:
            return load_annual(isin, stock.get("lei"), fetch, today)
        except Exception as exc:
            return stock.get("lei"), exc

    loaded = errors = 0
    with ThreadPoolExecutor(max_workers=3) as pool:
        for (stock, _), (lei, result) in zip(queue, pool.map(work, queue)):
            stock["eu_fundamentals_checked_at"] = today.isoformat()
            if lei:
                stock["lei"] = lei
            if isinstance(result, Exception):
                errors += 1
            elif result:
                result["checked_at"] = today.isoformat()
                stock["fundamentals"] = result
                loaded += 1
    return {"source": SOURCE, "lei_source": "GLEIF ISIN-LEI mapping",
            "eligible_eea_stocks": len(candidates), "checked_this_run": len(queue),
            "reports_loaded": loaded, "errors": errors,
            "with_esef_fundamentals": sum(1 for s, _ in candidates
                                          if (s.get("fundamentals") or {}).get("provider") == "filings.xbrl.org"),
            "limitations": "Annual consolidated IFRS figures only; banks/insurers may lack revenue; "
                           "no quarterly data; report availability date of the collection, not the official publication date."}
