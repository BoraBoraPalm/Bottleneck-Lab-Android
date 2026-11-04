"""Regression tests for the simplified global momentum-only app."""
import io,sys,unittest,csv
from pathlib import Path
from datetime import datetime,timezone,timedelta
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
import build_snapshot as q
import market_pipeline as m

class SimpleMarketTest(unittest.TestCase):
    def test_momentum_requires_253_bars_and_skips_only_recent_month(self):
        prices=[100.]*300
        before=q.momentum_12_2(prices)
        for i in range(1,22):prices[-i]=1000.
        self.assertEqual(before,q.momentum_12_2(prices))
        self.assertIsNone(q.momentum_12_2([100.]*252))
        prices[-22]=115
        self.assertAlmostEqual(q.momentum_12_2(prices),.15,places=5)
        # Month −2 (sessions 22–42 ago) belongs to the standard 12–2 window.
        prices=[100.]*300;prices[-43]=115
        self.assertAlmostEqual(q.momentum_12_2(prices),0,places=7)
        prices=[100.]*300;prices[-253]=80
        self.assertAlmostEqual(q.momentum_12_2(prices),.25,places=7)

    def test_cached_old_momentum_definition_is_recomputed_or_dropped(self):
        import tempfile,json as js
        current=datetime.now(timezone.utc);day=current.date().isoformat()
        base={"close":100.,"currency":"USD","avg_local_turnover_20d":50000000,
              "momentum_12_2":5.0,"momentum_basis":"Yahoo adjusted daily closes",
              "price_date":day,"source":"Yahoo Finance","last_checked_at":current.isoformat()}
        closes=[50.]*280;closes[-253]=40.;closes[-22]=60.;closes[-1]=70.
        points=[[(current.date()-timedelta(days=280-i)).isoformat(),c] for i,c in enumerate(closes)]
        points[-1][0]=day
        with tempfile.TemporaryDirectory() as tmp, patch("chart_history.ROOT",Path(tmp)):
            (Path(tmp)/"OLD.json").write_text(js.dumps({"asof":day,"source":"Yahoo Finance","points":points}))
            result=m.cached_quotes({"stocks":[{**base,"ticker":"OLD"},{**base,"ticker":"NOCHART"},
                {**base,"ticker":"NEW","momentum_12_2":.3,"momentum_skip_sessions":q.MOMENTUM_SKIP}]},
                {"OLD":{},"NOCHART":{},"NEW":{}})
        self.assertAlmostEqual(result["OLD"]["momentum_12_2"],.5,places=7)
        self.assertEqual(result["OLD"]["momentum_skip_sessions"],q.MOMENTUM_SKIP)
        self.assertIsNone(result["NOCHART"]["momentum_12_2"])
        self.assertIsNone(result["NOCHART"]["momentum_skip_sessions"])
        self.assertEqual(result["NEW"]["momentum_12_2"],.3)
        self.assertIn("NOCHART",m.requested_batch({"NOCHART":{}},result))

    def test_trade_republic_listed_stocks_get_priority_oldest_first(self):
        known={"NEW.VI":{"reference_isin":"AT0000000001"},"OLD.DE":{"reference_isin":"DE0000000002"},
               "FRESH.PA":{"reference_isin":"FR0000000003"},"OTHER.L":{"reference_isin":"GB0000000004"}}
        cache={"OLD.DE":{"last_checked_at":"2026-11-01T00:00:00Z"},"FRESH.PA":{"last_checked_at":"2026-11-04T00:00:00Z"}}
        listed={"AT0000000001","DE0000000002","FR0000000003"}
        self.assertEqual(m.tr_priority(known,cache,listed,limit=3),["NEW.VI","OLD.DE","FRESH.PA"])
        self.assertEqual(m.tr_priority(known,cache,listed,limit=1),["NEW.VI"])
        self.assertEqual(m.tr_priority(known,cache,None),[])
        self.assertNotIn("OTHER.L",m.tr_priority(known,cache,listed))
        self.assertIn("NEW.VI",m.requested_batch(known,cache,listed))

    def test_unknown_yahoo_symbols_are_skipped_for_thirty_days(self):
        today=datetime(2026,11,4,tzinfo=timezone.utc).date()
        old={"quote_misses":{"GONE.PA":"2026-10-20","OLD.PA":"2026-09-01","BAD":"x"}}
        misses=m.recent_misses(old,today)
        self.assertEqual(misses,{"GONE.PA":"2026-10-20"})
        known={"GONE.PA":{"reference_isin":"FR0000000001","region":"Europa"},"OK.PA":{"reference_isin":"FR0000000002","region":"Europa"}}
        batch=m.requested_batch(known,{},{"FR0000000001","FR0000000002"},misses)
        self.assertNotIn("GONE.PA",batch);self.assertIn("OK.PA",batch)

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
        self.assertEqual(result["momentum_skip_sessions"],21)

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
