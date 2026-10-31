"""Exact checks for transparent crash/exit reviews, split adjustment, stale-data fail closed."""
import math
import sys
import unittest
from datetime import datetime,timedelta,timezone
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
import trade_guidance as g
from build_snapshot import momentum_12_2

TODAY=datetime.now(timezone.utc).date()
DATE=TODAY.isoformat()

def bars_from_adjusted(adjusted,raw_factor=None):
    raw_factor=raw_factor or (lambda i:1)
    dates=[(TODAY-timedelta(days=len(adjusted)-i-1)).isoformat() for i in range(len(adjusted))]
    rows=[]
    for i,a in enumerate(adjusted):
        factor=raw_factor(i)
        p=a*factor
        rows.append((dates[i],p*1.012,p*.988,p,1_000_000,float(a)))
    return rows

def row(ctx,**extra):
    return {"ticker":"TEST","momentum_12_2":.35,
            "reference_close_eur":100.,"eur_per_unit":1.,
            "price_date":DATE,**ctx,**extra}

class GuidanceTest(unittest.TestCase):
    def test_positive_trend_and_positive_momentum_entry_review(self):
        x=[100+i*.5 for i in range(300)]
        ctx=g.price_context(bars_from_adjusted(x))
        self.assertGreater(ctx["sma200_ratio"],0)
        self.assertFalse(ctx["crash_warning"])
        r=row(ctx)
        g.assign_decision(r,{"risk":"normal"})
        self.assertEqual(r["entry_review"],"entry_review")
        self.assertEqual(r["exit_review"],"hold_review")
        self.assertLess(r["risk_reference_eur"],100+.5*299)

    def test_200d_bearish_trend_requires_exit_review(self):
        a=[100+i*.10 for i in range(280)]+[82.]*20
        ctx=g.price_context(bars_from_adjusted(a))
        r=row(ctx)
        g.assign_decision(r,{"risk":"normal"})
        self.assertEqual(r["entry_review"],"avoid_crash") # crash overrides trend
        self.assertEqual(r["exit_review"],"review_exit_crash")

    def test_slow_downtrend_exit_review_without_crash(self):
        a=[100.] * 260 + [100-i*.17 for i in range(40)]
        ctx=g.price_context(bars_from_adjusted(a))
        self.assertLess(ctx["sma200_ratio"],0)
        self.assertFalse(ctx["crash_warning"])
        r=row(ctx)
        g.assign_decision(r,{"risk":"normal"})
        self.assertEqual(r["entry_review"],"wait_downtrend")
        self.assertEqual(r["exit_review"],"review_exit_trend")

    def test_crash_21day_threshold(self):
        a=[100.]*278+[100-0.8*i for i in range(22)]
        ctx=g.price_context(bars_from_adjusted(a))
        self.assertLessEqual(ctx["return_21d"],-.15)
        self.assertTrue(ctx["crash_warning"])

    def test_252day_peak_drawdown_detects_drawdown(self):
        a=[100.]*279 + [98-1.3*i for i in range(21)]
        ctx=g.price_context(bars_from_adjusted(a))
        self.assertLessEqual(ctx["drawdown_252d"],-.25)
        self.assertTrue(ctx["crash_warning"])

    def test_split_causes_no_false_crash_or_atr(self):
        raw=lambda i:10 if i<280 else 1
        ctx=g.price_context(bars_from_adjusted([50.]*300,raw))
        self.assertAlmostEqual(ctx["drawdown_252d"],0.)
        self.assertAlmostEqual(ctx["return_21d"],0.)
        self.assertFalse(ctx["crash_warning"])
        self.assertLess(ctx["atr14_native"],2)

    def test_missing_critical_fields_fail_closed(self):
        r=row({"sma200_ratio":.2})
        g.assign_decision(r,{"risk":"normal"})
        self.assertEqual(r["entry_review"],"insufficient_data")
        self.assertEqual(r["exit_review"],"insufficient_data")
        self.assertIsNone(g.market_risk_from_quote(None)["risk"])

    def test_old_style_buy_limit_and_stop_are_distinct_eur_values(self):
        adjusted=[100+i*.5 for i in range(300)]
        context=g.price_context(bars_from_adjusted(adjusted))
        close=adjusted[-1]
        r=row(context,close=close,eur_per_unit=.82,
              reference_close_eur=close*.82)
        g.assign_decision(r,{"risk":"normal"})
        buy=(close-context["atr14_native"])*.82
        stop=(close-3.5*context["atr14_native"])*.82
        self.assertAlmostEqual(r["model_buy_limit_eur"],buy,places=4)
        self.assertAlmostEqual(r["model_initial_stop_eur"],stop,places=4)
        self.assertLess(r["model_initial_stop_eur"],r["model_buy_limit_eur"])
        self.assertLess(r["model_buy_limit_eur"],r["reference_close_eur"])
        self.assertEqual(r["entry_review"],"entry_review")

    def test_no_model_prices_for_stale_quotes(self):
        adjusted=[100+i*.5 for i in range(300)]
        context=g.price_context(bars_from_adjusted(adjusted))
        r=row(context,close=adjusted[-1],price_date=(TODAY-timedelta(days=8)).isoformat())
        g.assign_decision(r,{"risk":"normal"})
        self.assertEqual(r["entry_review"],"stale_quote")
        self.assertNotIn("model_buy_limit_eur",r)
        self.assertNotIn("model_initial_stop_eur",r)

    def test_no_model_prices_without_adjusted_ohlc(self):
        adjusted=[100+i*.5 for i in range(300)]
        context=g.price_context(bars_from_adjusted(adjusted))
        r=row(context,close=adjusted[-1],context_basis="unverified OHLC")
        g.assign_decision(r,{"risk":"normal"})
        self.assertNotIn("model_buy_limit_eur",r)
        self.assertNotIn("model_initial_stop_eur",r)

    def test_unknown_market_does_not_claim_buy(self):
        a=[100+i*.5 for i in range(300)]
        r=row(g.price_context(bars_from_adjusted(a)))
        g.assign_decision(r,{"risk":None})
        self.assertEqual(r["entry_review"],"market_unverified")
        r2=row(g.price_context(bars_from_adjusted(a)))
        g.assign_decision(r2,{"risk":"downtrend"})
        self.assertEqual(r2["entry_review"],"wait_market")

    def test_stale_market_and_stale_stock_require_review(self):
        a=[100+i*.5 for i in range(300)]
        ctx=g.price_context(bars_from_adjusted(a))
        market={"price_date":(TODAY-timedelta(days=8)).isoformat(),**ctx}
        self.assertIsNone(g.market_risk_from_quote(market)["risk"])
        r=row(ctx,price_date=(TODAY-timedelta(days=8)).isoformat())
        g.assign_decision(r,{"risk":"normal"})
        self.assertEqual(r["entry_review"],"stale_quote")
        self.assertEqual(r["exit_review"],"insufficient_data")

    def test_market_context_normal_crash_or_downtrend(self):
        a=[100+i*.5 for i in range(300)]
        risk=g.market_risk_from_quote({"price_date":DATE,**g.price_context(bars_from_adjusted(a))})
        self.assertEqual(risk["risk"],"normal")
        b=[100.]*279+[100-i*1.2 for i in range(21)]
        risk=g.market_risk_from_quote({"price_date":DATE,**g.price_context(bars_from_adjusted(b))})
        self.assertEqual(risk["risk"],"crash")

    def test_no_future_close_leakage_in_daily_indicators(self):
        base=[100+i*.13 for i in range(300)]
        first=g.price_context(bars_from_adjusted(base))
        extended=base+[400]
        last=g.price_context(bars_from_adjusted(extended[:-1]))
        for key in ("sma200_ratio","return_21d","drawdown_252d","atr14_native"):
            self.assertEqual(first[key],last[key])

if __name__=="__main__":unittest.main()
