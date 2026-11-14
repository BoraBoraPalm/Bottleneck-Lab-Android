"""Modules A, B and C3: published long-only portfolios, the signal search and factor mixes."""
from __future__ import annotations
import math
from pathlib import Path
import numpy as np
import pandas as pd
import lib

COST = {"m": 0.010, "q": 0.005, "a": 0.003, "r": 0.030}     # yearly haircut by re-formation rhythm
TURN = {"m": 2.0, "q": 1.0, "a": 0.3, "r": 12.0}            # yearly turnover assumed in the tax model
REB = {"m": "monatlich", "q": "viertel-/halbjährlich", "a": "jährlich (Juni)", "r": "monatlich"}

# id, French file, column tokens, label, app strategy, rhythm, small caps, signal lookback
SLEEVES = [
    ("MOM_D10", "10_Portfolios_Prior_12_2", ("HIPRIOR",), "Momentum 12–2: oberstes Zehntel", "momentum", "m", False, "12 Monate ohne den letzten"),
    ("MOM_BIG", "6_Portfolios_ME_Prior_12_2", ("BIG", "HIPRIOR"), "Momentum 12–2: große Werte, oberes Drittel", "momentum", "m", False, "12 Monate ohne den letzten"),
    ("MOM_SMALL", "6_Portfolios_ME_Prior_12_2", ("SMALL", "HIPRIOR"), "Momentum 12–2: Nebenwerte, oberes Drittel", "momentum", "m", True, "12 Monate ohne den letzten"),
    ("VAL_BIG", "6_Portfolios_2x3", ("BIG", "HIBM"), "Value (Buchwert/Kurs): große Werte, oberes Drittel", "value", "a", False, "Jahresabschluss"),
    ("VAL_Q5", "Portfolios_Formed_on_BE-ME", ("HI20",), "Value (Buchwert/Kurs): oberstes Fünftel", "value", "a", False, "Jahresabschluss"),
    ("VAL_SMALL", "6_Portfolios_2x3", ("SMALL", "HIBM"), "Value (Buchwert/Kurs): Nebenwerte", "value", "a", True, "Jahresabschluss"),
    ("EP_Q5", "Portfolios_Formed_on_E-P", ("HI20",), "Gewinnrendite (Gewinn/Kurs): oberstes Fünftel", "value", "a", False, "Jahresabschluss"),
    ("CFP_Q5", "Portfolios_Formed_on_CF-P", ("HI20",), "Cashflow-Rendite: oberstes Fünftel", "value", "a", False, "Jahresabschluss"),
    ("DP_Q5", "Portfolios_Formed_on_D-P", ("HI20",), "Dividendenrendite: oberstes Fünftel", "", "a", False, "12 Monate Dividenden"),
    ("QUAL_BIG", "6_Portfolios_ME_OP_2x3", ("BIG", "HIOP"), "Profitabilität: große Werte, oberes Drittel", "quality", "a", False, "Jahresabschluss"),
    ("QUAL_Q5", "Portfolios_Formed_on_OP", ("HI20",), "Profitabilität: oberstes Fünftel", "quality", "a", False, "Jahresabschluss"),
    ("QUAL_SMALL", "6_Portfolios_ME_OP_2x3", ("SMALL", "HIOP"), "Profitabilität: Nebenwerte", "quality", "a", True, "Jahresabschluss"),
    ("INV_BIG", "6_Portfolios_ME_INV_2x3", ("BIG", "LOINV"), "Geringes Bilanzwachstum: große Werte", "investment", "a", False, "Jahresabschluss"),
    ("INV_Q1", "Portfolios_Formed_on_INV", ("LO20",), "Geringes Bilanzwachstum: unterstes Fünftel", "investment", "a", False, "Jahresabschluss"),
    ("LOWVOL_Q1", "Portfolios_Formed_on_VAR", ("LO20",), "Geringe Schwankung (60 Tage): ruhigstes Fünftel", "lowRisk", "m", False, "60 Handelstage"),
    ("LOWRESVOL_Q1", "Portfolios_Formed_on_RESVAR", ("LO20",), "Geringe Restschwankung: ruhigstes Fünftel", "lowRisk", "m", False, "60 Handelstage"),
    ("LOWBETA_Q1", "Portfolios_Formed_on_BETA", ("LO20",), "Niedriges Beta: unterstes Fünftel", "lowRisk", "a", False, "5 Jahre"),
    ("SMALL_Q1", "Portfolios_Formed_on_ME", ("LO20",), "Nebenwerte: kleinstes Fünftel", "", "a", True, "Börsenwert"),
    ("BUYBACK", "Portfolios_Formed_on_NI", ("<0",), "Netto-Aktienrückkäufe", "", "a", False, "1 Jahr"),
    ("LOWISS_Q1", "Portfolios_Formed_on_NI", ("LO20",), "Geringe Aktienausgabe: unterstes Fünftel", "", "a", False, "1 Jahr"),
    ("LOWACC_Q1", "Portfolios_Formed_on_AC", ("LO20",), "Niedrige Accruals: unterstes Fünftel", "", "a", False, "Jahresabschluss"),
    ("STREV_D1", "10_Portfolios_Prior_1_0", ("LOPRIOR",), "Kurzfrist-Verlierer (1 Monat): unterstes Zehntel", "sander", "r", False, "1 Monat"),
    ("LTREV_D1", "10_Portfolios_Prior_60_13", ("LOPRIOR",), "Langfrist-Verlierer (5 Jahre): unterstes Zehntel", "sander", "m", False, "60 Monate ohne die letzten 12"),
]
MIXES = {
    "MIX_QVM": (["QUAL_BIG", "VAL_BIG", "MOM_BIG"], "Mix Quality + Value + Momentum (große Werte)"),
    "MIX_QVML": (["QUAL_BIG", "VAL_BIG", "MOM_BIG", "LOWVOL_Q1"], "Mix Quality + Value + Momentum + geringe Schwankung"),
    "MIX_MOM_LOWVOL": (["MOM_BIG", "LOWVOL_Q1"], "Mix Momentum + geringe Schwankung"),
    "MIX_QUAL_MOM": (["QUAL_BIG", "MOM_BIG"], "Mix Quality + Momentum"),
    "MIX_VAL_MOM": (["VAL_BIG", "MOM_BIG"], "Mix Value + Momentum"),
    "MIX_5": (["QUAL_BIG", "VAL_BIG", "MOM_BIG", "INV_BIG", "LOWVOL_Q1"], "Fünfer-Mix (Quality, Value, Momentum, Bilanzwachstum, Schwankung)"),
}
REGIONS = {"Developed": "Industrieländer", "Developed_ex_US": "Industrieländer ohne USA", "Europe": "Europa",
           "Japan": "Japan", "Asia_Pacific_ex_Japan": "Asien-Pazifik ohne Japan", "North_America": "Nordamerika",
           "Emerging": "Schwellenländer"}
INTL = [("VAL", "BE-ME", ("BIG", "HIBM"), "Value", "a", "VAL_BIG", "value"),
        ("QUAL", "OP", ("BIG", "HIOP"), "Profitabilität", "a", "QUAL_BIG", "quality"),
        ("INV", "INV", ("BIG", "LOINV"), "Geringes Bilanzwachstum", "a", "INV_BIG", "investment"),
        ("MOM", "Prior_12_2", ("BIG", "HIPRIOR"), "Momentum 12–2", "m", "MOM_BIG", "momentum")]
# Module A: nearest published portfolio per app strategy (declared in the protocol).
APP_MAP = {"Mom12m": "momentum", "IdioVol3F": "lowRisk", "RealizedVol": "lowRisk", "MaxRet": "lowRisk",
           "TrendFactor": "trend", "High52": "trend", "Mom6m": "trend",
           "LRreversal": "sander", "MRreversal": "sander", "STreversal": "sander",
           "RevenueSurprise": "growth", "NumEarnIncrease": "growth", "EarningsStreak": "growth", "MeanRankRevGrowth": "growth",
           "GP": "quality", "BM": "value", "EarningsSurprise": "earnings", "AnnouncementReturn": "earnings", "REV6": "earnings",
           "AssetGrowth": "investment"}
OPPOSITE = {"High52": ("sander", "Weit unter dem 52-Wochen-Hoch (unterstes Fünftel, Gegenseite von High52)"),
            "MeanRankRevGrowth": ("growth", "Höchstes Umsatzwachstum über 5 Jahre (Gegenseite von MeanRankRevGrowth)")}


def us_market(D: Path):
    ff = lib.french_table(D / "french/F-F_Research_Data_Factors_CSV.zip")
    return (ff["Mkt-RF"] + ff["RF"]).rename("m"), ff["RF"].rename("rf")


def sma_filter(m: pd.Series, months: int = 10) -> pd.Series:
    """1 in month t+1 when the market total-return index closed month t above its 10-month average."""
    idx = (1 + m).cumprod()
    sig = (idx > idx.rolling(months).mean()).astype(float)
    sig[idx.rolling(months).mean().isna()] = np.nan
    return sig.shift(1)


def run(D: Path, reg) -> dict:
    m, rf = us_market(D)
    info = {}
    # ---------------- C3: French sleeves
    sl, meta = {}, {}
    for sid, fname, tok, label, app, cls, small, look in SLEEVES:
        tab = lib.french_table(D / f"french/{fname}_CSV.zip", "monthly")
        sl[sid] = lib.pick(tab, *tok).dropna()
        cost = COST[cls] * (2 if small else 1)
        meta[sid] = (cost, TURN[cls])
        reg.add(id=sid, module="C3", family="Faktor-Portfolio (French)", app=app, label=label, r=sl[sid], m=m, rf=rf,
                cost=cost, turnover=TURN[cls], lookback=look, rebalance=REB[cls],
                note="wertgewichtet, alle US-Börsen" + ("; Nebenwerte: doppelte Kosten" if small else ""))
    net = {k: (1 + v) * (1 - meta[k][0]) ** (1 / 12) - 1 for k, v in sl.items()}
    for mid, (parts, label) in MIXES.items():
        r = pd.concat([sl[p] for p in parts], axis=1).dropna().mean(axis=1)
        reg.add(id=mid, module="C3", family="Faktor-Mix", app="mix", label=label, r=r, m=m, rf=rf,
                cost=float(np.mean([meta[p][0] for p in parts])), turnover=float(np.mean([meta[p][1] for p in parts])),
                lookback="je Baustein", rebalance="monatlich auf gleiche Anteile", note="Mix aus Teilportfolios, keine Schnittmenge")
    w = sma_filter(m)
    for tid, base, label in (("TF_MOM", ["MOM_BIG"], "Momentum (große Werte) nur über der 10-Monats-Linie des Marktes"),
                             ("TF_QVM", MIXES["MIX_QVM"][0], "Mix Quality + Value + Momentum nur über der 10-Monats-Linie")):
        risky = pd.concat([net[p] for p in base], axis=1).dropna().mean(axis=1)
        df = pd.concat([risky, rf, w], axis=1, keys=["r", "rf", "w"]).dropna()
        r = df.w * df.r + (1 - df.w) * df.rf - 0.001 * df.w.diff().abs().fillna(0)
        reg.add(id=tid, module="C3", family="Faktor-Mix mit Trendfilter", app="mix", label=label, r=r, m=m, rf=rf, cost=0.0,
                turnover=float(np.mean([meta[p][1] for p in base])), tax_r=df.r, w=df.w, exact=True,
                lookback="10 Monate (Markt)", rebalance="monatliche Prüfung",
                note=f"{int(df.w.diff().abs().sum())} Wechsel; im Markt {df.w.mean():.0%} der Monate")
    six = ["QUAL_BIG", "VAL_BIG", "MOM_BIG", "INV_BIG", "LOWVOL_Q1", "SMALL_Q1"]
    S = pd.concat([net[p] for p in six], axis=1, keys=six).dropna()
    past = np.log1p(S).rolling(12).sum().shift(1)
    top = past.rank(axis=1, ascending=False) <= 2
    W = top.div(top.sum(axis=1), axis=0).where(past.notna().all(axis=1))
    turn = W.diff().abs().sum(axis=1) / 2
    fm = ((W * S).sum(axis=1) - 0.002 * turn.fillna(0))[W.notna().all(axis=1)]
    reg.add(id="FACMOM", module="C3", family="Faktor-Mix", app="mix", label="Faktor-Momentum: die 2 von 6 Bausteinen mit der besten 12-Monats-Rendite",
            r=fm, m=m, rf=rf, cost=0.0, turnover=float(np.mean([meta[p][1] for p in six]) + 12 * turn.mean()), exact=True,
            lookback="12 Monate", rebalance="monatlich", note=f"mittlerer Bausteinwechsel {12 * turn.mean():.0%} p. a.")
    # ---------------- C3: regions
    for reg_key, reg_name in REGIONS.items():
        em = reg_key == "Emerging"
        f5 = lib.french_table(D / f"french/{reg_key}_5_Factors_CSV.zip")
        rm, rrf = (f5["Mkt-RF"] + f5["RF"]).dropna(), f5["RF"]
        prefix = "Emerging_Markets_6_Portfolios_ME_" if em else f"{reg_key}_6_Portfolios_ME_"
        parts = {}
        for key, fpart, tok, name, cls, us_id, app in INTL:
            s = lib.pick(lib.french_table(D / f"french/{prefix}{fpart}_CSV.zip", "monthly"), *tok).dropna()
            parts[key] = s
            reg.add(id=f"{reg_key}_{key}", module="C3-Regionen", family=f"Region: {reg_name}", app=app, label=f"{name}, große Werte – {reg_name}",
                    r=s, m=rm, rf=rrf, cost=COST[cls], turnover=TURN[cls], full_start=None,
                    intl_of=us_id if reg_key == "Developed_ex_US" else "", lookback="wie USA", rebalance=REB[cls], note="French-Regionenportfolio in USD")
        mix = pd.concat([parts[k] for k in ("QUAL", "VAL", "MOM")], axis=1).dropna().mean(axis=1)
        reg.add(id=f"{reg_key}_QVM", module="C3-Regionen", family=f"Region: {reg_name}", app="mix", label=f"Mix Quality + Value + Momentum – {reg_name}",
                r=mix, m=rm, rf=rrf, cost=(2 * COST["a"] + COST["m"]) / 3, turnover=(2 * TURN["a"] + TURN["m"]) / 3, full_start=None,
                intl_of="MIX_QVM" if reg_key == "Developed_ex_US" else "", lookback="je Baustein", rebalance="monatlich auf gleiche Anteile", note="")
    # ---------------- A + B: Open Source Asset Pricing
    L = pd.read_parquet(D / "osap/long_vw.parquet") / 100.0      # source returns are in percent
    L.index = pd.PeriodIndex(L.index, freq="M")
    Sh = pd.read_parquet(D / "osap/short_vw.parquet") / 100.0
    Sh.index = pd.PeriodIndex(Sh.index, freq="M")
    assert L.abs().max().max() < 3 and (L.min().min() > -1), "unexpected return units"
    N = pd.read_parquet(D / "osap/nlong_vw.parquet")
    doc = pd.read_csv(D / "osap/SignalDoc.csv", encoding="utf-8-sig").set_index("Acronym")
    costs, turns, pub, rows = {}, {}, {}, []
    for sig in L.columns:
        d = doc.loc[sig]
        pp = float(d["Portfolio Period"]) if pd.notna(d["Portfolio Period"]) else 1.0
        cls = "r" if sig == "STreversal" else "m" if pp <= 1 else "q" if pp <= 6 else "a"
        year = int(d["Year"])
        costs[sig], turns[sig], pub[sig] = COST[cls], TURN[cls], year
        common = dict(module="B", family="Veröffentlichtes Signal (OSAP)", m=m, rf=rf, cost=COST[cls], turnover=TURN[cls],
                      holdout_start=f"{max(2000, year + 1)}-01", lookback=str(d["Cat.Economic"]), rebalance=REB[cls])
        reg.add(id="OSAP_" + sig, app=APP_MAP.get(sig, ""), label=f"{d['LongDescription']} ({d['Authors']} {year})", r=L[sig].dropna(),
                note=f"oberstes wertgewichtetes Fünftel; Median {N[sig].median():.0f} Aktien", **common)
        if sig in OPPOSITE:
            reg.add(id=f"OSAP_{sig}_GEGENSEITE", app=OPPOSITE[sig][0], label=OPPOSITE[sig][1], r=Sh[sig].dropna(),
                    note="unterstes wertgewichtetes Fünftel", **common)
        row = {"signal": sig, "authors": d["Authors"], "year": year, "description": d["LongDescription"], "category": d["Cat.Economic"],
               "rebalance_months": pp, "cost": COST[cls], "median_stocks": float(N[sig].median())}
        for tag, a, b in (("insample", f"{int(d['SampleStartYear'])}-01", f"{int(d['SampleEndYear'])}-12"),
                          ("postpub", f"{year + 1}-01", None), ("since2000", "2000-01", None)):
            v = lib.versus(L[sig].dropna(), m, rf, COST[cls], start=a, end=b)
            for k in ("months", "gross_active", "active", "t", "p"):
                row[f"{tag}_{k}"] = v.get(k, math.nan)
        rows.append(row)
    scan = pd.DataFrame(rows)
    info["osap_scan"] = scan
    info["osap_missing_app_signals"] = sorted(set(APP_MAP) - set(L.columns))
    # ---------------- B2: pick the past winners, then hold them for a year
    A = np.log1p(L).sub(np.log1p(m.reindex(L.index)), axis=0)
    years = range(1980, int(L.index[-1].year) + 1)

    def walk(lb: int, n: int, published_only: bool) -> tuple[pd.Series, float, float, float]:
        out, cs, ts, kept = [], [], [], []
        prev: set = set()
        for y in years:
            win = A[(A.index.year >= y - lb) & (A.index.year < y)]
            ok = win.columns[win.notna().sum() >= 0.9 * lb * 12]
            if published_only:
                ok = [c for c in ok if pub[c] < y]
            sc = (win[ok].mean() / win[ok].std(ddof=1) * np.sqrt(win[ok].notna().sum())).dropna().sort_values(ascending=False)
            pickd = list(sc.index[:n])
            if len(pickd) < n:
                continue
            out.append(L.loc[L.index.year == y, pickd].mean(axis=1))
            cs.append(np.mean([costs[c] for c in pickd]))
            ts.append(np.mean([turns[c] for c in pickd]))
            if prev:
                kept.append(len(prev & set(pickd)) / n)
            prev = set(pickd)
        return pd.concat(out).dropna(), float(np.mean(cs)), float(np.mean(ts)), float(1 - np.mean(kept))

    for lb in (10, 15, 20):
        for n in (5, 10, 20):
            r, c, t, repl = walk(lb, n, False)
            reg.add(id=f"PICK_{lb}J_TOP{n}", module="B", family="Vergangene Sieger auswählen", app="search",
                    label=f"Jedes Jahr die {n} Signale mit dem besten t-Wert der letzten {lb} Jahre", r=r, m=m, rf=rf,
                    cost=c + 0.002 * repl, turnover=t + repl, full_start="1980-01", lookback=f"{lb} Jahre", rebalance="jährliche Auswahl",
                    note=f"im Mittel {repl:.0%} der Signale je Jahr ersetzt; alle Signale, auch vor ihrer Veröffentlichung")
    r, c, t, repl = walk(15, 10, True)
    reg.add(id="PICK_15J_TOP10_VEROEFF", module="B", family="Vergangene Sieger auswählen", app="search",
            label="Wie oben (15 Jahre, 10 Signale), nur damals schon veröffentlichte Signale", r=r, m=m, rf=rf, cost=c + 0.002 * repl,
            turnover=t + repl, full_start="1980-01", lookback="15 Jahre", rebalance="jährliche Auswahl", note=f"im Mittel {repl:.0%} je Jahr ersetzt")
    allpub = pd.concat([L.loc[L.index.year == y, [c for c in L.columns if pub[c] < y]].mean(axis=1) for y in years]).dropna()
    reg.add(id="ALLE_VEROEFFENTLICHTEN", module="B", family="Vergangene Sieger auswählen", app="search",
            label="Alle bereits veröffentlichten Signale gleichgewichtet", r=allpub, m=m, rf=rf, cost=float(np.mean(list(costs.values()))),
            turnover=float(np.mean(list(turns.values()))), full_start="1980-01", lookback="–", rebalance="monatlich", note="")
    info["market"], info["rf"] = m, rf
    return info
