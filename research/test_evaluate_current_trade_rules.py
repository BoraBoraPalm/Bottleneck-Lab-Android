"""Offline deterministic checks for frozen research-only model arithmetic and OHLC."""
import importlib.util,sys,unittest,datetime
from pathlib import Path
PATH=Path(__file__).resolve().parent/"evaluate_current_trade_rules.py"
spec=importlib.util.spec_from_file_location("eval_current_trade_rules",PATH)
r=importlib.util.module_from_spec(spec);spec.loader.exec_module(r)

def sample_data(c=100,signal_i=270,open_next=100,low_next=97,high_next=102,
                close_next=99,stop_next=None):
    start=datetime.date(2025,1,1)
    dates=[(start+datetime.timedelta(days=i)).isoformat() for i in range(315)]
    quote={}
    for j,d in enumerate(dates):
        price=c
        o=c;lo=c-1;hi=c+1
        if j==signal_i+1:
            o=open_next;lo=low_next;hi=high_next;price=close_next
        if stop_next is not None and j==signal_i+2:
            o=stop_next;lo=stop_next-1;hi=stop_next+1;price=stop_next
        quote[d]=[o,hi,lo,price,1000000,o,price,1]
    obj={"bars":quote,"currency":"USD"}
    return dates,obj

def pick(t="TEST",close=100,atr=2):
    return {"ticker":t,"close":close,"atr":atr,"currency":"USD",
        "mom":.35,"trend":.1,"crash":False,"correction":False,"region":"Nordamerika"}

class PortfolioResearchTest(unittest.TestCase):
    def test_signal_lags_252_and_42_not_one_month(self):
        dates,h=sample_data(c=100)
        for j in range(40,315):
            h["bars"][dates[j]][3]=100+j*.4
            h["bars"][dates[j]][6]=100+j*.4
            h["bars"][dates[j]][0]=100+j*.4
            h["bars"][dates[j]][7]=1
        h=r.prepare(h)
        i=270
        x=r.features("TEST",h,dates[i],lambda c,d:1)
        expected=(100+(i-42)*.4)/(100+(i-252)*.4)-1
        self.assertAlmostEqual(x["mom"],expected,places=8)

    def test_buy_limit_does_not_fill_when_price_never_drops(self):
        days,h=sample_data(open_next=103,low_next=101,high_next=104,close_next=102)
        for j in range(272,276):
            h["bars"][days[j]]=[104,105,101,104,1000000,104,104,1]
        obj=r.trade(pick(),"momentum_limit",270,days,h,lambda c,d:1,1000)
        self.assertIsNone(obj)

    def test_limit_fill_first_trading_day_and_stop_gap(self):
        days,h=sample_data(open_next=99,low_next=97,close_next=98.5,stop_next=92)
        obj=r.trade(pick(),"momentum_limit_stop",270,days,h,lambda c,d:1,1000)
        self.assertEqual(obj["buy_day"],days[271])
        self.assertEqual(obj["exit_day"],days[272])
        self.assertEqual(obj["exit_reason"],"stop_gap")
        self.assertLess(obj["pnl"],0)
        self.assertEqual(obj["risk_rule_stop_adj"],93.)

    def test_stop_at_entry_conservative_worst_case(self):
        days,h=sample_data(open_next=95,low_next=92,high_next=100,close_next=94)
        obj=r.trade(pick(),"momentum_limit_stop",270,days,h,lambda c,d:1,1000)
        self.assertEqual(obj["exit_reason"],"stop_same_day")
        self.assertLess(obj["pnl"],0)
        self.assertLessEqual(obj["exit_price_adj"],obj["fill_price_adj"])

    def test_limit_without_stop_survives_same_selloff(self):
        days,h=sample_data(open_next=95,low_next=92,close_next=95)
        obj=r.trade(pick(),"momentum_limit",270,days,h,lambda c,d:1,1000)
        self.assertNotIn("stop",obj["exit_reason"])

    def test_currency_pence_is_not_pound(self):
        # Regression guard for 1 GBp = 0.01 GBP, not for GBP itself.
        from inspect import getsource
        s=getsource(r.fx_rates)
        self.assertIn('factor=.01 if unit=="GBp" or cur=="GBX" else 1.0',s)

    def test_region_cap_no_double_count(self):
        selected=[]
        for reg in ("Asien","Europa","Nordamerika"):
            for j in range(10):
                selected.append({"ticker":f"{reg[:2]}{j}","region":reg,"mom":1-j/50,
                    "trend":.2,"crash":False,"correction":False})
        picks=r.pick(selected,False,True)
        self.assertEqual(len(picks),10)
        self.assertTrue(all(sum(p["region"]==reg for p in picks)<=4 for reg in ("Asien","Europa","Nordamerika")))
        self.assertEqual(r.pick(selected,True,False),[])

    def test_paired_significance_for_zero_excess_and_nonoverlap(self):
        diff=[0.]*60
        self.assertEqual(r.newey_west(diff)["p"],1.)
        self.assertEqual(r.bootstrap(diff),[0.0,0.0])
        x=[{"block_return":.02}]*60
        y=[{"block_return":.01}]*60
        self.assertEqual(r.direct_pair(x,y,"dummy")["n"],60)

    def test_fixed_rules_are_locked_to_live_display(self):
        self.assertEqual(r.PENDING_DAYS,5)
        self.assertEqual(r.HOLD_DAYS,20)
        self.assertEqual(r.ENTRY_ATR,1)
        self.assertEqual(r.STOP_ATR,2.5)
        self.assertEqual(r.BENCH,"ACWI")
        self.assertEqual(r.MAX_PER_REGION,4)

if __name__=="__main__":unittest.main()
