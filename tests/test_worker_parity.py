"""The quote worker must compute trend/crash/ATR exactly like the pipeline."""
import json
import math
import random
import shutil
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from trade_guidance import price_context  # noqa: E402
from build_snapshot import momentum_12_2  # noqa: E402

SCRIPT = """
import {priceContext, turnover} from %s;
const rows = JSON.parse(process.argv[1]);
console.log(JSON.stringify({context: priceContext(rows), turnover: turnover(rows)}));
"""


def series(seed, days=420, split_at=None, crash=False):
    rnd = random.Random(seed)
    rows, price, factor = [], 50.0, 1.0
    for i in range(days):
        price *= math.exp(rnd.gauss(0.0004, 0.018))
        if crash and i > days - 15:
            price *= 0.97
        if split_at is not None and i == split_at:
            factor = 0.5  # raw prices before the split are twice the adjusted ones
        raw = price / (factor if i < (split_at or 0) else 1.0)
        adj = price * rnd.uniform(0.95, 0.99) if i < days - 1 else price * 0.98
        hi, lo = raw * (1 + rnd.uniform(0, .02)), raw * (1 - rnd.uniform(0, .02))
        rows.append(["2025-%03d" % i, raw, adj, hi, lo, rnd.choice([0, 1000, 25000])])
    return rows


@unittest.skipUnless(shutil.which("node"), "node is required for the worker parity test")
class WorkerParity(unittest.TestCase):
    def run_worker(self, rows):
        module = json.dumps((ROOT / "cloudflare" / "quote-worker.js").as_uri())
        out = subprocess.run(["node", "--input-type=module", "-e", SCRIPT % module, json.dumps(rows)],
                             capture_output=True, text=True, check=True, cwd=ROOT)
        return json.loads(out.stdout)

    def test_same_context_and_turnover_as_pipeline(self):
        for seed, kwargs in ((1, {}), (2, {"split_at": 300}), (3, {"crash": True}), (4, {"days": 260})):
            rows = series(seed, **kwargs)
            bars = [(d, hi, lo, raw, vol, adj) for d, raw, adj, hi, lo, vol in rows]
            expected = price_context(bars)
            got = self.run_worker(rows)
            self.assertEqual(set(got["context"]), set(expected), seed)
            for key, value in expected.items():
                if isinstance(value, bool) or isinstance(value, str):
                    self.assertEqual(got["context"][key], value, (seed, key))
                else:
                    self.assertAlmostEqual(got["context"][key], value, places=5, msg=(seed, key))
            turnovers = [b[3] * b[4] for b in bars[-20:] if b[4] > 0]
            want = round(sum(turnovers) / len(turnovers), 0) if len(turnovers) >= 12 else None
            self.assertEqual(got["turnover"], want, seed)
        self.assertIsNone(self.run_worker(series(5, days=200))["context"], "fewer than 253 sessions")

    def test_momentum_from_worker_points_matches_pipeline(self):
        rows = series(6)
        adjusted = [r[2] for r in rows]
        scale = rows[-1][1] / rows[-1][2]
        points = [a * scale for a in adjusted]
        n = len(points)
        self.assertAlmostEqual(points[n - 22] / points[n - 253] - 1, momentum_12_2(adjusted), places=6)


DECIDE = """
const live = require(%s);
const cases = JSON.parse(process.argv[1]);
console.log(JSON.stringify(cases.map(([stock, market, now]) => live.decide({...stock}, market, Date.parse(now)))));
"""


@unittest.skipUnless(shutil.which("node"), "node is required for the decision parity test")
class DecisionParity(unittest.TestCase):
    def test_entry_exit_and_levels_match_pipeline(self):
        from unittest.mock import patch
        import trade_guidance
        base = {"momentum_12_2": .2, "sma200_ratio": .05, "return_21d": .01, "drawdown_252d": -.04,
                "reference_close_eur": 90.0, "eur_per_unit": .9, "risk_reference_native": 85.0, "close": 100.0,
                "atr14_native": 2.0, "crash_warning": False, "correction_warning": False, "price_date": "2026-11-03",
                "context_basis": "Yahoo adjusted OHLC, signal after close", "sma200_native": 95.0,
                "crash_21_level_native": 80.0, "crash_peak_level_native": 70.0}
        variants = [{}, {"crash_warning": True}, {"sma200_ratio": -.01}, {"momentum_12_2": -.1},
                    {"correction_warning": True}, {"price_date": "2026-10-20"}, {"atr14_native": 40.0},
                    {"momentum_12_2": None}]
        markets = [{"risk": "normal"}, {"risk": "downtrend"}, {"risk": None}]
        cases = [[{**base, **v}, m, "2026-11-04T12:00:00Z"] for v in variants for m in markets]
        module = json.dumps(str(ROOT / "docs" / "live-quote.js"))
        out = subprocess.run(["node", "-e", DECIDE % module, json.dumps(cases)], capture_output=True, text=True, check=True, cwd=ROOT)
        got = json.loads(out.stdout)
        fixed = type("FixedDate", (), {"now": staticmethod(lambda tz=None: __import__("datetime").datetime(2026, 11, 4, 12, tzinfo=tz))})
        for (stock, market, _), js in zip(cases, got):
            py = dict(stock)
            with patch.object(trade_guidance, "datetime", fixed):
                trade_guidance.assign_decision(py, market)
            for key in ("entry_review", "exit_review", "model_buy_limit_eur", "model_initial_stop_eur",
                        "risk_reference_eur", "entry_reference_eur", "sma200_level_eur", "crash_21_level_eur", "crash_peak_level_eur"):
                self.assertEqual(js.get(key), py.get(key), (key, stock, market))


if __name__ == "__main__":
    unittest.main()
