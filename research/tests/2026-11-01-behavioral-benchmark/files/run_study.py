"""Fixed one-off behavioral portfolio comparison; run with Python 3.12.

These are published research portfolio returns, not a stock-level execution
simulation. Read protocol.json and REPORT.md before interpreting any numbers.
"""
from __future__ import annotations

import csv
import hashlib
import io
import itertools
import json
import math
import re
from pathlib import Path
from zipfile import ZipFile

import numpy as np
import pandas as pd
import pyarrow.parquet as pq
from scipy.stats import norm

ROOT = Path(__file__).resolve().parent
DATA, OUT = ROOT / "data", ROOT / "output"
PSYCH = ["Mom12m", "EarningsSurprise", "REV6", "AnnouncementReturn"]
SIGNALS = PSYCH + ["BM", "GP"]
SEED = 20261101
REPS = 10000


def french_monthly(path):
    with ZipFile(path) as z:
        raw = z.read(next(n for n in z.namelist() if n.lower().endswith(".csv"))).decode("utf-8-sig")
    lines = raw.splitlines()
    first = next(i for i, line in enumerate(lines) if re.match(r"^\s*\d{6},", line))
    header = [x.strip() for x in next(csv.reader([lines[first - 1]]))]
    rows = []
    for line in lines[first:]:
        if not re.match(r"^\s*\d{6},", line):
            break
        row = next(csv.reader([line]))
        rows.append([row[0].strip()] + [float(x) / 100 for x in row[1:]])
    df = pd.DataFrame(rows, columns=["month"] + header[1:])
    df.index = pd.PeriodIndex(df.pop("month"), freq="M")
    assert df.index.is_unique and df.index.is_monotonic_increasing
    return df


def sleeves(filename, construction):
    if not (DATA / filename).exists():
        # The compact study bundle contains the exact selected input returns.
        # Use download_data.py to re-fetch and re-parse all source portfolios.
        universe = {"quintile": "value_weighted_quintiles", "liquid_original": "liquid_original",
                    "annual_big": "annual_big_sensitivity_only"}[construction]
        cached = pd.read_csv(OUT / (universe + "_inputs.csv"), index_col=0)
        cached.index = pd.PeriodIndex(cached.index, freq="M")
        counts = json.loads((DATA / "selected_counts.json").read_text())[universe]
        assert cached.index.equals(pd.period_range("2000-01", "2025-12", freq="M"))
        assert not cached[SIGNALS].isna().any().any()
        return cached[SIGNALS], counts
    ports = ["BH"] if construction == "annual_big" else ["05"]
    if construction == "liquid_original":
        ports = None
    filters = [("signalname", "in", SIGNALS)]
    if ports:
        filters.append(("port", "in", ports))
    frame = pq.read_table(DATA / filename, filters=filters).to_pandas()
    frame["month"] = pd.to_datetime(frame.date).dt.to_period("M")
    if construction == "liquid_original":
        # Original quantile count is fixed by each original paper, not chosen by
        # observed returns. Every included signal has positive ex-ante direction.
        frame = frame[frame.port != "LS"].copy()
        last = frame.groupby("signalname")["port"].max()
        frame = frame[frame.apply(lambda r: r.port == last[r.signalname], axis=1)]
    assert not frame.duplicated(["month", "signalname"]).any()
    target = pd.period_range("2000-01", "2025-12", freq="M")
    frame = frame[frame.month.isin(target)].copy()
    assert frame.Nshort.eq(0).all()
    assert frame.Nlong.gt(0).all()
    ret = frame.pivot(index="month", columns="signalname", values="ret").reindex(target)
    assert set(ret) == set(SIGNALS)
    assert not ret.isna().any().any(), f"Incomplete target period in {filename}"
    ret = ret[SIGNALS] / 100
    assert np.isfinite(ret).all().all() and (ret > -1).all().all()
    assert (ret.abs() < 3).all().all(), "Investigate input units/extreme returns"
    counts = {}
    for s, sub in frame.groupby("signalname"):
        counts[s] = {"minimum": int(sub.Nlong.min()), "median": float(sub.Nlong.median()),
                     "maximum": int(sub.Nlong.max()), "port": sub.port.iloc[0]}
    return ret, counts


def candidates(base):
    out = {s: base[s].to_numpy() for s in PSYCH}
    weights = {s: {s: 1.0} for s in PSYCH}
    for a, b in itertools.combinations(PSYCH, 2):
        name = a + " + " + b
        out[name] = .5 * (base[a].to_numpy() + base[b].to_numpy())
        weights[name] = {a: .5, b: .5}
    name = "Equal four"
    out[name] = base[PSYCH].mean(axis=1).to_numpy()
    weights[name] = {s: .25 for s in PSYCH}
    for s in ["BM", "GP"]:
        out[s] = base[s].to_numpy()
        weights[s] = {s: 1.0}
    out["Momentum + Value + Quality"] = base[["Mom12m", "BM", "GP"]].mean(axis=1).to_numpy()
    weights["Momentum + Value + Quality"] = {s: 1 / 3 for s in ["Mom12m", "BM", "GP"]}
    assert len(out) == 14
    assert all(math.isclose(sum(w.values()), 1) for w in weights.values())
    return pd.DataFrame(out, index=base.index), weights


def drag(returns, annual_cost):
    return (1 + returns) * (1 - annual_cost) ** (1 / 12) - 1


def hac_ols(y, x=None, lags=12):
    y = np.asarray(y, dtype=float)
    x = np.ones((len(y), 1)) if x is None else np.column_stack([np.ones(len(y)), x])
    assert len(y) > x.shape[1] + lags
    b = np.linalg.lstsq(x, y, rcond=None)[0]
    u = y - x @ b
    scores = x * u[:, None]
    meat = scores.T @ scores
    for lag in range(1, lags + 1):
        c = scores[lag:].T @ scores[:-lag]
        meat += (1 - lag / (lags + 1)) * (c + c.T)
    bread = np.linalg.pinv(x.T @ x)
    cov = bread @ meat @ bread * len(y) / (len(y) - x.shape[1])
    se = np.sqrt(np.maximum(0, np.diag(cov)))
    z = float(b[0] / se[0]) if se[0] > 1e-14 else 0.0
    return {"coefficient": float(b[0]), "se": float(se[0]), "z": z,
            "p": float(2 * norm.sf(abs(z))), "betas": [float(v) for v in b[1:]]}


def holm(ps):
    order = np.argsort(ps)
    out = np.empty(len(ps))
    last = 0.0
    for i, j in enumerate(order):
        last = max(last, min(1.0, (len(ps) - i) * ps[j]))
        out[j] = last
    return out


def metrics(r, rf, market):
    r, rf, market = (np.asarray(x, dtype=float) for x in (r, rf, market))
    assert len(r) == len(rf) == len(market) and np.isfinite(r).all()
    logs = np.log1p(r)
    wealth = np.r_[1.0, np.exp(logs.cumsum())]
    dd = wealth / np.maximum.accumulate(wealth) - 1
    excess = r - rf
    tracking = r - market
    longest = run = 0
    for v in dd[1:]:
        run = run + 1 if v < -1e-12 else 0
        longest = max(longest, run)
    relative = np.log1p(r) - np.log1p(market)
    roll = {}
    for months in (36, 60, 120):
        if len(r) < months:
            continue
        vals = np.convolve(relative, np.ones(months), "valid")
        roll[str(months)] = {"windows": len(vals), "outperformance_fraction": float(np.mean(vals > 0))}
    return {"months": len(r), "cagr": float(np.expm1(logs.mean() * 12)),
            "volatility": float(r.std(ddof=1) * np.sqrt(12)),
            "sharpe": float(excess.mean() / excess.std(ddof=1) * np.sqrt(12)),
            "max_month_end_drawdown": float(dd.min()), "longest_underwater_months": longest,
            "ending_wealth_1": float(wealth[-1]),
            "geometric_relative_excess": float(np.expm1(relative.mean() * 12)),
            "information_ratio": float(tracking.mean() / tracking.std(ddof=1) * np.sqrt(12))
                 if tracking.std(ddof=1) > 1e-12 else 0.0,
            "rolling_outperformance": roll}


def index_resamples(n, block, repetitions, rng):
    blocks = math.ceil(n / block)
    starts = rng.integers(n, size=(repetitions, blocks))
    return ((starts[:, :, None] + np.arange(block)) % n).reshape(repetitions, -1)[:, :n]


def bootstrap(returns, market, rf, repetitions=REPS, block=12):
    """Paired circular block bootstrap. Same months for every portfolio/market.

    Simultaneous intervals use maximum absolute, HAC-standardized deviations
    across the complete predeclared 14-strategy family. This controls only the
    within-study multiplicity, not the prior literature's selection process.
    """
    vals = returns.to_numpy()
    market, rf = np.asarray(market), np.asarray(rf)
    n, k = vals.shape
    relative = np.log1p(vals) - np.log1p(market[:, None])
    means = relative.mean(axis=0)
    ses = np.array([hac_ols(relative[:, j])["se"] for j in range(k)])
    rng = np.random.default_rng(SEED + block)
    boots, sharpe_diffs, winners = [], [], np.zeros(k, dtype=int)
    for first in range(0, repetitions, 250):
        idx = index_resamples(n, block, min(250, repetitions - first), rng)
        boots.append(relative[idx].mean(axis=1))
        e = vals[idx] - rf[idx, None]
        sr = e.mean(axis=1) / e.std(axis=1, ddof=1) * np.sqrt(12)
        bm = market[idx] - rf[idx]
        bsr = bm.mean(axis=1) / bm.std(axis=1, ddof=1) * np.sqrt(12)
        sharpe_diffs.append(sr - bsr[:, None])
        winners += np.bincount(np.argmax(sr, axis=1), minlength=k)
    boots = np.concatenate(boots)
    sharpe_diffs = np.concatenate(sharpe_diffs)
    critical = float(np.quantile(np.max(abs((boots - means) / ses), axis=1), .95))
    out = {}
    for j, name in enumerate(returns):
        out[name] = {
            "relative_excess_pointwise_95": np.expm1(np.quantile(boots[:, j], [.025, .975]) * 12).tolist(),
            "relative_excess_simultaneous_95": np.expm1((means[j] + np.array([-1, 1]) * critical * ses[j]) * 12).tolist(),
            "sharpe_difference_pointwise_95": np.quantile(sharpe_diffs[:, j], [.025, .975]).tolist(),
            "bootstrap_best_sharpe_fraction_NOT_future_probability": float(winners[j] / repetitions),
        }
    return {"block_months": block, "repetitions": repetitions, "simultaneous_critical": critical, "strategies": out}


def analyze(gross, ff, costs=(0, .005, .01, .02, .04), detailed=True):
    ff = ff.reindex(gross.index)
    assert not ff.isna().any().any()
    market, rf = ff["Market"].to_numpy(), ff["RF"].to_numpy()
    report = {"first": str(gross.index[0]), "last": str(gross.index[-1]), "months": len(gross),
              "benchmark": metrics(market, rf, market), "cost_scenarios": {}}
    for cost in costs:
        net = drag(gross, cost)
        rows = {}
        for name in gross:
            m = metrics(net[name], rf, market)
            m["break_even_annual_extra_cost"] = 1 - (1 + report["benchmark"]["cagr"]) / (1 + metrics(gross[name], rf, market)["cagr"])
            if cost == .01:
                diff = np.log1p(net[name]) - np.log1p(market)
                m["relative_log_hac"] = hac_ols(diff)
                m["capm_alpha_hac"] = hac_ols(net[name] - rf, ff[["Mkt-RF"]].to_numpy())
                m["ff5_momentum_alpha_hac"] = hac_ols(net[name] - rf, ff[["Mkt-RF", "SMB", "HML", "RMW", "CMA", "Mom"]].to_numpy())
            rows[name] = m
        if cost == .01:
            for field in ("relative_log_hac", "capm_alpha_hac", "ff5_momentum_alpha_hac"):
                ps = holm([rows[name][field]["p"] for name in rows])
                for name, p in zip(rows, ps):
                    rows[name][field]["p_holm_14"] = float(p)
        report["cost_scenarios"][str(cost)] = rows
    if detailed:
        net = drag(gross, .01)
        report["bootstrap"] = {str(b): bootstrap(net, market, rf, block=b) for b in (6, 12, 24)}
    return report


def fixed_development_selection(gross, ff):
    names = list(gross)[:11]
    net = drag(gross[names], .01)
    early = net.loc["2000-01":"2013-12"]
    rf = ff.loc[early.index, "RF"]
    sharpes = {n: metrics(early[n], rf, ff.loc[early.index, "Market"])["sharpe"] for n in names}
    selected = sorted(sharpes, key=lambda n: (-sharpes[n], n))[0]
    late = net.loc["2014-01":"2025-12"]
    return {"selected_using_development_only": selected, "development_sharpes": sharpes,
            "evaluation": metrics(late[selected], ff.loc[late.index, "RF"], ff.loc[late.index, "Market"]),
            "evaluation_benchmark": metrics(ff.loc[late.index, "Market"], ff.loc[late.index, "RF"], ff.loc[late.index, "Market"]),
            "warning": "Retrospective protocol; period not genuinely unseen to the literature or analyst."}


def walk_forward(gross, ff):
    """Ten-year trailing window; select once each January; trade next 12 months."""
    names = list(gross)[:11]
    net = drag(gross[names], .01)
    choices, returns = [], []
    for year in range(2010, 2026):
        train = net.loc[f"{year - 10}-01":f"{year - 1}-12"]
        assert len(train) == 120
        rf = ff.loc[train.index, "RF"]
        sharpes = {n: metrics(train[n], rf, ff.loc[train.index, "Market"])["sharpe"] for n in names}
        selected = sorted(sharpes, key=lambda n: (-sharpes[n], n))[0]
        target = net.loc[f"{year}-01":f"{year}-12", selected]
        assert len(target) == 12 and train.index.max() < target.index.min()
        choices.append({"year": year, "selected": selected, "training_last": str(train.index.max()), "train_sharpe": sharpes[selected]})
        returns.append(target)
    actual = pd.concat(returns)
    bm, rf = ff.loc[actual.index, "Market"], ff.loc[actual.index, "RF"]
    return {"choices": choices, "metrics": metrics(actual, rf, bm), "benchmark": metrics(bm, rf, bm),
            "relative_log_hac": hac_ols(np.log1p(actual) - np.log1p(bm)),
            "not_optimized": "Fixed 120-month training window and annual selection, no hindsight weights."}, actual


def validate_engine():
    # Known wealth path: initial loss counts in drawdown, and return percentages
    # are compounded, not added. No synthetic result is used as empirical data.
    r = np.array([-.5, 1., 0., 0.])
    m = metrics(r, np.zeros(4), np.zeros(4))
    assert math.isclose(m["max_month_end_drawdown"], -.5)
    assert math.isclose(m["ending_wealth_1"], 1.)
    assert math.isclose(m["cagr"], 0.)
    assert np.allclose(holm([.01, .03, .2]), [.03, .06, .2])
    x = np.array([-.02, .01, .03, -.01, .02] * 12)
    # With zero HAC lags, intercept variance is sample variance/n exactly.
    assert math.isclose(hac_ols(x, lags=0)["se"], x.std(ddof=1) / np.sqrt(len(x)), rel_tol=1e-12)
    assert np.allclose(drag(np.zeros(12), .01) + 1, .99 ** (1 / 12))
    assert math.isclose(np.prod(1 + drag(np.zeros(12), .01)), .99)
    fake = pd.DataFrame({s: np.full(12, (i + 1) / 100) for i, s in enumerate(SIGNALS)})
    c, weights = candidates(fake)
    assert np.allclose(c["Mom12m + EarningsSurprise"], .015)
    assert np.allclose(c["Equal four"], .025)
    assert np.allclose(c["Momentum + Value + Quality"], .04)
    idx = index_resamples(20, 6, 50, np.random.default_rng(1))
    assert idx.shape == (50, 20) and idx.min() >= 0 and idx.max() < 20
    print("Engine validation passed: compounding, initial drawdown, HAC variance, multiplicity, costs, sleeve weights, block indices.", flush=True)


def main():
    OUT.mkdir(exist_ok=True)
    validate_engine()
    protocol = json.loads((ROOT / "protocol.json").read_text())
    locked_hash = hashlib.sha256((ROOT / "protocol.json").read_bytes()).hexdigest()
    ff = french_monthly(DATA / "F-F_Research_Data_5_Factors_2x3_CSV.zip")
    mom = french_monthly(DATA / "F-F_Momentum_Factor_CSV.zip")
    ff = ff.join(mom)
    assert "Mom" in ff
    ff["Market"] = ff["Mkt-RF"] + ff["RF"]
    ff = ff.loc["2000-01":"2025-12"]
    assert len(ff) == 312 and not ff.isna().any().any()
    result = {"protocol_sha256": locked_hash, "protocol": protocol, "source_counts": {}, "universes": {}}
    variants = [("value_weighted_quintiles", "PredictorAltPorts_QuintilesVW.parquet", "quintile"),
                ("liquid_original", "PredictorAltPorts_LiqScreen_ME_gt_NYSE20pct.parquet", "liquid_original"),
                ("annual_big_sensitivity_only", "PredictorAltPorts_FF93style.parquet", "annual_big")]
    for universe, path, construction in variants:
        base, counts = sleeves(path, construction)
        gross, weights = candidates(base)
        result["source_counts"][universe] = counts
        result["weights"] = weights
        base.join(ff).to_csv(OUT / (universe + "_inputs.csv"))
        gross.to_csv(OUT / (universe + "_gross_sleeves.csv"))
        print("Evaluating", universe, len(gross), "months", flush=True)
        report = analyze(gross, ff, detailed=universe == "value_weighted_quintiles")
        report["subperiods"] = {}
        for start, end in protocol["subwindows"] + [["2014-01", "2025-12"]]:
            key = start + "_" + end
            report["subperiods"][key] = analyze(gross.loc[start:end], ff, costs=(.01,), detailed=False)
        if universe == "value_weighted_quintiles":
            report["fixed_development_selection"] = fixed_development_selection(gross, ff)
            report["walk_forward"], wf = walk_forward(gross, ff)
            wf.to_csv(OUT / "walk_forward_net_1pct.csv")
            curve = (1 + drag(gross, .01)).cumprod()
            curve["US Market"] = (1 + ff.Market).cumprod()
            curve.to_csv(OUT / "wealth_net_1pct.csv")
        result["universes"][universe] = report
        table = pd.DataFrame(report["cost_scenarios"]["0.01"]).T
        print(table[["cagr", "volatility", "sharpe", "max_month_end_drawdown"]].sort_values("sharpe", ascending=False).round(4).to_string(), flush=True)
        print("Market", report["benchmark"], flush=True)
        (OUT / "results.json").write_text(json.dumps(result, indent=2, allow_nan=False))
    print("COMPLETE", OUT / "results.json", flush=True)


if __name__ == "__main__":
    main()
