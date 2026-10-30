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

if __name__=="__main__":unittest.main()
