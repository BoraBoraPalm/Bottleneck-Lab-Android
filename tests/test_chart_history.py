"""Chart data sources must match the latest native quote without unsafe filenames."""
import json,os,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
import chart_history as charts

class ChartHistoryTests(unittest.TestCase):
    def fixture(self):
        days=["2025-03-%02d"%(i+1) for i in range(30)]
        # Underlying adjusted history is exactly one quarter raw historic price;
        # latest raw 100 and latest adjusted 25 -> scale=4.
        return [(d,110,90,80+i*20/29,10000,20+i*5/29) for i,d in enumerate(days)]

    def test_adjusted_closes_normalized_to_latest_native_raw(self):
        bars=self.fixture()
        result=charts.chart_payload("7203.T",bars,"JPY","Yahoo Finance")
        self.assertEqual(result["currency"],"JPY")
        self.assertEqual(result["asof"],bars[-1][0])
        self.assertAlmostEqual(result["points"][-1][1],bars[-1][3],places=5)
        self.assertAlmostEqual(result["points"][0][1],80,places=5)
        self.assertEqual(result["basis"],"adjusted close normalized to latest raw close")

    def test_reject_unadjusted_fallback(self):
        bars=self.fixture()
        self.assertIsNone(charts.chart_payload("7203.T",bars,"JPY","Stooq US (unverified adjustment)"))
        self.assertIsNone(charts.chart_payload("7203.T",[(*x[:5],None) for x in bars],"JPY","Yahoo Finance"))

    def test_safe_filenames_and_current_cache(self):
        with tempfile.TemporaryDirectory() as temp,patch.object(charts,"ROOT",Path(temp)):
            result=charts.chart_payload("7203.T",self.fixture(),"JPY","Yahoo Finance")
            self.assertTrue(charts.write_chart(result))
            self.assertTrue(charts.chart_is_current("7203.T","2025-03-30"))
            self.assertFalse(charts.chart_is_current("7203.T","2025-03-29"))
            self.assertEqual(charts.chart_count(),1)
            with charts.chart_file("7203.T").open(encoding="utf-8") as f:
                saved=json.load(f)
            self.assertEqual(saved["points"][-1][0],"2025-03-30")
            for bad in ("../data","x/y","..","some\\other"):
                with self.assertRaises(ValueError):
                    charts.chart_file(bad)

    def test_duplicate_or_unsorted_dates_rejected(self):
        bars=self.fixture()
        duplicate=bars[:10]+[bars[9]]+bars[10:]
        self.assertIsNone(charts.chart_payload("SAP.DE",duplicate,"EUR","Yahoo Finance"))
        self.assertIsNone(charts.chart_payload("SAP.DE",list(reversed(bars)),"EUR","Yahoo Finance"))

if __name__=="__main__":unittest.main()
