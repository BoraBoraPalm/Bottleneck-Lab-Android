"""Deterministic offline tests; require no external market data or GitHub secrets."""
import io
import sys
import unittest
from pathlib import Path
from datetime import datetime, timedelta, timezone
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/"scripts"))
import build_snapshot as quotes
import v4_pipeline as v4

class TestV4(unittest.TestCase):
    def test_nasdaq_symbol_filters(self):
        hdr="Symbol|Security Name|ETF|Test Issue\n"
        rows=[f"A{i:04d}|Example Industry {i} Common Stock|N|N" for i in range(400)]
        rows+=["Z0001|Example ETF|Y|N","Z0002|Test company|N|Y","Z0003|Example stock Warrants|N|N"]
        with patch.object(v4,"read_url",return_value=(hdr+"\n".join(rows)).encode()):
            got=v4.parse_directory("https://example.test",True)
        self.assertEqual(len(got),400)
        self.assertNotIn("Z0001",got)
        self.assertNotIn("Z0002",got)
        self.assertNotIn("Z0003",got)

    def test_expired_quotes_rejected(self):
        old=(datetime.now(timezone.utc)-timedelta(days=20)).isoformat()
        recent=datetime.now(timezone.utc).isoformat()
        base={"close":10,"atr":0.3,"momentum":0.15,"score":80,"price_date":"2026-10-10"}
        seen=[{"ticker":"NVDA","last_checked_at":old,**base},{"ticker":"ETN","last_checked_at":recent,**base}]
        result=v4.carry_fresh({"stocks":seen},{"NVDA":{},"ETN":{}})
        self.assertNotIn("NVDA",result)
        self.assertIn("ETN",result)

    def test_quote_has_dollar_turnover_and_real_date(self):
        today=datetime.now(timezone.utc).date()
        bars=[((today-timedelta(days=90-i)).isoformat(),102.0,98.0,100.0,60000) for i in range(90)]
        with patch.object(quotes,"fetch_yahoo",return_value=(bars,"USD","offline-test")):
            got,error=quotes.quote("TEST","Test")
        self.assertIsNone(error)
        self.assertAlmostEqual(got["avg_dollar_turnover_20d"],6000000)
        self.assertGreater(got["atr"],0)

    def test_rotating_probe_includes_curated_baseline(self):
        known={t:{} for t in v4.CURATED}
        known.update({f"Q{i:04d}":{} for i in range(400)})
        with patch.object(v4,"PROBE_PER_RUN",40):
            req,_=v4.pick_batch(known,{"stocks":[]})
        self.assertIn("MU",req)
        self.assertGreaterEqual(len(req),len(v4.CURATED)+40)

if __name__=="__main__":
    unittest.main()
