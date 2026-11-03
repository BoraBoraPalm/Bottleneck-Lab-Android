"""Meaningful factor/data regressions, not claims of investment profitability."""
import calendar
import math
import sys
import unittest
from datetime import date, timedelta
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/"scripts"))
import factor_research as f
import sander_fundamentals as s
from test_sander_fundamentals import company,annual

ASOF=date(2026,11,1)


def earnings_rows():
    result=[]
    eps=[1,1,1,1]
    for change in [0,.1,.2,0,.1,.2,0,.2,.3]:
        eps.append(eps[len(eps)-4]+change)
    for i,value in enumerate(eps):
        month=6+3*i
        year,month=2023+month//12,month%12+1
        end=date(year,month+2,calendar.monthrange(year,month+2)[1])
        result.append({"start":date(year,month,1).isoformat(),"end":end.isoformat(),
                       "filed":(end+timedelta(days=25)).isoformat(),"net_income":value,"tag":"NetIncomeLoss"})
    return result


def stock():
    return {"ticker":"TEST","name":"Example Manufacturing","source":"Yahoo Finance","currency":"USD",
            "close":100,"price_date":"2026-10-30","eligible_liquid_ranking":True,
            "split_history_checked":True,"split_history_start":"2020-01-01","split_events":[],
            "fundamentals":{"fy_end":"2025-12-31","filed":"2026-02-01","currency":"USD",
                "source":"SEC EDGAR","gross_profit":50,"assets":100,"prior_assets":95,
                "prior_assets_end":"2024-12-31","cashflow_to_assets":.2,
                "quarterly":{"earnings":{"source":"SEC net income","currency":"USD","rows":earnings_rows()}}},
            "valuation_data":{"source":"TGMCharts summary","currency":"USD","price_date":"2026-10-30",
                              "updated":"2026-10-31","close":100,"pb":2,"pe":20}}


class FactorDefinitionTests(unittest.TestCase):
    def test_quality_uses_gross_profit_to_assets_not_gross_margin(self):
        result=f.factors_for_stock(stock(),ASOF)
        self.assertEqual(result["quality"]["value"],.5)
        self.assertEqual(result["quality"]["state"],"green")
        self.assertAlmostEqual(result["investment"]["value"],-(100/95-1),places=7)
        self.assertEqual(result["value"]["value"],.5)

    def test_loss_making_quality_can_be_red_instead_of_missing(self):
        a=stock();a["fundamentals"]["gross_profit"]=-5
        result=f.factors_for_stock(a,ASOF)["quality"]
        self.assertEqual(result["state"],"red")
        self.assertLess(result["value"],0)

    def test_missing_or_future_annual_data_do_not_produce_scores(self):
        for key,value in (("assets",None),("filed","2027-01-01"),("fy_end","2024-01-01")):
            a=stock();a["fundamentals"][key]=value
            self.assertIsNone(f.factors_for_stock(a,ASOF)["quality"]["value"])

    def test_financial_issuers_need_another_profitability_definition(self):
        a=stock();a["stock_sector"]="Financial Services"
        self.assertIsNone(f.factors_for_stock(a,ASOF)["quality"]["value"])

    def test_investment_requires_matching_annual_balance_comparison(self):
        a=stock();a["fundamentals"]["prior_assets_end"]="2025-09-30"
        self.assertIsNone(f.factors_for_stock(a,ASOF)["investment"]["value"])

    def test_investment_colour_follows_rank_direction(self):
        order={"green":3,"yellow":2,"orange":1,"red":0}
        results=[]
        for assets in (40,80,95,104,110,125,140):
            a=stock();a["fundamentals"]["assets"]=assets
            results.append(f.factors_for_stock(a,ASOF)["investment"])
        ranked=sorted(results,key=lambda r:-r["value"])
        states=[order[r["state"]] for r in ranked]
        self.assertEqual(states,sorted(states,reverse=True))
        self.assertEqual(results[0]["state"],"green")
        self.assertIn("Starke Schrumpfung",results[0]["reason"])
        self.assertEqual(results[-1]["state"],"red")

    def test_value_rejects_quote_date_price_currency_or_future_update_mismatch(self):
        for key,value in (("price_date","2026-10-29"),("close",150),("currency","EUR"),
                          ("updated","2027-01-01"),("pb",None),("pb",-1)):
            a=stock();a["valuation_data"][key]=value
            self.assertIsNone(f.factors_for_stock(a,ASOF)["value"]["value"],key)

    def test_earnings_model_has_known_manual_result_and_excludes_current_shock_from_estimation(self):
        result=f.factors_for_stock(stock(),ASOF)["earnings"]
        self.assertEqual(result["status"],"ok")
        self.assertAlmostEqual(result["metrics"]["net_income_expected_model"],1.2)
        self.assertAlmostEqual(result["metrics"]["sigma"],math.sqrt(.06/7))
        self.assertAlmostEqual(result["value"],.2/math.sqrt(.06/7),places=7)
        a=stock();a["fundamentals"]["quarterly"]["earnings"]["rows"][-1]["net_income"]+=1
        changed=f.factors_for_stock(a,ASOF)["earnings"]
        self.assertEqual(changed["metrics"]["net_income_expected_model"],result["metrics"]["net_income_expected_model"])
        self.assertEqual(changed["metrics"]["sigma"],result["metrics"]["sigma"])

    def test_negative_earnings_deviation_is_red_with_full_evidence(self):
        a=stock();a["fundamentals"]["quarterly"]["earnings"]["rows"][-1]["net_income"]=0
        result=f.factors_for_stock(a,ASOF)["earnings"]
        self.assertEqual(result["status"],"ok");self.assertEqual(result["state"],"red")

    def test_earnings_model_missing_quarter_tag_change_and_future_filing_fail_closed(self):
        for mode in ("gap","tag","future"):
            a=stock();rows=a["fundamentals"]["quarterly"]["earnings"]["rows"]
            if mode=="gap":rows.pop(5)
            elif mode=="tag":rows[0]["tag"]="ProfitLoss"
            else:rows[-1]["filed"]="2026-10-31" # after the observed stock close
            self.assertIsNone(f.factors_for_stock(a,ASOF)["earnings"]["value"])

    def test_new_quarter_missing_income_does_not_resurrect_old_score(self):
        a=stock();a["fundamentals"]["quarterly"]["earnings"]["latest_report_end"]="2026-12-31"
        self.assertIsNone(f.factors_for_stock(a,ASOF)["earnings"]["value"])

    def test_amount_scale_and_share_split_do_not_change_net_income_signal(self):
        base=f.factors_for_stock(stock(),ASOF)["earnings"]["value"]
        a=stock();a["split_events"]=[{"date":"2024-06-01","ratio":10}]
        for row in a["fundamentals"]["quarterly"]["earnings"]["rows"]:
            row["net_income"]*=1e9
        self.assertAlmostEqual(f.factors_for_stock(a,ASOF)["earnings"]["value"],base)

    def test_zero_variance_does_not_report_infinite_surprise(self):
        a=stock()
        for row in a["fundamentals"]["quarterly"]["earnings"]["rows"]:row["net_income"]=1
        self.assertIsNone(f.factors_for_stock(a,ASOF)["earnings"]["value"])

    def test_zero_network_budget_still_recomputes_from_verified_cached_values(self):
        a=stock()
        with patch("builtins.print"):
            fetch=lambda *a,**k:self.fail("Network budget was zero")
            result=f.enrich_factors([a],{},fetch,maximum=0,asof=ASOF)
        self.assertEqual(result["available"],dict.fromkeys(("quality","value","earnings","investment"),1))


class FactorSourceTests(unittest.TestCase):
    def test_sec_income_annual_or_ytd_is_never_treated_as_quarter(self):
        rows=[{"start":"2025-01-01","end":"2025-12-31","filed":"2026-02-01","form":"10-K","val":4},
              {"start":"2026-01-01","end":"2026-06-30","filed":"2026-07-25","form":"10-Q","val":2},
              {"start":"2026-07-01","end":"2026-09-30","filed":"2026-10-25","form":"10-Q","val":1}]
        facts={"facts":{"us-gaap":{"NetIncomeLoss":{"units":{"USD":rows}}}}}
        self.assertEqual(len(f.sec_earnings_history(facts,ASOF)["rows"]),1)

    def test_derived_income_requires_documented_two_source_differencing(self):
        row={"periodStart":"2026-07-01","periodEnd":"2026-09-30","filed":"2026-10-25","form":"10-Q","fiscalPeriod":"Q3",
             "metrics":{"netIncome":1},"provenance":{"netIncome":{"tag":"NetIncomeLoss","filed":"2026-10-25","form":"10-Q"}}}
        p={"symbol":"TEST","period":"quarterly","currency":"USD","rows":[row]}
        self.assertEqual(len(f.relay_earnings_history(p,"TEST",ASOF)["rows"]),1)
        provenance=row["provenance"]["netIncome"]
        provenance["derived"]="ytd-differencing"
        self.assertEqual(f.relay_earnings_history(p,"TEST",ASOF)["rows"],[])
        provenance["inputs"]=["10K-source","10Q-source"]
        history=f.relay_earnings_history(p,"TEST",ASOF)
        self.assertTrue(history["rows"][0]["derived"])
        for field,value in (("inputs",["only-one"]),("tag","EarningsPerShareDiluted"),("filed","2027-01-01"),("derived","unknown")):
            old=provenance.get(field);provenance[field]=value
            self.assertEqual(f.relay_earnings_history(p,"TEST",ASOF)["rows"],[],field)
            provenance[field]=old
        row["provenance"]={}
        self.assertEqual(f.relay_earnings_history(p,"TEST",ASOF)["rows"],[])

    def test_valuation_requires_matching_common_stock_classification_and_dates(self):
        p={"symbol":"TEST","currency":"USD","classification":{"type":"operating"},
           "asOf":{"dataUpdatedAt":"2026-10-31T12:00:00Z"},"price":{"lastClose":100,"lastCloseDate":"2026-10-30"},
           "valuation":{"pbRatio":2,"earningsYieldPercent":5}}
        v=f.parse_valuation(p,"TEST",ASOF)
        self.assertEqual(v["pb"],2);self.assertEqual(v["earnings_yield"],.05)
        for kind in ("fund","warrant",None):
            p["classification"]={"type":kind}
            self.assertIsNone(f.parse_valuation(p,"TEST",ASOF))

    def test_gross_profit_and_prior_assets_come_from_matching_year_ends(self):
        raw=company(lastyear=2025)
        gaap=raw["facts"]["us-gaap"]
        gaap["GrossProfit"]={"units":{"USD":[annual("gross",2025,50)]}}
        gaap["Assets"]={"units":{"USD":[{"end":"2025-09-30","filed":"2025-11-04","form":"10-K","val":100},
                {"end":"2024-09-30","filed":"2024-11-04","form":"10-K","val":80}]}}
        result=s.fundamental_quality(raw,ASOF)
        self.assertEqual(result["gross_profit_to_assets"],.5)
        self.assertEqual(result["asset_growth_yoy"],.25)
        self.assertEqual(result["prior_assets_end"],"2024-09-30")


class LongRiskTests(unittest.TestCase):
    def test_known_sample_volatility_and_adjusted_split_invariance(self):
        prices=[100]
        for i in range(252):prices.append(prices[-1]*math.exp(.01 if i%2 else -.01))
        bars=[("2026-01-01",p+1,p-1,p,1000,p) for p in prices]
        expected=math.sqrt((252*.0001)/251)*math.sqrt(252)
        self.assertAlmostEqual(f.long_risk_metrics(bars)["volatility_252d"],expected,places=7)
        split=[(d,h/2,l/2,p/2,v*2,a) for d,h,l,p,v,a in bars]
        self.assertEqual(f.long_risk_metrics(split),f.long_risk_metrics(bars))
        self.assertEqual(f.long_risk_metrics(bars[:252]),{})

    def test_missing_adjusted_prices_withhold_volatility(self):
        self.assertEqual(f.long_risk_metrics([("x",1,1,1,1,None)]*253),{})


if __name__=="__main__":unittest.main()
