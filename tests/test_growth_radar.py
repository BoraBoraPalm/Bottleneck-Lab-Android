"""Quarter, provenance, missing-data and strategy integration regressions."""
import sys
import unittest
from datetime import date, timedelta
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/"scripts"))
import growth_radar as g
import sander_fundamentals as s

ASOF = date(2026, 10, 31)


def quarters(rates=(.20, .25, .40)):
    rows = []
    for year in (2025, 2026):
        for i, (start, end) in enumerate((("01-01", "03-31"), ("04-01", "06-30"), ("07-01", "09-30"))):
            revenue = 100 if year == 2025 else 100*(1+rates[i])
            rows.append({"start": f"{year}-{start}", "end": f"{year}-{end}",
                         "filed": (date.fromisoformat(f"{year}-{end}")+timedelta(days=25)).isoformat(),
                         "revenue": revenue, "net_income": revenue*(.1 if year == 2025 else .15),
                         "revenue_tag": "Revenues", "derived": False})
    return {"currency": "USD", "source": "SEC EDGAR 10-Q XBRL", "rows": rows}


def stock():
    return {"ticker": "GROW", "name": "Example Manufacturing", "source": "Yahoo Finance",
            "price_date": "2026-10-30", "return_63d": .35, "return_126d": .55,
            "breakout_63d_ratio": .01, "turnover_ratio_20d": 1.8,
            "growth_price_basis": "Yahoo adjusted closes; native price x share volume; 127 sessions",
            "fundamentals": {"fy_end": "2025-12-31", "filed": "2026-02-15",
                             "operating_cashflow_margin": .2, "quarterly": quarters()}}


def market():
    return {"date": "2026-10-30", "return_63d": .1, "return_126d": .2,
            "growth_price_basis": "Yahoo adjusted closes; 127 sessions"}


class QuarterlyTests(unittest.TestCase):
    def test_three_consecutive_yoy_comparisons(self):
        q = g.comparable_quarters(quarters(), ASOF)
        self.assertEqual([x["revenue_growth_yoy"] for x in q], [.2, .25, .4])
        self.assertEqual(q[-1]["prior_end"], "2025-09-30")

    def test_sec_annual_and_ytd_are_not_quarters(self):
        payload = {"facts": {"us-gaap": {"Revenues": {"units": {"USD": [
            {"start": "2026-01-01", "end": "2026-06-30", "filed": "2026-07-25", "val": 200, "form": "10-Q"},
            {"start": "2025-01-01", "end": "2025-12-31", "filed": "2026-02-01", "val": 400, "form": "10-K"}]}}}}}
        self.assertEqual(g.sec_quarters(payload, ASOF)["rows"], [])

    def test_sec_uses_latest_known_filing_and_newest_revenue_tag(self):
        rows = [{"start": r["start"], "end": r["end"], "filed": r["filed"],
                 "val": r["revenue"], "form": "10-Q"} for r in quarters()["rows"]]
        future = {**rows[-1], "filed": "2027-01-01", "val": 9999}
        payload = {"facts": {"us-gaap": {
            "Revenues": {"units": {"USD": [rows[0]]}},
            "RevenueFromContractWithCustomerExcludingAssessedTax": {"units": {"USD": rows+[future]}}}}}
        q = g.sec_quarters(payload, ASOF)
        self.assertEqual(q["rows"][-1]["revenue"], 140)
        self.assertEqual(len(g.comparable_quarters(q, ASOF)), 3)

    def test_missing_middle_or_latest_yoy_pair_does_not_skip_to_older_data(self):
        for index in (2, 4):
            q = quarters()
            q["rows"].pop(index)
            self.assertEqual(g.comparable_quarters(q, ASOF), [])

    def test_tag_changes_and_zero_prior_revenue_do_not_create_acceleration(self):
        q = quarters()
        q["rows"][-1]["revenue_tag"] = "SalesRevenueServicesNet"
        self.assertEqual(g.comparable_quarters(q, ASOF), [])
        q = quarters()
        q["rows"][2]["revenue"] = 0
        self.assertEqual(g.comparable_quarters(q, ASOF), [])

    def test_relay_requires_dated_per_value_provenance_and_discloses_derivation(self):
        row = {"fiscalPeriod": "Q3", "form": "10-Q", "periodStart": "2026-07-01",
               "periodEnd": "2026-09-30", "filed": "2026-10-25", "metrics": {"revenue": 140, "netIncome": 21},
               "provenance": {"revenue": {"tag": "Revenues", "form": "10-Q", "filed": "2026-10-25",
                                          "derived": "ytd-differencing", "inputs": ["accn1", "accn2"]},
                              "netIncome": {"tag": "NetIncomeLoss", "form": "10-Q", "filed": "2026-10-25"}}}
        obj = {"symbol": "GROW", "currency": "USD", "period": "quarterly", "rows": [row]}
        self.assertTrue(g.relay_quarters(obj, "GROW", ASOF)["rows"][0]["derived"])
        row["provenance"]["revenue"]["filed"] = "2027-01-01"
        self.assertEqual(g.relay_quarters(obj, "GROW", ASOF)["rows"], [])
        row["provenance"] = {}
        self.assertEqual(g.relay_quarters(obj, "GROW", ASOF)["rows"], [])

    def test_wrong_currency_or_annual_relay_response_rejected(self):
        for obj in ({"symbol": "GROW", "currency": "EUR", "period": "quarterly"},
                    {"symbol": "GROW", "currency": "USD", "period": "annual"}):
            self.assertEqual(g.relay_quarters(obj, "GROW", ASOF)["rows"], [])


class GrowthScreenTests(unittest.TestCase):
    def screen(self, value):
        return g.growth_screen(value, market(), ASOF)

    def test_qualified_components_and_six_month_history_without_momentum(self):
        candidate = stock()
        result = self.screen(candidate)
        self.assertNotIn("momentum_12_2", candidate)
        self.assertEqual(result["status"], "qualified")
        self.assertAlmostEqual(result["revenue_acceleration"], .15)
        self.assertAlmostEqual(result["score"], .45*result["growth_score"]+.3*result["quality_score"]+.25*result["confirmation_score"], places=2)
        self.assertEqual(len(result["unchecked"]), 4)

    def test_growth_does_not_accelerate(self):
        candidate = stock()
        candidate["fundamentals"]["quarterly"] = quarters((.3, .4, .35))
        self.assertEqual(self.screen(candidate)["status"], "criteria_not_met")
        self.assertIsNone(self.screen(candidate)["score"])

    def test_two_percentage_point_acceleration_boundary_is_inclusive(self):
        candidate = stock()
        candidate["fundamentals"]["quarterly"] = quarters((.15, .2, .22))
        self.assertEqual(self.screen(candidate)["status"], "qualified")
        candidate["fundamentals"]["quarterly"] = quarters((.15, .2, .219))
        self.assertEqual(self.screen(candidate)["status"], "criteria_not_met")

    def test_missing_quality_is_not_filled_and_cash_burn_is_excluded(self):
        for value, status in ((None, "missing_quality"), (0, "criteria_not_met"), (-.2, "criteria_not_met")):
            candidate = stock()
            candidate["fundamentals"]["operating_cashflow_margin"] = value
            result = self.screen(candidate)
            self.assertEqual(result["status"], status)
            self.assertIsNone(result["score"])

    def test_shrinking_loss_can_qualify_without_misleading_earnings_percentage(self):
        candidate = stock()
        for q in candidate["fundamentals"]["quarterly"]["rows"]:
            q["net_income"] = q["revenue"]*(-.1 if q["end"].startswith("2025") else -.04)
        result = self.screen(candidate)
        self.assertEqual(result["status"], "qualified")
        self.assertAlmostEqual(result["net_margin_change_yoy"], .06)

    def test_no_future_filings_relative_to_last_stock_close(self):
        candidate = stock()
        candidate["fundamentals"]["quarterly"]["rows"][-1]["filed"] = "2026-10-31"
        self.assertIsNone(self.screen(candidate)["score"])

    def test_old_reports_old_prices_and_sector_specifics_do_not_qualify(self):
        candidate = stock()
        candidate["fundamentals"]["fy_end"] = "2024-12-31"
        self.assertEqual(self.screen(candidate)["status"], "stale_financials")
        candidate = stock()
        candidate["name"] = "Example Bank"
        self.assertEqual(self.screen(candidate)["status"], "sector_specific")
        candidate = stock()
        self.assertEqual(g.growth_screen(candidate, market(), date(2026, 11, 10))["status"], "missing_price")

    def test_market_date_source_or_missing_turnover_prevents_price_confirmation(self):
        for key, value in (("price_date", "2026-10-29"), ("turnover_ratio_20d", None), ("source", "Stooq")):
            candidate = stock()
            candidate[key] = value
            result = self.screen(candidate)
            self.assertEqual(result["status"], "missing_price")
            self.assertIsNone(result["confirmation_score"])
            self.assertIsNotNone(result["growth_score"])

    def test_relative_strength_uses_compound_ratio_and_can_reject_market_laggard(self):
        result = self.screen(stock())
        self.assertAlmostEqual(result["relative_63d"], 1.35/1.1-1, places=6)
        candidate = stock()
        candidate["return_63d"] = .05
        self.assertEqual(self.screen(candidate)["status"], "criteria_not_met")

    def test_enrichment_never_preserves_stale_success_from_previous_run(self):
        candidates = [stock(), {"ticker": "MISSING", "growth_score": 99}]
        result = g.enrich_growth(candidates, market(), ASOF)
        self.assertEqual(result["qualified_candidates"], 1)
        self.assertIsNone(candidates[1]["growth_score"])

    def test_successful_old_cache_is_upgraded_despite_recent_attempt_marker(self):
        candidate = stock()
        candidate["eligible_liquid_ranking"] = True
        old_fund = {**candidate["fundamentals"], "schema_version": 2, "checked_at": date.today().isoformat()}
        prior = {"stocks": [{"ticker": "GROW", "fundamentals": old_fund,
                             "fundamentals_checked_at": date.today().isoformat()}]}
        upgraded = {**old_fund, "schema_version": s.SCHEMA_VERSION}
        with patch.object(s, "ticker_map", return_value={"GROW": 123}), \
             patch.object(s, "download_fundamental", return_value=upgraded) as fetch:
            s.enrich_stocks([candidate], prior, maximum=1)
        fetch.assert_called_once()


class PriceTests(unittest.TestCase):
    def bars(self, split=False):
        result = []
        for i in range(127):
            adjusted = 100+i
            factor = 2 if split and i >= 117 else 1
            raw = adjusted/factor
            result.append(((ASOF-timedelta(days=126-i)).isoformat(), raw+1, raw-1,
                           raw, 1000000*factor, adjusted))
        return result

    def test_six_month_returns_and_turnover_do_not_change_on_split(self):
        ordinary, split = g.price_metrics(self.bars()), g.price_metrics(self.bars(True))
        self.assertEqual(ordinary, split)
        self.assertAlmostEqual(ordinary["return_126d"], 1.26)
        self.assertEqual(g.price_metrics(self.bars()[:126]), {})

    def test_missing_volume_stays_missing(self):
        bars = self.bars()
        bars[-1] = (*bars[-1][:4], 0, bars[-1][5])
        self.assertIsNone(g.price_metrics(bars)["turnover_ratio_20d"])


if __name__ == "__main__":
    unittest.main()
