#!/usr/bin/env python3
"""Copy the figures the app quotes from the archived result files into docs/evidence-data.js.

The app never types these numbers by hand: tests/test_evidence.cjs compares the generated file
with research/tests/2026-11-14-strategy-audit/files/output/all_strategies.csv.
All values are percentage points per year (one decimal) unless the name says otherwise.
"""
from __future__ import annotations
import argparse, json
from pathlib import Path
import pandas as pd

IDS = """MOM_D10 MOM_BIG OSAP_Mom12m IND_MOM122 IND_MOM122_3M IND_MOM122_12M IND_TREND OSAP_TrendFactor LOWVOL_Q1 OSAP_GP QUAL_BIG
Europe_QUAL Japan_QUAL Emerging_QUAL VAL_Q5 VAL_BIG OSAP_BM INV_Q1 OSAP_AssetGrowth OSAP_EarningsSurprise OSAP_RevenueSurprise
OSAP_EarningsStreak OSAP_MeanRankRevGrowth_GEGENSEITE IND_DIP OSAP_High52_GEGENSEITE STREV_D1 LTREV_D1 T_APP T_SMA200 T_SMA10M
IND_TIMING MIX_QVM MIX_QUAL_MOM IND_APPMIX IND_RAM IND_HIGH52 GEM GTAA5 Emerging_QVM Developed_ex_US_QVM Europe_MOM Emerging_MOM
PICK_10J_TOP10 PICK_15J_TOP10 PICK_20J_TOP10 PICK_15J_TOP10_VEROEFF ALLE_VEROEFFENTLICHTEN FACMOM""".split()
pc = lambda v: None if pd.isna(v) else round(100 * float(v), 1)
r2 = lambda v: None if pd.isna(v) else round(float(v), 2)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True, help="folder with the result files of the study")
    ap.add_argument("--target", required=True, help="docs/evidence-data.js")
    a = ap.parse_args()
    O = Path(a.out)
    df = pd.read_csv(O / "all_strategies.csv").set_index("id")
    s = json.loads((O / "summary.json").read_text())
    rows = {i: {"from": df.at[i, "first"][:4], "to": df.at[i, "last"][:4], "net": pc(df.at[i, "active"]), "gross": pc(df.at[i, "gross_active"]),
                "t": r2(df.at[i, "t"]), "hold": pc(df.at[i, "hold_active"]), "holdFrom": str(df.at[i, "hold_first"])[:4], "holdT": r2(df.at[i, "hold_t"]),
                "recent": pc(df.at[i, "recent_active"]), "win10": None if pd.isna(df.at[i, "win10"]) else round(100 * df.at[i, "win10"]),
                "cagr": pc(df.at[i, "cagr"]), "market": pc(df.at[i, "bench_cagr"]), "maxdd": round(100 * df.at[i, "maxdd"]),
                "marketMaxdd": round(100 * df.at[i, "bench_maxdd"]), "tax": pc(df.at[i, "tax_median_pa"]), "verdict": df.at[i, "verdict"]} for i in IDS}
    c5 = df[df.module == "C5"].copy()
    c5["grp"] = c5.family.str.replace("Echtes Produkt: ", "")
    etf = {g: {"n": int(len(x)), "ahead": int((x.active > 0).sum()), "median": pc(x.active.median())} for g, x in c5.groupby("grp")}
    st = pd.read_csv(O / "exploratory_stocks.csv").set_index("id")
    stocks = {i: {"net": pc(r.active), "t": r2(r.t), "win5": round(100 * r.win5), "cagr": pc(r.cagr), "universe": pc(r.bench_cagr),
                  "vsSpy": pc(r.active_vs_spy), "from": r["first"][:4], "to": r["last"][:4]} for i, r in st.iterrows()}
    se = pd.read_csv(O / "exploratory_sectors.csv").set_index("id")
    sectors = {i: {"net": pc(r.active), "t": r2(r.t), "since2000": pc(r.since2000_active), "last15": pc(r.last15y_active)}
               for i, r in se.iterrows() if i.startswith("IND12_MOM122")}
    em = pd.read_csv(O / "exploratory_emerging.csv")
    cost = em[(em.kind == "Kosten") & (em.name == "Mix QVM")].set_index("variant").active
    fund = em[em.kind == "Echter Fonds"].set_index("name")
    hurdle = pd.read_csv(O / "tax_hurdle.csv")
    hurdle = hurdle[hurdle["from"] == "1963-07"].set_index("turnover_per_year").median_after_tax_gap_pa
    o = s["osap"]
    data = {
        "study": {"id": "2026-11-14-strategy-audit", "date": "2026-11-14", "dataEnd": s["data_end"]["french"],
                  "strategies": s["strategies_evaluated"], "verdicts": s["verdict_counts"], "nominal": s["nominal_p_below_5pct"],
                  "afterHolm": s["criteria_pass_counts"]["K1"]},
        "rows": rows, "etf": etf, "stocks": stocks, "sectors12": sectors,
        "osap": {"signals": o["signals"], "inSample": pc(o["mean_gross_active_insample"]), "afterPublication": pc(o["mean_gross_active_postpub"]),
                 "sharePositiveAfter": round(100 * o["share_positive_gross_postpub"]), "significantInSample": o["insample_net_p_below_5pct"],
                 "significantAfter": o["postpub_net_p_below_5pct"], "significantAfterHolm": o["postpub_net_holm_below_5pct"]},
        "tax": {"turnover30": pc(hurdle[0.3]), "turnover100": pc(hurdle[1.0]), "turnover200": pc(hurdle[2.0])},
        "emerging": {"gross": pc(cost["0.0% p. a."]), "at1": pc(cost["1.0% p. a."]), "at2": pc(cost["2.0% p. a."]),
                     "valueFund": {"net": pc(fund.at["DFEVX gegen VEIEX", "active"]), "t": r2(fund.at["DFEVX gegen VEIEX", "t"]),
                                   "from": fund.at["DFEVX gegen VEIEX", "first"][:4]},
                     "fundsAhead": int((fund.active > 0).sum()), "funds": int(len(fund))},
    }
    body = json.dumps(data, ensure_ascii=False, indent=1, sort_keys=True)
    Path(a.target).write_text(
        "/* Generated by research/tests/2026-11-14-strategy-audit/files/code/export_app_evidence.py from the archived\n"
        "   result files. Percentage points per year unless named otherwise. Do not edit by hand. */\n"
        "(function(root){\n\"use strict\";\nconst data=" + body + ";\n"
        "if(typeof module!==\"undefined\"&&module.exports)module.exports=data;\nroot.StockEvidenceData=data;\n"
        "})(typeof window!==\"undefined\"?window:globalThis);\n")
    print(f"{a.target}: {len(rows)} strategies, {len(stocks)} stock rules, {len(etf)} product groups")


if __name__ == "__main__":
    main()
