"""Offline invariants for no-lookahead signal and exchange-order simulation."""
import importlib.util
import math
import unittest
from datetime import date, timedelta
from pathlib import Path

spec=importlib.util.spec_from_file_location("btl_backtest",Path(__file__).parent/"backtest_5y.py")
b=importlib.util.module_from_spec(spec);spec.loader.exec_module(b)

class BacktestInvariants(unittest.TestCase):
    def setUp(self):
        self.days=[(date(2022,1,3)+timedelta(days=i)).isoformat() for i in range(110)]
        bars=[[100+i*.1,101+i*.1,99+i*.1,100+i*.1,100000,100+i*.1] for i in range(len(self.days))]
        self.h={"dates":self.days,"bars":bars,"index":{d:i for i,d in enumerate(self.days)}}
        self.fx=lambda day: 0.9

    def test_signal_never_reads_future_bars(self):
        at=self.days[80]
        before=b.signals_on("ABC",self.h["bars"],self.h["index"],at)
        self.assertIsNotNone(before)
        for future in self.h["bars"][81:]:
            future[3]=9999
            future[1]=9999
            future[2]=9990
        after=b.signals_on("ABC",self.h["bars"],self.h["index"],at)
        self.assertEqual(before,after)

    def test_first_possible_fill_is_next_day_not_decision_close(self):
        days=self.days[:22]
        bars=[[100,101,99,100,100000,100] for _ in days]
        bars[0][2]=1     # decision date absurd low; must NOT be used
        bars[1]=[100,100,99,100,100000,100] # low too high to buy at limit 98
        bars[2]=[100,100,97,98,100000,98]  # crosses buy limit 98
        hist={"bars":bars,"index":{d:i for i,d in enumerate(days)}}
        signal=(60,"T",100.,2.,.1,10000000.)
        executed=b.trade(signal,0,days,hist,self.fx,1000)
        self.assertIsNotNone(executed)
        self.assertEqual(executed["buy_date"],days[2])
        self.assertEqual(executed["limit_price_usd"],98)
        self.assertEqual(executed["stop_price_usd"],93)
        self.assertEqual(executed["buy_fee"],1)
        self.assertEqual(executed["sell_fee"],1)

    def test_stop_gap_executes_at_worse_open(self):
        days=self.days[:22]
        bars=[[100,101,99,100,100000,100] for _ in days]
        bars[1]=[99,100,97,99,100000,99]
        bars[2]=[87,93,86,89,100000,89] # gap under $93 stop
        hist={"bars":bars,"index":{d:i for i,d in enumerate(days)}}
        signal=(60,"T",100.,2.,.1,10000000.)
        executed=b.trade(signal,0,days,hist,self.fx,1000)
        self.assertEqual(executed["exit_reason"],"stop_gap")
        self.assertLess(executed["sell_eur"],87*.9)

    def test_entry_gap_below_stop_cannot_lock_in_impossible_profit(self):
        days=self.days[:22]
        bars=[[100,101,99,100,100000,100] for _ in days]
        # Previous close=100, ATR=2, buy limit=98, stop=93;
        # next open gaps to 85 USD, so buy and stop should never
        # yield a sale above the 85 USD executed entry.
        bars[1]=[85,87,80,82,100000,82]
        hist={"bars":bars,"index":{d:i for i,d in enumerate(days)}}
        signal=(60,"T",100.,2.,.1,10000000.)
        tr=b.trade(signal,0,days,hist,self.fx,1000,slip=0)
        self.assertEqual(tr["buy_date"],days[1])
        self.assertEqual(tr["exit_date"],days[1])
        self.assertLessEqual(tr["sell_eur"],tr["buy_eur"])
        self.assertLessEqual(tr["pnl_eur"],-2)

    def test_fees_always_both_sides(self):
        days=self.days[:22]
        bars=[[100,101,99,100,100000,100] for _ in days]
        bars[1]=[99,100,97,99,100000,99]
        hist={"bars":bars,"index":{d:i for i,d in enumerate(days)}}
        signal=(60,"T",100.,2.,.1,10000000.)
        tr=b.trade(signal,0,days,hist,self.fx,1000,slip=0)
        qty=tr["shares"]
        expected=qty*tr["sell_eur"]-1-(qty*tr["buy_eur"]+1)
        self.assertAlmostEqual(tr["pnl_eur"],expected)
        self.assertEqual(tr["exit_reason"],"time_exit")

if __name__=="__main__":unittest.main()
