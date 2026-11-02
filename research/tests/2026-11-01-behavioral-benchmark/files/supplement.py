"""Independent construction/FX diagnostics, explicitly added after primary run.

These checks address the quarterly/annual refresh conventions discovered in
the source audit. They are not a second search for a winning strategy.
"""
import json
from pathlib import Path
import numpy as np
import pandas as pd
from run_study import ROOT, DATA, OUT, french_monthly, metrics, drag, hac_ols, holm, validate_engine


def main():
    validate_engine()
    original = json.loads((OUT / "results.json").read_text())
    (DATA / "selected_counts.json").write_text(json.dumps(original["source_counts"], indent=2))
    inputs = pd.read_csv(OUT / "value_weighted_quintiles_inputs.csv", index_col=0)
    inputs.index = pd.PeriodIndex(inputs.index, freq="M")
    market = inputs.Market
    rf = inputs.RF
    six = french_monthly(DATA / "6_Portfolios_ME_Prior_12_2_CSV.zip").reindex(inputs.index)
    ten = french_monthly(DATA / "10_Portfolios_Prior_12_2_CSV.zip").reindex(inputs.index)
    raw = pd.DataFrame({"French monthly large top30": six["BIG HiPRIOR"],
                        "French monthly small top30": six["SMALL HiPRIOR"],
                        "French monthly top10": ten["Hi PRIOR"],
                        "French monthly decile9": ten["PRIOR 9"]}, index=inputs.index)
    assert not raw.isna().any().any()
    raw.to_csv(OUT / "independent_monthly_momentum_inputs.csv")
    checks = {"label": "Exploratory independent construction check, added after the primary test; all inspected variants are disclosed.",
              "momentum": {}, "currency": {}}
    for name in raw:
        n = drag(raw[name], .01)
        m = metrics(n, rf, market)
        m["relative_log_hac"] = hac_ols(np.log1p(n) - np.log1p(market))
        checks["momentum"][name] = m
    # Disclose multiplicity across the 14 fixed strategies + all four inspected
    # monthly momentum variants, rather than selecting the highest one silently.
    original_ps = [v["relative_log_hac"]["p"] for v in original["universes"]["value_weighted_quintiles"]["cost_scenarios"]["0.01"].values()]
    extra_ps = [v["relative_log_hac"]["p"] for v in checks["momentum"].values()]
    adjusted = holm(original_ps + extra_ps)
    for name, adj in zip(checks["momentum"], adjusted[-4:]):
        checks["momentum"][name]["relative_log_hac"]["p_holm_all_18"] = float(adj)

    fx = pd.DataFrame(json.loads((DATA / "usd_eur_daily.json").read_text()))
    assert fx.base.eq("USD").all() and fx.quote.eq("EUR").all()
    fx["date"] = pd.to_datetime(fx.date)
    assert fx.date.is_monotonic_increasing and fx.date.is_unique
    fx["month"] = fx.date.dt.to_period("M")
    month_fx = fx.groupby("month").tail(1).set_index("month")
    assert (month_fx.date.dt.to_period("M") == month_fx.index).all()
    change = month_fx.rate.pct_change().reindex(inputs.index)
    assert not change.isna().any()
    month_fx.to_csv(OUT / "usd_eur_month_end_reference.csv")
    net = pd.read_csv(OUT / "wealth_net_1pct.csv", index_col=0)
    net.index = pd.PeriodIndex(net.index, freq="M")
    # Recover simple returns including the first month's initial unit capital.
    r_usd = net / net.shift(1).fillna(1) - 1
    r_eur = (1 + r_usd).mul(1 + change, axis=0) - 1
    assert np.allclose(r_usd["US Market"], market)
    assert np.allclose(r_eur["US Market"], (1 + market) * (1 + change) - 1)
    bm_eur = r_eur["US Market"]
    for name in r_eur:
        # No EUR Sharpe: we do not have an aligned EUR risk-free series. Using
        # FX-converted US T-bills as if risk-free in EUR would be inappropriate.
        logs = np.log1p(r_eur[name])
        wealth = np.r_[1, np.exp(logs.cumsum())]
        m = {"cagr": float(np.expm1(logs.mean() * 12)),
             "volatility": float(r_eur[name].std(ddof=1) * np.sqrt(12)),
             "max_month_end_drawdown": float((wealth / np.maximum.accumulate(wealth) - 1).min())}
        # Common FX cancels exactly in relative monthly gross returns.
        assert np.allclose(np.log1p(r_eur[name]) - np.log1p(bm_eur),
                           np.log1p(r_usd[name]) - np.log1p(market))
        checks["currency"][name] = m
    checks["fx_method"] = "Unhedged USD to EUR; last available reference each calendar month. Frankfurter blended official-source mid-rates, not broker FX fills. EUR Sharpe intentionally omitted. No Austrian taxes."
    (OUT / "supplement.json").write_text(json.dumps(checks, indent=2, allow_nan=False))
    print(json.dumps({"monthly_momentum_cagr": {k: v["cagr"] for k, v in checks["momentum"].items()},
                      "eur_cagr": {k: v["cagr"] for k, v in checks["currency"].items()}}, indent=2))


if __name__ == "__main__":
    main()
