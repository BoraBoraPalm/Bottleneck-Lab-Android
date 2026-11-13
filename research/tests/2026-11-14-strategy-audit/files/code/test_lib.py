"""Offline unit tests of the research library (synthetic data only)."""
import io, json, math, sys, tempfile, unittest, zipfile
from pathlib import Path
import numpy as np
import pandas as pd
sys.path.insert(0, str(Path(__file__).resolve().parent))
import lib

FRENCH = """This file was created using the 202609 CRSP database.
It contains value- and equal-weighted returns.

  Average Value Weighted Returns -- Monthly
,SMALL LoBM,BIG HiBM
192607,   1.00,  -99.99
192608,  -2.00,   3.00

  Average Equal Weighted Returns -- Monthly
,SMALL LoBM,BIG HiBM
192607,   9.00,   9.00

  Annual
,SMALL LoBM,BIG HiBM
1927,  10.00,  20.00

Copyright 2026 Eugene F. Fama and Kenneth R. French
"""


class ParsingTest(unittest.TestCase):
    def test_french_sections_and_missing(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "x.zip"
            with zipfile.ZipFile(p, "w") as z:
                z.writestr("x.csv", FRENCH)
            t = lib.french_table(p, lib.VW_M)
            self.assertEqual(list(t.columns), ["SMALL LoBM", "BIG HiBM"])
            self.assertEqual(str(t.index[1]), "1926-08")
            self.assertAlmostEqual(t.iloc[0, 0], 0.01)
            self.assertTrue(math.isnan(t.iloc[0, 1]))
            self.assertAlmostEqual(lib.pick(t, "BIG", "HIBM").iloc[1], 0.03)
            self.assertEqual(len(lib.french_sections(p)), 3)
            with self.assertRaises(KeyError):
                lib.pick(t, "BM")

    def test_yahoo_monthly(self):
        days = pd.bdate_range("2020-01-01", "2020-04-30")
        px = 100 * np.cumprod(np.full(len(days), 1.001))
        payload = {"chart": {"result": [{"timestamp": [int(x.timestamp()) + 52200 for x in days],
                   "indicators": {"adjclose": [{"adjclose": list(px)}]}}]}}
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "s.json"
            p.write_text(json.dumps(payload))
            s = lib.yahoo_adjclose(p)
            m = lib.to_monthly(s)
        self.assertEqual([str(x) for x in m.index], ["2020-02", "2020-03", "2020-04"])
        feb = len(pd.bdate_range("2020-02-01", "2020-02-29"))
        self.assertAlmostEqual(m.iloc[0], 1.001 ** feb - 1, places=10)


class StatisticsTest(unittest.TestCase):
    def test_holm_and_bh(self):
        p = [0.01, 0.04, 0.03, np.nan]
        np.testing.assert_allclose(lib.holm(p)[:3], [0.03, 0.06, 0.06])
        np.testing.assert_allclose(lib.bh(p)[:3], [0.03, 0.04, 0.04])

    def test_nw_mean_matches_iid_t_without_lags(self):
        rng = np.random.default_rng(1)
        x = rng.normal(0.01, 0.05, 600)
        m, t = lib.nw_mean(x, lags=0)
        self.assertAlmostEqual(t, m / (x.std(ddof=0) / math.sqrt(len(x))), places=8)

    def test_versus_identity_and_cost(self):
        idx = pd.period_range("1990-01", periods=360, freq="M")
        rng = np.random.default_rng(2)
        m = pd.Series(rng.normal(0.008, 0.04, 360), idx)
        rf = pd.Series(0.002, idx)
        same = lib.versus(m, m, rf)
        self.assertAlmostEqual(same["active"], 0.0, places=12)
        self.assertAlmostEqual(same["beta"], 1.0, places=8)
        worse = lib.versus(m, m, rf, cost=0.01)
        self.assertAlmostEqual(worse["active"], math.log(0.99), places=10)
        self.assertEqual(worse["win10"], 0.0)
        better = lib.versus((1 + m) * 1.001 - 1, m, rf)
        self.assertAlmostEqual(better["breakeven_cost"], 1 - 1.001 ** -12, places=8)
        self.assertEqual(better["win5"], 1.0)


class TaxModelTest(unittest.TestCase):
    def setUp(self):
        self.n = 120
        self.r = np.full(self.n, 0.008)
        self.zero = np.zeros(self.n)
        self.years = np.repeat(np.arange(2000, 2010), 12)

    def test_buy_and_hold_defers_tax(self):
        g = 1.008 ** self.n
        v = lib.after_tax(self.r, self.zero, np.ones(self.n), self.years, div=0.0)
        self.assertAlmostEqual(v, 1 + (g - 1) * (1 - lib.KEST), places=10)

    def test_full_turnover_pays_every_year_and_is_worse(self):
        hold = lib.after_tax(self.r, self.zero, np.ones(self.n), self.years, div=0.0)
        churn = lib.after_tax(self.r, self.zero, np.ones(self.n), self.years, div=0.0, turnover=12.0)
        yearly = 1 + (1.008 ** 12 - 1) * (1 - lib.KEST)
        self.assertAlmostEqual(churn, yearly ** 10, places=10)
        self.assertLess(churn, hold)

    def test_losses_are_not_carried_forward(self):
        r = np.array([-0.5] * 1 + [0.0] * 11 + [1.0] + [0.0] * 11)   # year 1: -50 %, year 2: +100 %
        years = np.repeat([2000, 2001], 12)
        hold = lib.after_tax(r, np.zeros(24), np.ones(24), years, div=0.0)
        churn = lib.after_tax(r, np.zeros(24), np.ones(24), years, div=0.0, turnover=12.0)
        self.assertAlmostEqual(hold, 1.0, places=12)                    # back to the start, no gain
        self.assertAlmostEqual(churn, 1.0 - lib.KEST * 0.5, places=12)  # taxed on the recovery

    def test_switch_to_cash_realises_gain_and_costs(self):
        w = np.array([1.0] * 12 + [0.0] * 12)
        r = np.array([0.1] + [0.0] * 23)
        years = np.repeat([2000, 2001], 12)
        v = lib.after_tax(r, np.zeros(24), w, years, cost=0.001, div=0.0)
        bought = 0.999
        sold = bought * 1.1 * 0.999
        # the gain is realised by the switch in January of the second year and taxed at that year-end
        self.assertAlmostEqual(v, sold - lib.KEST * (bought * 1.1 - bought), places=12)

    def test_tax_windows_shape(self):
        idx = pd.period_range("1980-01", periods=480, freq="M")
        m = pd.Series(0.007, idx)
        out = lib.tax_windows(m, m, pd.Series(0.0, idx), turnover=1.0)
        self.assertEqual(out["tax_windows"], 21)
        self.assertLess(out["tax_median_ratio"], 1.0)
        self.assertEqual(out["tax_win_share"], 0.0)


if __name__ == "__main__":
    unittest.main()
