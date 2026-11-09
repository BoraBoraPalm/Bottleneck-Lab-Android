"""Benchmark series for the Depot-Check: published only with verified data."""
import json
import sys
import tempfile
import unittest
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import benchmarks as b


def bars(n=60, adjusted=True, payout_at=None):
    start = date(2026, 1, 1)
    out = []
    for i in range(n):
        close = 100 + i
        factor = .97 if payout_at is not None and i < payout_at else 1.0  # adjusted before the ex-day
        out.append(((start + timedelta(days=i)).isoformat(), close * 1.01, close * .99, close, 1e6,
                    close * factor if adjusted else None))
    out.append(out[-1][:3] + (out[-1][3] + 1,) + out[-1][4:])  # second bar for the same day
    return out


class Benchmarks(unittest.TestCase):
    def test_publishes_verified_etfs_and_index(self):
        calls = []
        def fetch(symbol):
            calls.append(symbol)
            if symbol == "SPY":
                return bars(payout_at=40), "USD", "Yahoo Finance"
            if symbol == "EL4F.DE":  # distributing, but no payout visible in the data
                return bars(), "EUR", "Yahoo Finance"
            if symbol == "EXS1.DE":  # accumulating: no payouts expected
                return bars(adjusted=False), "EUR", "Yahoo Finance"
            raise RuntimeError("HTTP Error 404")
        with tempfile.TemporaryDirectory() as tmp:
            status = b.publish_benchmarks(Path(tmp), fetch)
            index = json.loads((Path(tmp) / "index.json").read_text())
            spy = json.loads((Path(tmp) / "SPY.json").read_text())
            dax = json.loads((Path(tmp) / "DAX.json").read_text())
            self.assertFalse((Path(tmp) / "ACWI.json").exists())
        self.assertEqual(status["available"], 2)
        self.assertIn("ACWI", status["missing"])
        self.assertEqual(status["chosen"], {"SPY": "SPY", "DAX": "EXS1.DE"})
        self.assertIn("distributions missing", status["rejected"]["EL4F.DE"])
        listed = {e["id"]: e for e in index["benchmarks"]}
        self.assertTrue(listed["SPY"]["available"]); self.assertEqual(listed["SPY"]["currency"], "USD")
        self.assertEqual(listed["SPY"]["ter_percent"], 0.0945); self.assertEqual(listed["SPY"]["distributions_recent"], 1)
        self.assertFalse(listed["ACWI"]["available"]); self.assertIn("404", listed["ACWI"]["error"])
        self.assertEqual(listed["DAX"]["markets"], ["DE"]); self.assertEqual(listed["DAX"]["symbol"], "EXS1.DE")
        self.assertFalse(listed["DAX"]["distributing"])
        self.assertEqual(len(spy["points"]), 60, "one point per date")
        self.assertEqual(spy["points"][-1][1], 160.0, "scaled to the latest close")
        self.assertEqual(spy["closes"][-1], 160.0); self.assertEqual(len(spy["closes"]), 60)
        self.assertAlmostEqual(1 - (spy["points"][39][1] / spy["closes"][39]) / (spy["points"][40][1] / spy["closes"][40]), .03)
        self.assertEqual(dax["points"][0][1], 100.0, "accumulating ETF without adjclose uses the close")
        self.assertEqual(spy["benchmark"]["name"], "S&P 500"); self.assertEqual(dax["benchmark"]["ter_percent"], 0.16)
        self.assertEqual(calls.count("EL4F.DE"), 1)

    def test_distribution_detection(self):
        points = [["d1", 97.0], ["d2", 100.0], ["d3", 100.0000001], ["d4", 50.0]]
        closes = [100.0, 100.0, 100.0, 50.0]
        self.assertEqual(b.distributions(points, closes), [1], "3 % payout; rounding noise and splits ignored")

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
        app = [(x["id"], x["symbol"], x["ter"], x["markets"]) for x in json.loads(out.stdout)]
        self.assertEqual(app, [(x["id"], x["etfs"][0]["symbol"], x["etfs"][0]["ter_percent"], x["markets"]) for x in b.BENCHMARKS])


if __name__ == "__main__":
    unittest.main()
