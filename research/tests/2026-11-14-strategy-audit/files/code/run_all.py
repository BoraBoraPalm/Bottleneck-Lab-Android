#!/usr/bin/env python3
"""Run every module of the strategy audit on the frozen input bundle and write all result files."""
from __future__ import annotations
import argparse, json, math, platform, sys, time
from pathlib import Path
import numpy as np
import pandas as pd
sys.path.insert(0, str(Path(__file__).resolve().parent))
import lib, mod_factors, mod_funds, mod_rules  # noqa: E402

DEFAULTS = {"full_start": "1963-07", "holdout_start": "2000-01", "exact": False, "intl_of": "", "app": "", "note": ""}
KEEP = ("id", "module", "family", "app", "label", "cost", "turnover", "exact", "lookback", "rebalance", "note", "intl_of")


class Registry:
    def __init__(self):
        self.items: list[dict] = []

    def add(self, **kw):
        assert kw["id"] not in {e["id"] for e in self.items}, kw["id"]
        self.items.append({**DEFAULTS, **kw})


def evaluate(e: dict) -> dict | None:
    r, m, rf, cost, fs = e["r"].dropna(), e["m"], e["rf"], e["cost"], e["full_start"]
    full = lib.versus(r, m, rf, cost, start=fs)
    if full.get("months", 0) < 36:
        return None
    gross = lib.versus(r, m, rf, 0.0, start=fs)
    whole = lib.versus(r, m, rf, cost)
    hold = lib.versus(r, m, rf, cost, start=e["holdout_start"]) if e["holdout_start"] else full
    recent = lib.versus(r, m, rf, cost, start=str(pd.Period(full["last"], "M") - 179))
    if "tax" in e:
        tax = e["tax"]
    elif "tax_r" in e:
        tr = e["tax_r"]
        tax = lib.tax_windows(tr[tr.index >= pd.Period(fs, "M")] if fs else tr, m, rf, e["turnover"], w=e["w"], cost=0.001)
    else:
        net = (1 + r) * (1 - cost) ** (1 / 12) - 1
        tax = lib.tax_windows(net[net.index >= pd.Period(fs, "M")] if fs else net, m, rf, e["turnover"])
    row = {k: e[k] for k in KEEP}
    row.update({k: full[k] for k in ("first", "last", "months", "cagr", "bench_cagr", "vol", "bench_vol", "sharpe", "bench_sharpe",
                                     "maxdd", "bench_maxdd", "active", "t", "p", "alpha", "t_alpha", "beta", "te",
                                     "win5", "win10", "win20", "win10_recent", "worst10")})
    row.update(gross_active=gross["active"], t_gross=gross["t"], breakeven_cost=gross["breakeven_cost"],
               active_at_2pct=gross["active"] + math.log(0.98) if not e["exact"] else math.nan)
    for tag, v in (("hold", hold), ("recent", recent), ("whole", whole)):
        for k in ("first", "months", "active", "t", "p", "cagr", "bench_cagr", "sharpe", "bench_sharpe", "maxdd", "bench_maxdd", "win10"):
            row[f"{tag}_{k}"] = v.get(k, math.nan)
    row.update({k: tax.get(k, math.nan) for k in ("tax_windows", "tax_median_ratio", "tax_median_pa", "tax_win_share")})
    return row


def verdicts(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["p_holm"], df["p_bh"] = lib.holm(df["p"].values), lib.bh(df["p"].values)
    df["K1"] = (df.active > 0) & (df.p_holm < 0.05)
    df["K2"] = (df.hold_active > 0) & (df.hold_p < 0.05)
    df["K3"] = (df.win10 >= 0.8) & (df.win10_recent >= 0.6)
    df["K4"] = df.recent_active > 0
    abroad = df[df.intl_of != ""].set_index("intl_of")
    k5 = df["id"].map(lambda i: bool(abroad.at[i, "active"] > 0 and abroad.at[i, "p"] < 0.10) if i in abroad.index else None)
    df["K5"] = k5.astype(object)
    df["K6"] = df.tax_median_ratio > 1
    reliable = df.K1 & df.K2 & df.K3 & df.K4 & df.K6 & df.K5.map(lambda v: v is None or bool(v))
    against = (df.gross_active < 0) & (df.t_gross < -1.645)
    hints = df.K1 | (df.K2 & df.K4)
    df["verdict"] = np.select([reliable, against, hints], ["verlässlich", "Evidenz dagegen", "Hinweise, nicht verlässlich"], "nicht belegt")
    df["risk_reducing"] = ((df.sharpe > df.bench_sharpe) & (df.maxdd >= df.bench_maxdd + 0.10)
                           & (df.hold_sharpe > df.hold_bench_sharpe) & (df.hold_maxdd >= df.hold_bench_maxdd + 0.10))
    return df


def tax_hurdle(m: pd.Series, rf: pd.Series) -> pd.DataFrame:
    rows = []
    for label, start in (("1963-07", "1963-07"), ("1927-01", "1927-01")):
        mm = m[m.index >= pd.Period(start, "M")]
        for t in (0.1, 0.3, 0.5, 1.0, 2.0, 4.0, 12.0):
            v = lib.tax_windows(mm, mm, rf, t)
            rows.append({"from": label, "turnover_per_year": t, "windows": v["tax_windows"],
                         "median_after_tax_gap_pa": v["tax_median_pa"], "median_wealth_ratio_20y": v["tax_median_ratio"]})
    return pd.DataFrame(rows)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--supplement", default="")
    a = ap.parse_args()
    D, O = Path(a.data), Path(a.out)
    O.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    reg = Registry()
    info = mod_factors.run(D, reg)
    print(f"factors registered: {len(reg.items)}", flush=True)
    mod_rules.run(D, reg)
    print(f"+ rules: {len(reg.items)}", flush=True)
    finfo = mod_funds.run(D, reg, info["rf"])
    print(f"+ funds: {len(reg.items)}", flush=True)
    rows, skipped = [], []
    for e in reg.items:
        row = evaluate(e)
        (rows.append(row) if row else skipped.append(e["id"]))
    df = verdicts(pd.DataFrame(rows))
    df.to_csv(O / "all_strategies.csv", index=False, float_format="%.6g")
    scan = info["osap_scan"]
    for tag in ("insample", "postpub", "since2000"):
        scan[f"{tag}_p_holm"], scan[f"{tag}_p_bh"] = lib.holm(scan[f"{tag}_p"].values), lib.bh(scan[f"{tag}_p"].values)
    scan.to_csv(O / "osap_scan.csv", index=False, float_format="%.6g")
    hurdle = tax_hurdle(info["market"], info["rf"])
    hurdle.to_csv(O / "tax_hurdle.csv", index=False, float_format="%.6g")
    rets = pd.concat({"US_MARKT": info["market"], "T_BILL": info["rf"], **{e["id"]: e["r"] for e in reg.items}}, axis=1)
    rets.sort_index().to_csv(O / "strategy_returns.csv.gz", float_format="%.6f")
    explore = {}
    if a.supplement and (Path(a.supplement) / "manifest.json").is_file():
        import mod_explore
        explore = mod_explore.run(D, Path(a.supplement), O, info["market"], info["rf"])
    both = scan.dropna(subset=["insample_gross_active", "postpub_gross_active"])
    both = both[both.postpub_months >= 60]
    summary = {
        "strategies_evaluated": int(len(df)), "skipped_too_short": skipped,
        "holm_family_size": int(df.p.notna().sum()),
        "verdict_counts": df.verdict.value_counts().to_dict(),
        "verdict_by_module": {k: v.to_dict() for k, v in df.groupby("module").verdict.value_counts().unstack(fill_value=0).iterrows()},
        "criteria_pass_counts": {k: int(df[k].map(bool).sum()) for k in ("K1", "K2", "K3", "K4", "K6")},
        "nominal_p_below_5pct": int((df.p < 0.05).sum()), "bh_below_5pct": int((df.p_bh < 0.05).sum()),
        "risk_reducing": df.loc[df.risk_reducing, "id"].tolist(),
        "osap": {"signals": int(len(scan)), "missing_app_signals": info["osap_missing_app_signals"],
                 "with_both_periods": int(len(both)),
                 "mean_gross_active_insample": float(both.insample_gross_active.mean()),
                 "mean_gross_active_postpub": float(both.postpub_gross_active.mean()),
                 "share_positive_gross_postpub": float((both.postpub_gross_active > 0).mean()),
                 "postpub_net_p_below_5pct": int((scan.postpub_p < 0.05).sum()),
                 "postpub_net_holm_below_5pct": int((scan.postpub_p_holm < 0.05).sum()),
                 "insample_net_p_below_5pct": int((scan.insample_p < 0.05).sum())},
        "funds": {k: v for k, v in finfo.items() if k.startswith("etf_")},
        "c4_vs_world": {k: {x: v.get(x) for x in ("first", "last", "cagr", "bench_cagr", "active", "t", "maxdd", "bench_maxdd")} for k, v in finfo["c4_vs_world"].items()},
        "c4_vs_6040": {k: {x: v.get(x) for x in ("first", "last", "cagr", "bench_cagr", "active", "t", "maxdd", "bench_maxdd")} for k, v in finfo["c4_vs_6040"].items()},
        "data_end": {"french": str(info["market"].index[-1])}, "exploratory": explore,
        "environment": {"python": platform.python_version(), "numpy": np.__version__, "pandas": pd.__version__},
        "runtime_seconds": round(time.time() - t0, 1),
    }
    (O / "summary.json").write_text(json.dumps(summary, indent=1, ensure_ascii=False, default=str))
    print(json.dumps({k: summary[k] for k in ("strategies_evaluated", "verdict_counts", "criteria_pass_counts",
                                              "nominal_p_below_5pct", "bh_below_5pct", "runtime_seconds")}, ensure_ascii=False))


if __name__ == "__main__":
    main()
