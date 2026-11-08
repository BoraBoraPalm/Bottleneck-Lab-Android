"""Benchmark series for the Depot-Check: published only with verified data."""
import json
import sys
import tempfile
import unittest
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import benchmarks as b


def bars(n=60, adjusted=True):
    start = date(2026, 1, 1)
    out = []
    for i in range(n):
        close = 100 + i
        out.append(((start + timedelta(days=i)).isoformat(), close * 1.01, close * .99, close, 1e6, close * .9 if adjusted else None))
    out.append(out[-1][:3] + (out[-1][3] + 1,) + out[-1][4:])  # second bar for the same day
    return out


class Benchmarks(unittest.TestCase):
    def test_publishes_available_series_and_index(self):
        def fetch(symbol):
            if symbol == "^GDAXI":
                return bars(adjusted=False), "EUR", "Yahoo Finance"
            if symbol == "SPY":
                return bars(), "USD", "Yahoo Finance"
            raise RuntimeError("HTTP Error 404")
        with tempfile.TemporaryDirectory() as tmp:
            status = b.publish_benchmarks(Path(tmp), fetch)
            index = json.loads((Path(tmp) / "index.json").read_text())
            spy = json.loads((Path(tmp) / "SPY.json").read_text())
            dax = json.loads((Path(tmp) / "DAX.json").read_text())
            self.assertFalse((Path(tmp) / "ACWI.json").exists())
        self.assertEqual(status["available"], 2)
        self.assertIn("ACWI", status["missing"])
        listed = {e["id"]: e for e in index["benchmarks"]}
        self.assertTrue(listed["SPY"]["available"]); self.assertEqual(listed["SPY"]["currency"], "USD")
        self.assertFalse(listed["ACWI"]["available"]); self.assertIn("404", listed["ACWI"]["error"])
        self.assertEqual(listed["DAX"]["markets"], ["DE"])
        self.assertEqual(len(spy["points"]), 60, "one point per date")
        self.assertEqual(spy["points"][-1][1], 160.0, "scaled to the latest close")
        self.assertEqual(dax["points"][0][1], 100.0, "index without adjclose uses the close")
        self.assertEqual(spy["benchmark"]["name"], "S&P 500")

    def test_every_issuer_country_maps_to_at_most_one_benchmark(self):
        seen = {}
        for item in b.BENCHMARKS:
            for market in item["markets"]:
                self.assertNotIn(market, seen, market)
                seen[market] = item["id"]
        self.assertEqual(seen["*"], "ACWI")
        self.assertEqual(len({i["id"] for i in b.BENCHMARKS}), len(b.BENCHMARKS))


class SameListInApp(unittest.TestCase):
    @unittest.skipUnless(__import__("shutil").which("node"), "node required")
    def test_app_uses_the_same_benchmarks(self):
        import subprocess
        root = Path(__file__).resolve().parents[1]
        out = subprocess.run(["node", "-e", "console.log(JSON.stringify(require('./docs/trade-check.js').BENCHMARKS))"],
                             capture_output=True, text=True, check=True, cwd=root)
        app = [(x["id"], x["symbol"], x["markets"]) for x in json.loads(out.stdout)]
        self.assertEqual(app, [(x["id"], x["symbol"], x["markets"]) for x in b.BENCHMARKS])


if __name__ == "__main__":
    unittest.main()
