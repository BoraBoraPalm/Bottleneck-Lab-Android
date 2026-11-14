"""Exploratory add-ons E (emerging markets) and S (the app's own rules on single stocks); see protocol."""
from __future__ import annotations
import json
from pathlib import Path
import numpy as np
import pandas as pd
import lib

FEE_STOCK = 0.002       # per side
KNOWN_EVENTS = ("1987-10", "2008-10", "2008-11", "2020-03")
EM_GROUPS = {"Value": "DFEVX FNDE PXH AVES 5MVL.DE PSRM.DE", "Dividende": "DEM DGS EDIV WTEI.DE", "Momentum": "EEMO",
             "Mehrfaktor": "EMGF QEMM TLTE JPEM GEM", "Geringe Schwankung": "EEMV EUNZ.DE",
             "Breit mit Faktorneigung": "DFCEX AVEM", "Kontrolle (breiter Markt)": "DFEMX"}
KEYS = ("first", "last", "months", "cagr", "bench_cagr", "active", "t", "p", "maxdd", "bench_maxdd", "win5")


def emerging(D: Path, S: Path, rf: pd.Series) -> tuple[pd.DataFrame, dict]:
    f5 = lib.french_table(D / "french/Emerging_5_Factors_CSV.zip")
    rm, rrf = (f5["Mkt-RF"] + f5["RF"]).dropna(), f5["RF"]
    part = lambda f, *tok: lib.pick(lib.french_table(D / f"french/Emerging_Markets_6_Portfolios_ME_{f}_CSV.zip", "monthly"), *tok).dropna()
    parts = {"Value": part("BE-ME", "BIG", "HIBM"), "Quality": part("OP", "BIG", "HIOP"), "Momentum": part("Prior_12_2", "BIG", "HIPRIOR")}
    parts["Mix QVM"] = pd.concat(parts.values(), axis=1).dropna().mean(axis=1)
    rows = []
    for name, s in parts.items():
        for c in (0.0, 0.005, 0.01, 0.015, 0.02):
            v = lib.versus(s, rm, rrf, c)
            rows.append({"kind": "Kosten", "name": name, "variant": f"{c:.1%} p. a.", **{k: v.get(k) for k in KEYS}})
        for a, b in (("1991-07", "1999-12"), ("2000-01", "2009-12"), ("2010-01", "2019-12"), ("2020-01", None)):
            v = lib.versus(s, rm, rrf, 0.0, start=a, end=b)
            rows.append({"kind": "Zeitraum, vor Kosten", "name": name, "variant": f"{a[:4]}–{(b or v.get('last', ''))[:4]}", **{k: v.get(k) for k in KEYS}})
    Y = pd.read_csv(S / "em_monthly_returns.csv", index_col=0)
    Y.index = pd.PeriodIndex(Y.index, freq="M")
    audit = json.loads((S / "em_audit.json").read_text())
    notes = {"missing": [s for s, a in audit.items() if "error" in a], "excluded": []}

    def start_of(sym):
        a = audit.get(sym, {})
        if "first" not in a or sym not in Y.columns:
            return None
        st = pd.Period(a["first"][:7], "M") + 7
        late = [d for d, v in a.get("moves_over_12pct", []) if abs(v) > 0.20 and pd.Period(d[:7], "M") >= st and d[:7] not in KNOWN_EVENTS]
        if late:
            notes["excluded"].append(f"{sym}: {late[0]}")
            return None
        return st

    zero = pd.Series(0.0, Y.index)
    for group, syms in EM_GROUPS.items():
        for sym in syms.split():
            bench = "IS3N.DE" if sym.endswith(".DE") else "VEIEX"
            s0, b0 = start_of(sym), start_of(bench)
            if s0 is None or b0 is None:
                continue
            r = Y[sym].dropna()
            v = lib.versus(r[r.index >= max(s0, b0)], Y[bench], zero if bench.endswith(".DE") else rf)
            if v.get("months", 0) >= 36:
                rows.append({"kind": "Echter Fonds", "name": f"{sym} gegen {bench}", "variant": group, **{k: v.get(k) for k in KEYS}})
            else:
                notes.setdefault("too_short", []).append(sym)
    return pd.DataFrame(rows), notes


def stocks(D: Path, S: Path, rf: pd.Series) -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    P = {}
    for f in ("px", "mom", "vol", "sma", "dd"):
        P[f] = pd.read_parquet(S / f"stock_{f}.parquet").astype("float64")
        P[f].index = pd.PeriodIndex(P[f].index, freq="M")
    px = P["px"]
    months = px.index[px.index >= pd.Period("2010-12", "M")]
    px, mom, vol, sma, dd = (P[f].reindex(months) for f in ("px", "mom", "vol", "sma", "dd"))
    mem = pd.read_csv(S / "sp500_membership.csv.gz")
    mem["m"] = pd.PeriodIndex(pd.to_datetime(mem.date), freq="M")
    last = mem.groupby("m").tickers.last().reindex(pd.period_range(mem.m.min(), months[-1], freq="M")).ffill()
    M = pd.DataFrame(False, index=months, columns=px.columns)
    listed = {}
    for m in months:
        names = set(last[m].split(","))
        listed[m] = len(names)
        M.loc[m, [c for c in px.columns if c in names]] = True
    full_px = P["px"]
    nxt = (full_px.shift(-1) / full_px - 1).reindex(months)
    gone = px.notna() & nxt.isna()
    ret = nxt.where(~gone, 0.0)                      # no later price: counted as flat, see notes
    E = M & px.notna() & mom.notna() & vol.notna() & sma.notna()
    audit = json.loads((S / "stock_audit.json").read_text())
    glitch = [t for t in px.columns if audit.get(t, {}).get("max_abs_daily_move", 0) > 2.0]   # reused tickers / bad ticks
    E[glitch] = False
    # ---- annual SEC facts, usable 120 days after the fiscal year end and for at most 550 days
    have_facts = (S / "sec_frames.parquet").is_file()
    by_cik, cik_map = {}, {}
    if have_facts:
        facts = pd.read_parquet(S / "sec_frames.parquet")
        facts["end"] = pd.to_datetime(facts["end"])
        dur = facts[facts.concept != "Assets"].copy()
        dur = dur[(dur.end - pd.to_datetime(dur.start)).dt.days.between(340, 380)]
        wide = dur.pivot_table(index=["cik", "end"], columns="concept", values="val", aggfunc="first")
        rev_cols = [c for c in ("Revenues", "RevenueFromContractWithCustomerExcludingAssessedTax",
                                "RevenueFromContractWithCustomerIncludingAssessedTax", "SalesRevenueNet") if c in wide.columns]
        wide["rev"] = wide[rev_cols].bfill(axis=1).iloc[:, 0]
        wide = wide.join(facts[facts.concept == "Assets"].groupby(["cik", "end"]).val.first().rename("assets")).reset_index().sort_values(["cik", "end"])
        near = wide.groupby("cik").end.diff().dt.days.between(350, 380)
        wide["rev_prev"] = wide.groupby("cik").rev.shift().where(near)
        wide["assets_prev"] = wide.groupby("cik").assets.shift().where(near)
        wide["avail"] = (wide.end + pd.Timedelta(days=120)).dt.to_period("M")
        wide["margin"] = wide.NetIncomeLoss / wide.rev.where(wide.rev > 0)
        wide["growth"] = wide.rev / wide.rev_prev.where(wide.rev_prev > 0) - 1
        wide["gpa"] = wide.get("GrossProfit") / wide.assets.where(wide.assets > 0)
        wide["ag"] = wide.assets / wide.assets_prev.where(wide.assets_prev > 0) - 1
        wide = wide.rename(columns={"NetIncomeLoss": "ni", "NetCashProvidedByUsedInOperatingActivities": "cfo"})
        cik_map = json.loads((S / "cik_map.json").read_text())
        by_cik = {c: g.drop_duplicates("avail", keep="last").set_index("avail") for c, g in wide.groupby("cik")}
    F = {k: pd.DataFrame(np.nan, index=months, columns=px.columns) for k in ("ni", "cfo", "margin", "growth", "gpa", "ag")}
    for t in px.columns:
        g = by_cik.get(cik_map.get(t))
        if g is None:
            continue
        for k in F:
            F[k][t] = g[k].reindex(months, method="ffill", limit=14).values
    # ---- rules
    dip = (dd >= -0.55) & (dd <= -0.15)
    qual = (F["ni"] > 0) & (F["cfo"] > 0) & (F["margin"] >= 0.03) & (F["growth"] >= -0.10)
    score = (0.5 * 100 * (dd.abs() - 0.15) / 0.40 + 0.25 * 100 * ((F["margin"] - 0.03) / 0.17).clip(0, 1)
             + 0.25 * 100 * ((F["growth"] + 0.10) / 0.35).clip(0, 1))
    pct = lambda X, base=E: X.where(base).rank(axis=1, pct=True)
    top = lambda X, frac, base=E: pct(X, base) >= 1 - frac
    hasf = E & F["gpa"].notna()
    rules = {
        "S_SANDER": (dip & qual, "Hoch-Tief-Mut wie in der App: alle Treffer", (1, 12)),
        "S_SANDER_TOP10": ((score.where(E & dip & qual).rank(axis=1, ascending=False, method="first") <= 10), "Hoch-Tief-Mut: die zehn höchsten App-Scores", (1,)),
        "S_DIP": (dip, "Nur Kursteil: 15–55 % unter dem 252-Tage-Hoch", (1,)),
        "S_QUALFILTER": (qual, "Nur Qualitätsteil: Gewinn, Cashflow, Marge, Umsatz", (1,)),
        "S_MOM": (top(mom, 0.1), "Momentum 12–2: oberstes Zehntel", (1, 12)),
        "S_LOWVOL": (top(-vol, 0.1), "Geringe Schwankung: ruhigstes Zehntel", (1,)),
        "S_TREND": (top(sma, 0.1), "Abstand zur 200-Tage-Linie: oberstes Zehntel", (1,)),
        "S_HIGH52": (top(dd, 0.1), "Nähe zum 52-Wochen-Hoch: oberstes Zehntel", (1,)),
        "S_RAM": (top(mom / vol, 0.1), "Momentum je Schwankung: oberstes Zehntel", (1,)),
        "S_APPMIX": (top((pct(mom) + pct(sma) + pct(-vol)) / 3, 0.1), "App-Mix Momentum + Trend + Schwankung: oberstes Zehntel", (1,)),
        "S_GPA": (top(F["gpa"], 0.2, hasf), "Bruttogewinn/Bilanzsumme: oberstes Fünftel", (1, 12)),
        "S_LOWAG": (top(-F["ag"], 0.2, E & F["ag"].notna()), "Geringstes Bilanzwachstum: unterstes Fünftel", (1,)),
        "S_QUAL_MOM": (top((pct(F["gpa"], hasf) + pct(mom, hasf)) / 2, 0.1, hasf), "Quality + Momentum (Rangmittel): oberstes Zehntel", (1,)),
    }
    sector_file = S / "sectors.json"
    if sector_file.is_file():
        sector = pd.Series(json.loads(sector_file.read_text())).reindex(px.columns)
        secmom = pd.DataFrame(np.nan, index=months, columns=px.columns)
        for name in sector.dropna().unique():
            cols = sector.index[sector == name]
            inside = mom[cols].where(E[cols])
            secmom[cols] = np.repeat(inside.median(axis=1).where(inside.notna().sum(axis=1) >= 8).values[:, None], len(cols), axis=1)
        hass = E & secmom.notna()
        best3 = secmom.where(hass).rank(axis=1, method="dense", ascending=False) <= 3
        rules["S_SECTOR3"] = (best3 & hass, "Branchen-Momentum: alle Aktien der 3 stärksten von 11 Sektoren", (1, 3))
        rules["S_SECTOR_MOM"] = (top((pct(mom, hass) + pct(secmom, hass)) / 2, 0.1, hass),
                                 "Momentum + Branchen-Momentum (Rangmittel wie im App-Mixer): oberstes Zehntel", (1, 3, 12))
    n_all = E.sum(axis=1)
    W_all = E.div(n_all, axis=0).astype(float)
    ewu = (W_all * ret).sum(axis=1)
    hold_index = months + 1
    spy = pd.read_csv(D / "yahoo/monthly_returns.csv", index_col=0)["SPY"]
    spy.index = pd.PeriodIndex(spy.index, freq="M")
    bench = pd.Series(ewu.values, hold_index).iloc[:-1]
    rows = []
    needs_facts = {"S_SANDER", "S_SANDER_TOP10", "S_QUALFILTER", "S_GPA", "S_LOWAG", "S_QUAL_MOM"}
    for key, (mask, label, freqs) in rules.items():
        if key in needs_facts and not have_facts:
            continue
        for f in freqs:
            sel = (mask & E)
            if f > 1:
                sel = sel.astype(float).where(pd.Series(months.month % f == 0, months), axis=0).ffill().fillna(0).astype(bool) & px.notna()
            n = sel.sum(axis=1)
            W = sel.div(n.where(n > 0), axis=0).astype(float).fillna(0.0)
            W[n == 0] = W_all[n == 0]
            turn = W.diff().abs().sum(axis=1).fillna(0) / 2
            r = pd.Series(((W * ret).sum(axis=1) - 2 * FEE_STOCK * turn).values, hold_index).iloc[:-1]
            if f > 1:
                r = r[r.index >= pd.Period("2011-01", "M")]
            a, b = lib.versus(r, bench, rf), lib.versus(r, spy, rf)
            rows.append({"id": key if f == 1 else f"{key}_{f}M", "label": label + {1: "", 3: ", vierteljährliche Auswahl", 12: ", jährliche Auswahl"}[f],
                         "avg_names": float(n[n > 0].mean()) if (n > 0).any() else 0.0, "months_without_names": int((n == 0).sum()),
                         "turnover_pa": float(12 * turn.mean()), **{k: a.get(k) for k in KEYS},
                         "sharpe": a.get("sharpe"), "bench_sharpe": a.get("bench_sharpe"),
                         "active_vs_spy": b.get("active"), "t_vs_spy": b.get("t"), "spy_cagr": b.get("bench_cagr")})
    yr = pd.DataFrame({"listed": pd.Series(listed), "with_prices": (M & px.notna()).sum(axis=1), "evaluated": n_all,
                       "with_annual_facts": (E & F["ni"].notna() & F["margin"].notna()).sum(axis=1)})
    cov = yr.groupby(yr.index.year).mean().round(0)
    v = lib.versus(bench, spy, rf)
    notes = {"universe_equal_weight_vs_spy": {k: v.get(k) for k in KEYS}, "positions_without_later_price": int((gone & E).sum().sum()),
             "members_in_price_file": int(px.shape[1]), "excluded_for_daily_jump_over_200pct": glitch,
             "annual_facts_available": bool(have_facts)}
    return pd.DataFrame(rows), cov, notes


def coarse_industries(D: Path, S: Path) -> pd.DataFrame:
    """Industry rotation with 12 broad groups (3 held), the granularity of the app's sector field."""
    import mod_rules

    class Sink:
        items: list = []

        def add(self, **kw):
            self.items.append(kw)

    sink = Sink()
    mod_rules.industry_rotation(D, sink, path=S / "12_Industry_Portfolios_daily_CSV.zip", K=3, prefix="IND12", module="E")
    rows = []
    for e in sink.items:
        full, hold = lib.versus(e["r"], e["m"], e["rf"], start="1963-07"), lib.versus(e["r"], e["m"], e["rf"], start="2000-01")
        recent = lib.versus(e["r"], e["m"], e["rf"], start=str(pd.Period(full["last"], "M") - 179))
        rows.append({"id": e["id"], "label": e["label"], "note": e["note"], **{k: full.get(k) for k in KEYS + ("win10", "win10_recent", "sharpe", "bench_sharpe")},
                     "since2000_active": hold.get("active"), "since2000_t": hold.get("t"), "last15y_active": recent.get("active")})
    return pd.DataFrame(rows)


def run(D: Path, S: Path, O: Path, m: pd.Series, rf: pd.Series) -> dict:
    if (S / "12_Industry_Portfolios_daily_CSV.zip").is_file():
        coarse_industries(D, S).to_csv(O / "exploratory_sectors.csv", index=False, float_format="%.6g")
    em, em_notes = emerging(D, S, rf)
    em.to_csv(O / "exploratory_emerging.csv", index=False, float_format="%.6g")
    st, cov, st_notes = stocks(D, S, rf)
    st.to_csv(O / "exploratory_stocks.csv", index=False, float_format="%.6g")
    cov.to_csv(O / "exploratory_stocks_coverage.csv", float_format="%.0f")
    return {"emerging": em_notes, "stocks": st_notes}
