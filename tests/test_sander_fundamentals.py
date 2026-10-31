"""No fabricated Sander-style quality candidates, no quarterly/YTD mixing."""
import sys,unittest
from datetime import date,timedelta
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
import sander_fundamentals as s

def annual(tag,year,val,unit="USD",form="10-K",fp="FY",filed=None,duration=364):
    end=date(year,9,30)
    start=end-timedelta(days=duration)
    return {"start":start.isoformat(),"end":end.isoformat(),
            "filed":(filed or end+timedelta(days=35)).isoformat(),
            "fp":fp,"form":form,"val":val}

def company(growth=.1,profit=18,cfo=22,lastyear=2025):
    rev=[annual("rev",lastyear-1,100),
         annual("rev",lastyear,100*(1+growth))]
    def block(series):return {"units":{"USD":series}}
    return {"cik":320193,"facts":{"us-gaap":{
        "RevenueFromContractWithCustomerExcludingAssessedTax":block(rev),
        "NetIncomeLoss":block([annual("profit",lastyear,profit)]),
        "NetCashProvidedByUsedInOperatingActivities":block([annual("cfo",lastyear,cfo)])}}}

def share(drop=-.3):
    return {"ticker":"AAPL","source":"Yahoo Finance",
            "drawdown_252d":drop,"eligible_global_ranking":True}

class SandScreenTest(unittest.TestCase):
    def test_annual_report_recognizes_filed_profits_cash_and_growth(self):
        f=s.fundamental_quality(company(),asof=date(2026,10,31))
        self.assertTrue(f["quality_ok"])
        self.assertAlmostEqual(f["revenue_growth_yoy"],.10)
        self.assertAlmostEqual(f["profit_margin"],18/110)
        self.assertEqual(f["fy_end"],"2025-09-30")
        self.assertEqual(f["filed"],"2025-11-04")
        self.assertTrue(s.sander_screen(share(),f)>0)

    def test_negative_cfo_rejected(self):
        f=s.fundamental_quality(company(cfo=-1),asof=date(2026,10,31))
        self.assertFalse(f["quality_ok"])
        self.assertIsNone(s.sander_screen(share(),f))

    def test_negative_net_income_rejected(self):
        f=s.fundamental_quality(company(profit=-1),asof=date(2026,10,31))
        self.assertFalse(f["quality_ok"])
        self.assertIsNone(s.sander_screen(share(),f))

    def test_unverified_non_yahoo_and_no_price_dip_rejected(self):
        f=s.fundamental_quality(company(),asof=date(2026,10,31))
        self.assertIsNone(s.sander_screen(share(drop=-.03),f))
        self.assertIsNone(s.sander_screen(share(drop=-.7),f))
        self.assertIsNone(s.sander_screen({**share(),"source":"Stooq"},f))
        self.assertIsNone(s.sander_screen({**share(),"drawdown_252d":None},f))
        self.assertIsNone(s.sander_screen(share(),None))

    def test_no_quarterly_or_ytd_fake_annual(self):
        f=company()
        v=f["facts"]["us-gaap"]["NetCashProvidedByUsedInOperatingActivities"]["units"]["USD"]
        v[0]["fp"]="Q3"
        self.assertIsNone(s.fundamental_quality(f,asof=date(2026,10,31)))

    def test_no_future_filing(self):
        f=company()
        f["facts"]["us-gaap"]["NetIncomeLoss"]["units"]["USD"][0]["filed"]="2027-01-01"
        self.assertIsNone(s.fundamental_quality(f,asof=date(2026,10,31)))

    def test_missing_prior_revenue_rejected(self):
        f=company()
        f["facts"]["us-gaap"]["RevenueFromContractWithCustomerExcludingAssessedTax"]["units"]["USD"]=\
          [f["facts"]["us-gaap"]["RevenueFromContractWithCustomerExcludingAssessedTax"]["units"]["USD"][-1]]
        self.assertIsNone(s.fundamental_quality(f,asof=date(2026,10,31)))

    def test_not_unnecessarily_optimistic_on_weak_growth(self):
        f=s.fundamental_quality(company(growth=-.2),asof=date(2026,10,31))
        self.assertFalse(f["quality_ok"])
        self.assertIsNone(s.sander_screen(share(),f))

    def test_synthetic_verified_qualified_candidate_in_stock_screener(self):
        verified=s.fundamental_quality(company(),asof=date(2026,10,31))
        old={"stocks":[]}
        stocks=[share(),{**share(drop=-.22),"ticker":"NOSEC","source":"Yahoo Finance"}]
        with patch.object(s,"ticker_map",return_value={"AAPL":320193}),\
             patch.object(s,"download_fundamental",return_value=verified):
            result=s.enrich_stocks(stocks,old,maximum=5)
        self.assertGreater(stocks[0]["sander_score"],0)
        self.assertIsNone(stocks[1]["sander_score"])
        self.assertEqual(result["qualified_candidates"],1)
        self.assertEqual(result["with_verified_fundamentals"],1)

    def test_broken_provider_does_not_leak_fake_candidates(self):
        stocks=[share()]
        with patch.object(s,"ticker_map",side_effect=RuntimeError("blocked")):
            result=s.enrich_stocks(stocks,{"stocks":[]},maximum=3)
        self.assertEqual(result["qualified_candidates"],0)
        self.assertIsNone(stocks[0]["sander_score"])
        self.assertEqual(result["status"],"partial")

if __name__=="__main__":unittest.main()
