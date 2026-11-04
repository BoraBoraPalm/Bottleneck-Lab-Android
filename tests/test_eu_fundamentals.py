"""ESEF annual data: exact xBRL-JSON semantics, no estimates, bounded requests."""
import sys
import unittest
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import eu_fundamentals as eu
import factor_research as fr
import sander_fundamentals as sf

LEI = "969500MOSL3L2PMI9P51"
TODAY = date(2026, 11, 4)
IFRS = "https://xbrl.ifrs.org/taxonomy/2024-03-27/ifrs-full"


def fact(concept, value, period, unit="iso4217:EUR", entity="lei:" + LEI, decimals=-6, **extra):
    dims = {"concept": concept, "entity": entity, "period": period}
    if unit:
        dims["unit"] = unit
    dims.update(extra)
    return {"value": str(value), "decimals": decimals, "dimensions": dims}


FY = "2025-01-01T00:00:00/2026-01-01T00:00:00"      # 2025-01-01 .. 2025-12-31
PY = "2024-01-01T00:00:00/2025-01-01T00:00:00"
END = "2026-01-01T00:00:00"                           # instant 2025-12-31
PEND = "2025-01-01T00:00:00"                          # instant 2024-12-31


def report(**changes):
    facts = {
        "r1": fact("ifrs-full:Revenue", 44000e6, FY),
        "r0": fact("ifrs-full:Revenue", 40000e6, PY),
        "n1": fact("ifrs-full:ProfitLossAttributableToOwnersOfParent", 6600e6, FY),
        "n0": fact("ifrs-full:ProfitLossAttributableToOwnersOfParent", 5500e6, PY),
        "nt": fact("ifrs-full:ProfitLoss", 6800e6, FY),
        "c1": fact("ifrs-full:CashFlowsFromUsedInOperatingActivities", 9000e6, FY),
        "x1": fact("ifrs-full:PurchaseOfPropertyPlantAndEquipmentClassifiedAsInvestingActivities", 2000e6, FY),
        "a1": fact("ifrs-full:Assets", 130000e6, END),
        "a0": fact("ifrs-full:Assets", 125000e6, PEND),
        "e1": fact("ifrs-full:EquityAttributableToOwnersOfParent", 75000e6, END),
        "et": fact("ifrs-full:Equity", 76000e6, END),
        "ca": fact("ifrs-full:CurrentAssets", 40000e6, END),
        "cl": fact("ifrs-full:CurrentLiabilities", 25000e6, END),
        # Must be ignored: segment member, another entity, extension concept,
        # quarterly duration, non-currency unit.
        "seg": fact("ifrs-full:Revenue", 1e6, FY, **{"ifrs-full:SegmentsAxis": "san:PharmaMember"}),
        "oth": fact("ifrs-full:Revenue", 2e6, FY, entity="lei:529900T8BM49AURSDO55"),
        "ext": fact("san:Revenue", 3e6, FY),
        "q4": fact("ifrs-full:Revenue", 11000e6, "2025-10-01T00:00:00/2026-01-01T00:00:00"),
        "shr": fact("ifrs-full:Revenue", 5, FY, unit="xbrli:shares"),
        "dup": fact("ifrs-full:Revenue", 44000e6, FY, decimals=-6),
    }
    facts.update(changes.pop("facts", {}))
    for key in changes.pop("drop", ()):
        facts.pop(key)
    return {"documentInfo": {"documentType": "https://xbrl.org/2021/xbrl-json",
                             "namespaces": {"ifrs-full": IFRS, "lei": "http://standards.iso.org/iso/17442",
                                            "iso4217": "http://www.xbrl.org/2003/iso4217", "san": "http://www.sanofi.com/2025"}},
            "facts": facts}


FILING = {"period_end": date(2025, 12, 31), "added": date(2026, 3, 1), "json_url": "/x.json",
          "viewer_url": "/" + LEI + "/2025-12-31/ESEF/FR/0/san/reports/ixbrlviewer.html"}


def gleif(*leis):
    return {"data": [{"type": "lei-records", "id": lei, "attributes": {"lei": lei, "entity": {"legalName": {"name": "SANOFI"}}}}
                     for lei in leis]}


def filings(*rows):
    return {"data": [{"type": "filing", "id": str(i), "attributes": row} for i, row in enumerate(rows)],
            "meta": {"count": len(rows)}, "jsonapi": {"version": "1.0"}}


def filing_row(end, added="2026-03-01 10:00:00.1", url="/a.json", errors=0):
    return {"period_end": end, "date_added": added, "json_url": url, "error_count": errors,
            "viewer_url": "/v.html", "fxo_id": LEI + "-" + end + "-ESEF-FR-0", "country": "FR"}


class ReportParsing(unittest.TestCase):
    def test_annual_figures_follow_xbrl_json_periods(self):
        a = eu.annual_from_report(report(), LEI, FILING, TODAY)
        self.assertEqual(a["currency"], "EUR")
        self.assertEqual(a["revenue"], 44000e6, "segment, other entity, extension and Q4 facts ignored")
        self.assertEqual(a["prior_revenue"], 40000e6)
        self.assertEqual(a["net_income"], 6600e6, "attributable to the parent, like SEC NetIncomeLoss")
        self.assertEqual(a["equity"], 75000e6)
        self.assertEqual(a["assets"], 130000e6)
        self.assertEqual(a["prior_assets"], 125000e6)
        self.assertEqual(a["prior_assets_end"], "2024-12-31", "instant T00:00:00 is the end of the previous day")
        self.assertEqual(a["fy_end"], "2025-12-31")
        self.assertEqual(a["filed"], "2026-03-01")
        self.assertAlmostEqual(a["revenue_growth_yoy"], .1)
        self.assertAlmostEqual(a["profit_margin"], .15)
        self.assertAlmostEqual(a["free_cashflow"], 7000e6)
        self.assertAlmostEqual(a["current_ratio"], 1.6)
        self.assertNotIn("liabilities", a, "untagged total liabilities are not derived")
        self.assertIsNone(a["liabilities_to_equity"])
        self.assertTrue(a["quality_ok"])
        self.assertEqual(a["provider"], "filings.xbrl.org")
        self.assertTrue(a["report_url"].startswith("https://filings.xbrl.org/"))
        self.assertEqual(a["quarterly"], {})

    def test_missing_or_conflicting_values_stay_missing(self):
        conflict = report(facts={"dup": fact("ifrs-full:Revenue", 45000e6, FY)})
        self.assertIsNone(eu.annual_from_report(conflict, LEI, FILING, TODAY).get("revenue"))
        precise = report(facts={"dup": fact("ifrs-full:Revenue", 44012e6, FY, decimals=0)})
        self.assertEqual(eu.annual_from_report(precise, LEI, FILING, TODAY)["revenue"], 44012e6)
        partial = eu.annual_from_report(report(drop=("c1", "x1")), LEI, FILING, TODAY)
        self.assertIsNone(partial["operating_cashflow_margin"])
        self.assertIsNone(partial["free_cashflow"])
        self.assertFalse(partial["quality_ok"])
        fallback = eu.annual_from_report(report(drop=("n1",)), LEI, FILING, TODAY)
        self.assertEqual(fallback["net_income"], 6800e6, "total profit only if the parent share is untagged")

    def test_unusable_reports_are_rejected(self):
        self.assertIsNone(eu.annual_from_report(report(), LEI, {**FILING, "period_end": date(2024, 3, 31)}, TODAY))
        two = report(facts={"usd": fact("ifrs-full:Assets", 1e9, END, unit="iso4217:USD")})
        self.assertIsNone(eu.annual_from_report(two, LEI, FILING, TODAY), "mixed reporting currencies")
        self.assertIsNone(eu.annual_from_report(report(), "5493001KJTIIGC8Y1R12", FILING, TODAY), "facts of another LEI only")
        no_ifrs = report()
        no_ifrs["documentInfo"]["namespaces"]["ifrs-full"] = "http://example.com/other"
        self.assertIsNone(eu.annual_from_report(no_ifrs, LEI, FILING, TODAY))


class Lookups(unittest.TestCase):
    def test_isin_to_unique_lei(self):
        self.assertEqual(eu.lei_for_isin("FR0000120578", lambda *a, **k: gleif(LEI)), LEI)
        self.assertIsNone(eu.lei_for_isin("FR0000120578", lambda *a, **k: gleif()))
        self.assertIsNone(eu.lei_for_isin("FR0000120578", lambda *a, **k: gleif(LEI, "529900T8BM49AURSDO55")))
        self.assertEqual(eu.eea_isin("fr0000120578"), "FR0000120578")
        for bad in ("US0378331005", "CH0012032048", "FR000012057", None):
            self.assertIsNone(eu.eea_isin(bad))

    def test_latest_usable_filing(self):
        rows = (filing_row("2024-12-31", url="/old.json"), filing_row("2025-12-31", errors=3, url="/err.json"),
                filing_row("2025-12-31", errors=0, url="/new.json"), filing_row("2026-12-31", url="/future.json"),
                {**filing_row("2025-12-31"), "json_url": None})
        chosen = eu.latest_filing(LEI, lambda url, **k: filings(*rows), TODAY)
        self.assertEqual(chosen["json_url"], "/new.json")
        self.assertEqual(chosen["period_end"], date(2025, 12, 31))
        self.assertEqual(chosen["added"], date(2026, 3, 1))
        self.assertIsNone(eu.latest_filing(LEI, lambda url, **k: filings(), TODAY))


class Enrichment(unittest.TestCase):
    def fetcher(self, calls):
        def fetch(url, **kw):
            calls.append(url)
            if url.startswith(eu.GLEIF):
                return gleif(LEI)
            if "/api/entities/" in url:
                return filings(filing_row("2025-12-31", url="/r.json"))
            return report()
        return fetch

    def stock(self, ticker="SAN.PA", isin="FR0000120578", **extra):
        return {"ticker": ticker, "reference_isin": isin, "eligible_liquid_ranking": True,
                "avg_turnover_20d_eur": 1e8, **extra}

    def test_loads_eea_reports_only_and_records_attempts(self):
        calls = []
        stocks = [self.stock(), self.stock("AAPL", "US0378331005"), self.stock("NESN.SW", "CH0038863350")]
        status = eu.enrich_eu_fundamentals(stocks, {}, self.fetcher(calls), today=TODAY)
        self.assertEqual(status["reports_loaded"], 1)
        self.assertEqual(stocks[0]["fundamentals"]["revenue"], 44000e6)
        self.assertEqual(stocks[0]["lei"], LEI)
        self.assertEqual(stocks[0]["eu_fundamentals_checked_at"], "2026-11-04")
        self.assertNotIn("fundamentals", stocks[1])
        self.assertNotIn("fundamentals", stocks[2])
        self.assertEqual(len(calls), 3)

    def test_cache_refresh_retry_and_budget(self):
        fresh = eu.annual_from_report(report(), LEI, FILING, TODAY)
        fresh["checked_at"] = "2026-10-30"
        prior = {"stocks": [{"ticker": "SAN.PA", "lei": LEI, "fundamentals": fresh, "eu_fundamentals_checked_at": "2026-10-30"},
                            {"ticker": "AIR.PA", "eu_fundamentals_checked_at": "2026-11-03"}]}
        calls = []
        stocks = [self.stock(), self.stock("AIR.PA", "NL0000235190"), self.stock("MC.PA", "FR0000121014")]
        status = eu.enrich_eu_fundamentals(stocks, prior, self.fetcher(calls), today=TODAY, maximum=5)
        self.assertEqual(stocks[0]["fundamentals"]["checked_at"], "2026-10-30", "fresh cache reused")
        self.assertEqual(status["checked_this_run"], 1, "recent failed attempt waits; only MC.PA is due")
        self.assertIn("fundamentals", stocks[2])
        calls.clear()
        eu.enrich_eu_fundamentals([self.stock("MC.PA", "FR0000121014")], {}, self.fetcher(calls), maximum=0, today=TODAY)
        self.assertEqual(calls, [])
        old = dict(fresh, checked_at="2026-08-01")
        kept = [self.stock()]
        eu.enrich_eu_fundamentals(kept, {"stocks": [{"ticker": "SAN.PA", "fundamentals": old}]}, self.fetcher([]), maximum=0, today=TODAY)
        self.assertNotIn("fundamentals", kept, "older than KEEP_DAYS is dropped")

    def test_errors_are_counted_not_raised(self):
        def broken(url, **kw):
            raise RuntimeError("HTTP 503")
        stocks = [self.stock()]
        status = eu.enrich_eu_fundamentals(stocks, {}, broken, today=TODAY)
        self.assertEqual(status["errors"], 1)
        self.assertNotIn("fundamentals", stocks[0])
        self.assertEqual(stocks[0]["eu_fundamentals_checked_at"], "2026-11-04")


class Integration(unittest.TestCase):
    def test_sec_step_keeps_esef_data_and_scores_it(self):
        fund = eu.annual_from_report(report(), LEI, FILING, TODAY)
        fund["checked_at"] = TODAY.isoformat()
        stock = {"ticker": "SAN.PA", "source": "Yahoo Finance", "drawdown_252d": -.3, "fundamentals": fund}
        older = dict(fund, revenue=1.0, checked_at=TODAY.isoformat())
        sf.enrich_stocks([stock], {"stocks": [{"ticker": "SAN.PA", "fundamentals": older}]}, maximum=0)
        self.assertEqual(stock["fundamentals"]["revenue"], 44000e6, "not replaced by the previous snapshot")
        self.assertIsNotNone(stock["sander_score"])

    def test_ratio_factors_accept_reporting_currency(self):
        fund = eu.annual_from_report(report(facts={"gp": fact("ifrs-full:GrossProfit", 30000e6, FY)}), LEI, FILING, TODAY)
        stock = {"ticker": "SAN.PA", "price_date": "2026-11-03", "currency": "EUR", "fundamentals": fund}
        result = fr.factors_for_stock(stock, TODAY)
        self.assertAlmostEqual(result["quality"]["value"], 30000 / 130000)
        self.assertAlmostEqual(result["investment"]["metrics"]["asset_growth"], 130 / 125 - 1)
        self.assertIsNone(result["value"]["value"], "no dated valuation source outside the US")


if __name__ == "__main__":
    unittest.main()
