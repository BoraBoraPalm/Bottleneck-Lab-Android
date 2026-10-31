"""Offline tests for SEC as-of filters, annual alignment and QVM coverage."""
import sys
import unittest
from pathlib import Path
from datetime import date
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
import multifactor as m

def fact(name,value,unit="USD",start="2024-01-01",end="2024-12-31",filed="2025-02-20",form="10-K"):
    r={"val":value,"end":end,"filed":filed,"form":form}
    if start is not None:r["start"]=start
    return (name,{ "units":{unit:[r]} })

def fake_filing():
    tags=dict([
       fact("Revenues",2000000000),
       fact("GrossProfit",800000000),
       fact("NetCashProvidedByUsedInOperatingActivities",240000000),
       fact("NetIncomeLoss",120000000),
       fact("Assets",1300000000,start=None),
       fact("StockholdersEquity",700000000,start=None),
       fact("LongTermDebt",300000000,start=None),
       fact("WeightedAverageNumberOfDilutedSharesOutstanding",100000000,unit="shares")
    ])
    return {"cik":1234,"facts":{"us-gaap":tags}}

class TestFundamentals(unittest.TestCase):
    def test_data_not_known_before_filing(self):
        f=fake_filing()
        self.assertIsNone(m.sec_fundamentals(f,date(2025,2,1)))
        got=m.sec_fundamentals(f,date(2025,2,25))
        self.assertIsNotNone(got)
        self.assertEqual(got["filed"],"2025-02-20")
        self.assertEqual(got["assets_usd"],1300000000)

    def test_future_restatement_cannot_leak(self):
        f=fake_filing()
        f["facts"]["us-gaap"]["Revenues"]["units"]["USD"].append({
            "val":9999999999,"start":"2024-01-01","end":"2024-12-31",
            "filed":"2026-02-20","form":"10-K/A"})
        pre=m.sec_fundamentals(f,date(2025,3,1))
        post=m.sec_fundamentals(f,date(2026,3,1))
        self.assertEqual(pre["annual_revenue_usd"],2000000000)
        self.assertEqual(post["annual_revenue_usd"],9999999999)

    def test_momentum_excludes_last_42_days(self):
        values=[100.0]*300
        initial=m.momentum_12_2(values)
        for i in range(1,43):values[-i]=2000
        self.assertEqual(m.momentum_12_2(values),initial)
        self.assertIsNone(m.momentum_12_2([100.]*252))

    def test_incomplete_company_does_not_receive_zero_or_top_score(self):
        stocks=[{"ticker":"A","close":50,"currency":"USD",
                 "momentum_12_2":.2,"eligible_for_ranking":True,
                 "fundamentals":{"assets_usd":1000,"fiscal_year_end":"2024-12-31",
                   "filed":"2025-02-20","diluted_shares":100,
                   "gross_profit_usd":400,"op_cashflow_usd":200,
                   "net_income_usd":100}},
                {"ticker":"B","close":20,"currency":"USD","momentum_12_2":.5,
                 "eligible_for_ranking":True}]
        status=m.assign_multifactor(stocks,as_of=date(2025,4,1),min_eligible=2)
        self.assertEqual(status["status"],"insufficient_data")
        self.assertNotIn("multifactor",stocks[0])
        self.assertNotIn("multifactor",stocks[1])

    def test_simple_two_stock_ranks_and_missing_facts(self):
        base={"close":10,"currency":"USD","eligible_for_ranking":True}
        f={"assets_usd":1000,"fiscal_year_end":"2024-12-31",
           "filed":"2025-02-20","diluted_shares":100,"gross_profit_usd":400,
           "op_cashflow_usd":200,"net_income_usd":100,
           "equity_usd":600}
        stocks=[{**base,"ticker":"A","momentum_12_2":.2,"fundamentals":dict(f)},
                {**base,"ticker":"B","momentum_12_2":.1,"fundamentals":{**f,"gross_profit_usd":200}},
                {"ticker":"C","close":10,"currency":"USD","eligible_for_ranking":True,
                 "momentum_12_2":.9}]
        status=m.assign_multifactor(stocks,as_of=date(2025,4,1),min_eligible=2)
        self.assertEqual(status["ranking_count"],2)
        self.assertIn("multifactor",stocks[0])
        self.assertNotIn("multifactor",stocks[2])
        self.assertGreater(stocks[0]["multifactor"]["score"],stocks[1]["multifactor"]["score"])

    def test_invalid_filing_and_stale_year_rejected(self):
        row={"ticker":"A","close":10,"currency":"USD",
             "momentum_12_2":.4,"eligible_for_ranking":True,
             "fundamentals":{"assets_usd":1000,"diluted_shares":100,
              "gross_profit_usd":400,"op_cashflow_usd":200,
              "fiscal_year_end":"2021-12-31","filed":"2022-02-20"}}
        self.assertIsNone(m.metrics_for_row(row,date(2025,5,1)))
if __name__=="__main__":
    unittest.main()
