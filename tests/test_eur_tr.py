"""Offline tests for EUR display and conservative TR-AT ISIN membership."""
import json
import sys
import unittest
from pathlib import Path
from unittest.mock import patch
from datetime import datetime, timezone, timedelta
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
import fx_eur, tr_at_universe

class TestCurrencyAndBroker(unittest.TestCase):
    def test_eur_conversion_of_close_and_atr(self):
        stocks=[{"ticker":"MU","close":100.0,"atr":5.0,"currency":"USD"},
                {"ticker":"NEX.PA","close":50.0,"atr":1.0,"currency":"EUR"},
                {"ticker":"MISSING","close":30.0,"atr":1.0,"currency":"XYZ"}]
        rates={"USD":{"eur_per_unit":0.8,"fx_date":"2026-10-30"},
               "EUR":{"eur_per_unit":1,"fx_date":"2026-10-30"}}
        count,missing=fx_eur.add_eur_prices(stocks,rates)
        self.assertEqual(count,2);self.assertEqual(missing,["XYZ"])
        self.assertEqual(stocks[0]["reference_close_eur"],80.0)
        self.assertEqual(stocks[0]["reference_atr_eur"],4.0)
        self.assertEqual(stocks[1]["reference_close_eur"],50.0)
        self.assertNotIn("reference_close_eur",stocks[2])

    def test_fx_date_is_required(self):
        d=datetime.now(timezone.utc).date()
        rates=[{"date":d.isoformat(),"base":"EUR","quote":f"X{i:02d}","rate":1.25}
               for i in range(21)]
        def fake(url,timeout):
            return json.dumps(rates).encode()
        got=fx_eur.latest_eur_rates(fake)
        self.assertAlmostEqual(got["X00"]["eur_per_unit"],0.8)

    def test_subunits_and_previous_rates(self):
        today=datetime(2026,11,8,tzinfo=timezone.utc).date()
        fx={"EUR":{"eur_per_unit":1.0,"fx_date":"2026-11-08","source":"native EUR"},
            "ILS":{"eur_per_unit":.25,"fx_date":"2026-11-06","source":"ref"},
            "ZAR":{"eur_per_unit":.05,"fx_date":"2026-11-06","source":"ref"}}
        fx_eur.add_subunits(fx)
        self.assertAlmostEqual(fx["ILA"]["eur_per_unit"],.0025)
        self.assertAlmostEqual(fx["ZAc"]["eur_per_unit"],.0005)
        previous={"fx_eur":{"GBP":{"eur_per_unit":1.15,"fx_date":"2026-11-05"},
                            "SAR":{"eur_per_unit":.23,"fx_date":"2026-11-02"},
                            "ILS":{"eur_per_unit":.3,"fx_date":"2026-11-05"},
                            "OLD":{"eur_per_unit":2.0,"fx_date":"2026-10-20"},
                            "BAD":{"eur_per_unit":"x","fx_date":"2026-11-05"}}}
        merged,reused=fx_eur.with_previous_rates(fx,previous,today=today)
        self.assertEqual(reused,["GBP","SAR"],"only valid rates at most a week old")
        self.assertEqual(merged["ILS"]["eur_per_unit"],.25,"today's rate wins")
        self.assertAlmostEqual(merged["GBp"]["eur_per_unit"],.0115)
        self.assertIn("previous run",merged["GBP"]["source"])
        self.assertNotIn("OLD",merged)

    def test_yahoo_fallback_for_missing_currencies(self):
        today=datetime(2026,11,8,tzinfo=timezone.utc).date()
        fx={"EUR":{"eur_per_unit":1.0,"fx_date":"2026-11-08","source":"native EUR"},
            "USD":{"eur_per_unit":.9,"fx_date":"2026-11-06","source":"ref"}}
        calls=[]
        def fake(symbol):
            calls.append(symbol)
            if symbol=="TWDEUR=X":return [("2026-11-05",1,1,.027,0,None),("2026-11-06",1,1,.028,0,None)],"EUR","Yahoo"
            if symbol=="KWDEUR=X":return [("2026-11-06",1,1,2.8,0,None)],"EUR","Yahoo"
            if symbol=="SAREUR=X":return [("2026-10-01",1,1,.24,0,None)],"EUR","Yahoo"
            raise RuntimeError("HTTP 404")
        merged,used,failed=fx_eur.with_yahoo_rates(fx,{"USD","EUR","TWD","KWF","SAR","XXX",None,"GBp"},fetch=fake,today=today)
        self.assertEqual(sorted(calls),["GBPEUR=X","KWDEUR=X","SAREUR=X","TWDEUR=X","XXXEUR=X"],"only currencies without a rate")
        self.assertEqual(used,["KWD","TWD"])
        self.assertEqual(sorted(failed),["GBP","SAR","XXX"],"stale and failed rates are reported, not used")
        self.assertAlmostEqual(merged["TWD"]["eur_per_unit"],.028)
        self.assertAlmostEqual(merged["KWF"]["eur_per_unit"],.0028,"fils from Kuwaiti dinar")
        self.assertEqual(merged["USD"]["eur_per_unit"],.9,"reference rate is kept")
        count,missing=fx_eur.add_eur_prices([{"ticker":"2330.TW","close":1000.0,"atr":10.0,"currency":"TWD"}],merged)
        self.assertEqual((count,missing),(1,[]))

    def test_isin_join_requires_unambiguous_mapping(self):
        ids={"MU":[("US5951121038","NASDAQ")],
             "X":[("US0000000001","NASDAQ"),("US0000000002","NASDAQ")],
             "SU":[("FR0000121972","EURONEXT PARIS")],
             "HUBB":[("US4435106079","NYSE")]}
        self.assertEqual(tr_at_universe.candidate_isins("MU",ids),"US5951121038")
        self.assertIsNone(tr_at_universe.candidate_isins("X",ids))
        self.assertEqual(tr_at_universe.candidate_isins("SU.PA",ids),"FR0000121972")
        self.assertIsNone(tr_at_universe.candidate_isins("MISSING",ids))

    def test_tr_fail_closed_on_missing_official_list(self):
        stocks=[{"ticker":"MU"},{"ticker":"SU.PA"}]
        with patch.object(tr_at_universe,"isin_values_from_pdf",side_effect=ValueError("No PDF")), \
             patch.object(tr_at_universe,"decode_identifiers",return_value={
                 "MU":[("US5951121038","NASDAQ")]}):
            status=tr_at_universe.apply_tr_filter(stocks,fetch=lambda *args,**kw:b"not_pdf")
        self.assertFalse(status["list_loaded"])
        self.assertEqual(status["verified"],0)
        self.assertTrue(all(not s["tr_at_listed"] for s in stocks))

    def test_tr_inclusion_uses_isin_only(self):
        stocks=[{"ticker":"MU"},{"ticker":"X"}]
        with patch.object(tr_at_universe,"isin_values_from_pdf",return_value={"US5951121038"}),\
             patch.object(tr_at_universe,"decode_identifiers",return_value={
                "MU":[("US5951121038","NASDAQ")],
                "X":[("US0000000001","NASDAQ"),("US0000000002","NASDAQ")]}):
            result=tr_at_universe.apply_tr_filter(stocks,fetch=lambda *args,**kw:b"fixture")
        self.assertTrue(stocks[0]["tr_at_listed"])
        self.assertFalse(stocks[1]["tr_at_listed"])
        self.assertEqual(result["verified"],1)

    def test_preloaded_reference_is_reused_without_download(self):
        stocks=[{"ticker":"MU","reference_isin":"US5951121038"}]
        reference={"pdf_isins":{"US5951121038"},"ids":{"MU":[("US5951121038","NASDAQ")]},
                   "status":{"list_loaded":True,"mapping_loaded":True,"verified":0,"unknown":0}}
        def no_fetch(*args,**kw):raise AssertionError("must not download twice")
        result=tr_at_universe.apply_tr_filter(stocks,fetch=no_fetch,reference=reference)
        self.assertEqual(result["verified"],1);self.assertTrue(stocks[0]["tr_at_listed"])
        self.assertEqual(reference["status"]["verified"],0,"shared reference status is not mutated")

if __name__=="__main__":unittest.main()
