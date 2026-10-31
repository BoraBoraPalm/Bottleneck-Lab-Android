"""Regression tests for the simplified global momentum-only app."""
import io,sys,unittest,csv
from pathlib import Path
from datetime import datetime,timezone,timedelta
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
import build_snapshot as q
import market_pipeline as m

class SimpleMarketTest(unittest.TestCase):
    def test_momentum_requires_253_bars_and_excludes_recent_42(self):
        prices=[100.]*300
        before=q.momentum_12_2(prices)
        for i in range(1,43):prices[-i]=1000.
        self.assertEqual(before,q.momentum_12_2(prices))
        self.assertIsNone(q.momentum_12_2([100.]*252))
        prices[-43]=115
        self.assertAlmostEqual(q.momentum_12_2(prices),.15,places=5)

    def test_adjusted_momentum_ignores_share_split(self):
        today=datetime.now(timezone.utc).date()
        bars=[]
        for i in range(320):
            raw=100. if i<300 else 10.  # 10:1 split would fake a -90% move
            adj=10.  # adjusted close has removed mechanical price changes
            day=(today-timedelta(days=320-i)).isoformat()
            bars.append((day,raw*1.01,raw*.99,raw,100000,adj))
        with patch.object(q,"fetch_yahoo",return_value=(bars,"USD","Yahoo Finance")):
            result,error=q.quote("SPLIT","Global")
        self.assertIsNone(error)
        self.assertAlmostEqual(result["momentum_12_2"],0,places=6)
        self.assertEqual(result["momentum_basis"],"Yahoo adjusted daily closes")

    def test_missing_adjustments_cannot_supply_momentum(self):
        current=datetime.now(timezone.utc)
        sample={"ticker":"AAA","close":100.,"currency":"USD",
                "avg_local_turnover_20d":50000000,"momentum_12_2":5.0,
                "price_date":current.date().isoformat(),"source":"Yahoo Finance",
                "last_checked_at":current.isoformat()}
        original=m.cached_quotes({"stocks":[sample]},{"AAA":{}})
        self.assertIsNone(original["AAA"]["momentum_12_2"])

    def test_no_incorrect_stooq_fallback_for_foreign_symbol(self):
        with self.assertRaises(RuntimeError):
            q.fetch_stooq("7203.T")
        with self.assertRaises(RuntimeError):
            q.fetch_stooq("ASML.AS")

    def test_quote_retains_real_currency_and_no_old_atr_score(self):
        today=datetime.now(timezone.utc).date()
        days=[((today-timedelta(days=320-i)).isoformat(),102,98,100,500000)
              for i in range(320)]
        with patch.object(q,"fetch_yahoo",return_value=(days,"JPY","fake Yahoo")):
            result,error=q.quote("7203.T","Global")
        self.assertIsNone(error)
        self.assertEqual(result["currency"],"JPY")
        self.assertIn("momentum_12_2",result)
        self.assertNotIn("score",result)
        self.assertNotIn("atr",result)

    def test_region_cap_uses_eligible_only(self):
        data=[]
        for region,count in (("Asien",16),("Europa",15),("Nordamerika",6)):
            for i in range(count):
                data.append({"ticker":f"{region[0]}{i:02d}","region":region,
                    "momentum_12_2":(100-i)/100,"eligible_global_ranking":True})
        data[0]["eligible_global_ranking"]=False
        result=m.group_highlights(data,20,4)
        self.assertEqual(len(result),12)
        self.assertNotIn("A00",result)
        self.assertEqual(len(set(result)),len(result))

    def test_discovery_fallback_includes_curated(self):
        with patch.object(m,"discover_global",side_effect=RuntimeError("offline")),\
             patch.object(m,"parse_directory",side_effect=RuntimeError("offline")):
            found,status,errors=m.discover({})
        self.assertIn("MU",found)
        self.assertIn("7203.T",found)
        self.assertEqual(status["status"],"unavailable")
        self.assertTrue(errors)

    def test_trim_cache_does_not_carry_legacy_score_and_stops(self):
        current=datetime.now(timezone.utc)
        payload={"ticker":"AAA","close":100.,"currency":"USD",
                 "avg_local_turnover_20d":50000000,"momentum_12_2":0.3,
                 "price_date":current.date().isoformat(),"source":"Test",
                 "last_checked_at":current.isoformat(),"score":100.,
                 "atr":4.5,"stop":89.}
        cached=m.cached_quotes({"stocks":[payload]},{"AAA":{}})
        self.assertIn("AAA",cached)
        self.assertNotIn("score",cached["AAA"])
        self.assertNotIn("atr",cached["AAA"])
        self.assertNotIn("stop",cached["AAA"])
if __name__=="__main__":unittest.main()
