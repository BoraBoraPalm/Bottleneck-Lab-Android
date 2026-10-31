"""Display real partial financials without weakening the Sander eligibility gate."""
import sys
import unittest
from datetime import date, timedelta
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
import sander_fundamentals as s
from test_sander_fundamentals import annual,company,share


class FundamentalDisplayTests(unittest.TestCase):
    def test_pre_revenue_company_still_displays_filed_losses(self):
        facts=company(profit=-20,cfo=-15)
        for row in facts["facts"]["us-gaap"]["RevenueFromContractWithCustomerExcludingAssessedTax"]["units"]["USD"]:
            row["val"]=0
        result=s.fundamental_quality(facts,asof=date(2026,10,31))
        self.assertEqual(result["revenue"],0)
        self.assertEqual(result["net_income"],-20)
        self.assertIsNone(result["profit_margin"])
        self.assertIsNone(result["revenue_growth_yoy"])
        self.assertFalse(result["quality_ok"])

    def test_matching_annual_cashflow_and_balance_ratios(self):
        facts=company()
        gaap=facts["facts"]["us-gaap"]
        gaap["NetIncomeLoss"]["units"]["USD"].append(annual("net",2024,12))
        gaap["PaymentsToAcquirePropertyPlantAndEquipment"]={"units":{"USD":[annual("capex",2025,5)]}}
        for tag,value in {"Assets":100,"StockholdersEquity":40,"Liabilities":60,
                "AssetsCurrent":30,"LiabilitiesCurrent":15}.items():
            gaap[tag]={"units":{"USD":[{"end":"2025-09-30","filed":"2026-02-01",
                "form":"10-Q","fp":"Q1","val":value}]}}
        result=s.fundamental_quality(facts,asof=date(2026,10,31))
        self.assertEqual(result["free_cashflow"],17)
        self.assertEqual(result["net_income_growth_yoy"],.5)
        self.assertEqual(result["equity_ratio"],.4)
        self.assertEqual(result["current_ratio"],2)
        self.assertEqual(result["liabilities_to_equity"],1.5)
        self.assertEqual(result["balance_filed"],"2026-02-01")

    def test_other_quarter_balance_cannot_be_mixed_with_annual_income(self):
        facts=company()
        facts["facts"]["us-gaap"]["Assets"]={"units":{"USD":[
            {"end":"2026-03-31","filed":"2026-05-01","form":"10-Q","val":100}]}}
        result=s.fundamental_quality(facts,asof=date(2026,10,31))
        self.assertIsNone(result["equity_ratio"])
        self.assertNotIn("assets",result)

    def test_missing_capex_never_implies_cashflow_equals_free_cashflow(self):
        result=s.fundamental_quality(company(),asof=date(2026,10,31))
        self.assertIsNone(result["free_cashflow"])
        self.assertIsNone(result["free_cashflow_margin"])
        self.assertGreater(result["operating_cashflow_margin"],0)

    def test_turnaround_does_not_report_misleading_percentage_growth(self):
        facts=company()
        facts["facts"]["us-gaap"]["NetIncomeLoss"]["units"]["USD"].append(annual("net",2024,-12))
        result=s.fundamental_quality(facts,asof=date(2026,10,31))
        self.assertIsNone(result["net_income_growth_yoy"])
        self.assertEqual(result["earnings_comparison"],"turnaround")

    def test_future_restatement_does_not_replace_known_past_filing(self):
        facts=company()
        facts["facts"]["us-gaap"]["NetIncomeLoss"]["units"]["USD"].append(
            annual("net",2025,999,filed=date(2027,1,1)))
        result=s.fundamental_quality(facts,asof=date(2026,10,31))
        self.assertEqual(result["net_income"],18)

    def test_zero_and_negative_equity_do_not_produce_good_debt_ratios(self):
        for equity in (0,-10):
            result=s._derived_metrics({"revenue":100,"net_income":10,"operating_cashflow":15,
                "equity":equity,"assets":100,"liabilities":100-equity,
                "current_assets":50,"current_liabilities":0})
            self.assertIsNone(result["liabilities_to_equity"])
            self.assertIsNone(result["current_ratio"])
            self.assertLessEqual(result["equity_ratio"],0)

    def test_ordinary_momentum_stock_gets_financials_without_a_price_dip(self):
        stock={**share(drop=-.02),"momentum_12_2":.4}
        verified=s.fundamental_quality(company(),asof=date(2026,10,31))
        with patch.object(s,"ticker_map",return_value={"AAPL":320193}), \
             patch.object(s,"download_fundamental",return_value=verified):
            result=s.enrich_stocks([stock],{},maximum=1)
        self.assertEqual(result["with_verified_fundamentals"],1)
        self.assertEqual(stock["fundamentals"]["net_income"],18)
        self.assertIsNone(stock["sander_score"])

    def test_failed_recent_lookup_does_not_starve_other_stocks(self):
        today=date.today().isoformat()
        stock=share()
        previous={"stocks":[{**stock,"fundamentals_checked_at":today}]}
        with patch.object(s,"ticker_map") as mapping,patch.object(s,"tgm_annual_quality") as fetch:
            result=s.enrich_stocks([stock],previous,maximum=1)
        self.assertEqual(result["checked_this_run"],0)
        mapping.assert_not_called()
        fetch.assert_not_called()

    def test_zero_request_budget_is_respected(self):
        with patch.object(s,"ticker_map") as mapping:
            result=s.enrich_stocks([share()],{},maximum=0)
        self.assertEqual(result["checked_this_run"],0)
        mapping.assert_not_called()

    def test_non_usd_provider_values_are_not_silently_labelled_usd(self):
        with patch.object(s,"get_json",return_value={"symbol":"AAPL","period":"annual",
                "currency":"JPY","rows":[{}]}):
            self.assertIsNone(s.tgm_annual_quality("AAPL"))

    def test_quarterly_duration_in_annual_endpoint_is_rejected(self):
        row={"periodStart":"2025-07-01","periodEnd":"2025-09-30",
            "filed":"2025-11-04","form":"10-K","fiscalPeriod":"FY",
            "metrics":{"revenue":100,"netIncome":20}}
        with patch.object(s,"get_json",return_value={"symbol":"AAPL","period":"annual",
                "currency":"USD","rows":[row]}):
            self.assertIsNone(s.tgm_annual_quality("AAPL"))


if __name__=="__main__":unittest.main()
