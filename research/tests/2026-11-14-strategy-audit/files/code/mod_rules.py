"""Modules C1 and C2: market timing and industry rotation on daily French data (1926–2026)."""
from __future__ import annotations
import math
from pathlib import Path
import numpy as np
import pandas as pd
import lib

FEE = 0.001  # per side, on the traded amount


def month_end_mask(index: pd.DatetimeIndex) -> np.ndarray:
    p = np.asarray(index.to_period("M").astype(str))
    return np.append(p[1:] != p[:-1], True)


def monthly(daily: pd.Series) -> pd.Series:
    """Calendar-month returns from complete months of a daily return series."""
    d = daily.dropna()
    first_full = d.index[0].to_period("M") + (0 if d.index[0].day <= 4 else 1)
    g = (1 + d).groupby(d.index.to_period("M")).prod() - 1
    return g[g.index >= first_full]


def tax_daily(mkt: pd.Series, rf: pd.Series, eff: pd.Series, years_window: int = 20, first_year: int = 1964) -> dict:
    yrs = mkt.index.year.values
    m, c, w = mkt.values, rf.values, eff.values
    ratios = []
    for y in range(first_year, int(yrs[-1]) - years_window + 1):
        i0, i1 = np.searchsorted(yrs, y), np.searchsorted(yrs, y + years_window)
        if np.isnan(w[i0:i1]).any():
            continue
        a = lib.after_tax(m[i0:i1], c[i0:i1], w[i0:i1], yrs[i0:i1], 252, FEE)
        b = lib.after_tax(m[i0:i1], c[i0:i1], np.ones(i1 - i0), yrs[i0:i1], 252, FEE)
        ratios.append(a / b)
    if not ratios:
        return {"tax_windows": 0}
    r = np.array(ratios)
    return {"tax_windows": len(r), "tax_median_ratio": float(np.median(r)),
            "tax_median_pa": float(np.median(r) ** (1 / years_window) - 1), "tax_win_share": float((r > 1).mean())}


def market_timing(D: Path, reg) -> None:
    ff = lib.french_table(D / "french/F-F_Research_Data_Factors_daily_CSV.zip")
    mkt, rf = ff["Mkt-RF"] + ff["RF"], ff["RF"]
    P = (1 + mkt).cumprod()
    sma = P.rolling(200).mean()
    ret21, dd = P / P.shift(21) - 1, P / P.rolling(252).max() - 1
    mom = P.shift(21) / P.shift(252) - 1
    valid = (sma.notna() & mom.notna()).values
    me = month_end_mask(P.index)
    tgt: dict[str, pd.Series] = {"T_SMA200": (P > sma).astype(float).where(valid)}
    # the app's own rule: leave below the 200-day line or in a crash, re-enter only on a full entry signal
    above, crash = (P >= sma).values, ((ret21 <= -0.15) | (dd <= -0.25)).values
    entry = above & (mom > 0).values & ~((ret21 <= -0.08) | (dd <= -0.15)).values
    state, app = math.nan, np.full(len(P), np.nan)
    for i in range(len(P)):
        if not valid[i]:
            continue
        if state != 1.0:
            state = 1.0 if entry[i] else 0.0
        elif (not above[i]) or crash[i]:
            state = 0.0
        app[i] = state
    tgt["T_APP"] = pd.Series(app, P.index)
    Pm = P[me]
    avg10 = Pm.rolling(10).mean()
    tgt["T_SMA10M"] = (Pm > avg10).astype(float).where(avg10.notna()).reindex(P.index).ffill()
    Cm = (1 + rf).cumprod()[me]
    tgt["T_TSMOM12"] = ((Pm / Pm.shift(12)) > (Cm / Cm.shift(12))).astype(float).where(Pm.shift(12).notna()).reindex(P.index).ffill()
    vm = (mkt.rolling(21).std() * math.sqrt(252))[me]
    goal = vm.expanding(60).median().shift(1)
    for cap, key in ((1.0, "T_VOL_1X"), (1.5, "T_VOL_15X")):
        tgt[key] = (goal / vm).clip(upper=cap).where(goal.notna()).reindex(P.index).ffill()
    eff = {k: v.shift(2) for k, v in tgt.items()}            # signal after close t, traded at close t+1
    eff["T_HALLOWEEN"] = pd.Series(np.isin(P.index.month, [11, 12, 1, 2, 3, 4]).astype(float), P.index)
    nth = pd.Series(1, P.index).groupby(P.index.to_period("M")).cumsum().values
    eff["T_TOM"] = pd.Series(((nth <= 3) | me).astype(float), P.index)
    labels = {
        "T_SMA200": ("US-Markt nur über der 200-Tage-Linie, sonst T-Bills", "timing", "200 Handelstage", "tägliche Prüfung"),
        "T_APP": ("Ein-/Ausstiegsregel der App auf den US-Markt angewendet", "entryexit", "200/252/21 Handelstage", "tägliche Prüfung"),
        "T_SMA10M": ("US-Markt nur über der 10-Monats-Linie (Faber)", "timing", "10 Monate", "monatliche Prüfung"),
        "T_TSMOM12": ("US-Markt nur bei 12-Monats-Rendite über T-Bills", "timing", "12 Monate", "monatliche Prüfung"),
        "T_VOL_1X": ("Schwankungssteuerung ohne Hebel (Aktienquote ≤ 100 %)", "timing", "21 Handelstage", "monatlich"),
        "T_VOL_15X": ("Schwankungssteuerung mit Hebel bis 150 %", "timing", "21 Handelstage", "monatlich"),
        "T_HALLOWEEN": ("Halloween: November–April Aktien, Mai–Oktober T-Bills", "timing", "Kalender", "zweimal jährlich"),
        "T_TOM": ("Monatswechsel: letzter und erste drei Handelstage", "timing", "Kalender", "zweimal monatlich"),
    }
    m_month, rf_month = monthly(mkt), monthly(rf)
    for key, (label, app_key, look, reb) in labels.items():
        e = eff[key]
        day = (e * mkt + (1 - e) * rf - FEE * e.diff().abs().fillna(0)).where(e.notna())
        switches = e.diff().abs()[e.notna()]
        tax = {} if key == "T_VOL_15X" else tax_daily(mkt, rf, e)
        reg.add(id=key, module="C1", family="Markt-Timing", app=app_key, label=label, r=monthly(day), m=m_month, rf=rf_month,
                cost=0.0, turnover=float(switches.sum() / (e.notna().sum() / 252)), exact=True, tax=tax, lookback=look, rebalance=reb,
                note=f"im Markt {e.mean():.0%} der Tage; {switches.gt(0).sum() / (e.notna().sum() / 252):.1f} Umschichtungen p. a."
                     + ("; Hebel für Privatanleger kaum umsetzbar, keine Steuerrechnung" if key == "T_VOL_15X" else ""))


def industry_rotation(D: Path, reg) -> None:
    R = lib.french_table(D / "french/30_Industry_Portfolios_daily_CSV.zip", "daily")
    ff = lib.french_table(D / "french/F-F_Research_Data_Factors_daily_CSV.zip").reindex(R.index)
    assert not R.isna().any().any() and not ff.isna().any().any()
    P, PM, PC = (1 + R).cumprod(), (1 + ff["Mkt-RF"] + ff["RF"]).cumprod(), (1 + ff["RF"]).cumprod()
    sig_pos = np.where(month_end_mask(P.index))[0][:-1]       # last trading day of each month
    ex_pos = sig_pos + 1                                      # traded at the next close
    hold = lambda X: pd.DataFrame(X.values[ex_pos[1:]] / X.values[ex_pos[:-1]] - 1,
                                  index=P.index[ex_pos[:-1]].to_period("M"), columns=getattr(X, "columns", None))
    HP = hold(P)
    m_c2, rf_c2 = hold(PM.to_frame("m"))["m"], hold(PC.to_frame("rf"))["rf"]
    at = lambda X: pd.DataFrame(X.values[sig_pos[:-1]], index=HP.index, columns=P.columns)
    mom122, mom121 = at(P.shift(21) / P.shift(252) - 1), at(P / P.shift(252) - 1)
    mom61, smar = at(P / P.shift(126) - 1), at(P / P.rolling(200).mean() - 1)
    vol, dd = at(np.log1p(R).rolling(252).std() * math.sqrt(252)), at(P / P.rolling(252).max() - 1)
    bill12 = pd.Series((PC / PC.shift(252) - 1).values[sig_pos[:-1]], HP.index)
    ok = mom122.notna().all(axis=1) & vol.notna().all(axis=1)
    K = 6

    def top(score: pd.DataFrame) -> pd.DataFrame:
        return (score.rank(axis=1, ascending=False, method="first") <= K).astype(float) / K

    pct = lambda X: X.rank(axis=1, pct=True)
    dip = ((dd <= -0.15) & (dd >= -0.55)).astype(float)
    none = dip.sum(axis=1) == 0
    dipw = dip.div(dip.sum(axis=1).where(~none, 1), axis=0)
    dipw[none] = 1 / P.shape[1]
    dual = top(mom121) * (mom121.gt(bill12, axis=0)).astype(float)
    specs = {
        "IND_MOM122": (top(mom122), "Branchen-Momentum 12–2 (wie App-Definition)", "momentum", "252 bis 21 Handelstage", (1, 3, 12)),
        "IND_MOM121": (top(mom121), "Branchen-Momentum 12 Monate inkl. letztem Monat", "momentum", "252 Handelstage", (1,)),
        "IND_MOM61": (top(mom61), "Branchen-Momentum 6 Monate", "momentum", "126 Handelstage", (1,)),
        "IND_TREND": (top(smar), "Branchen mit größtem Abstand über der 200-Tage-Linie", "trend", "200 Handelstage", (1, 3, 12)),
        "IND_LOWVOL": (top(-vol), "Branchen mit geringster 252-Tage-Schwankung", "lowRisk", "252 Handelstage", (1, 3, 12)),
        "IND_HIGH52": (top(dd), "Branchen am nächsten am 52-Wochen-Hoch", "high52", "252 Handelstage", (1,)),
        "IND_DIP": (dipw, "Branchen 15–55 % unter dem 52-Wochen-Hoch (Kursteil von Hoch-Tief-Mut)", "sander", "252 Handelstage", (1,)),
        "IND_RAM": (top(mom122 / vol), "Branchen-Momentum 12–2 je Schwankung", "riskmom", "252 Handelstage", (1,)),
        "IND_APPMIX": (top((pct(mom122) + pct(smar) + pct(-vol)) / 3), "App-Mix auf Branchen: Momentum + Trend + geringe Schwankung", "mix", "252/200 Handelstage", (1, 3, 12)),
        "IND_TIMING": ((smar >= 0).astype(float) / P.shape[1], "Alle 30 Branchen, jede nur über ihrer 200-Tage-Linie", "entryexit", "200 Handelstage", (1,)),
        "IND_DUALMOM": (dual, "Branchen-Momentum mit T-Bill-Filter (Dual Momentum)", "momentum", "252 Handelstage", (1,)),
        "IND_EW": (pd.DataFrame(1 / P.shape[1], HP.index, P.columns), "Alle 30 Branchen gleichgewichtet", "", "–", (1,)),
    }
    freq_name = {1: "monatlich", 3: "vierteljährlich", 12: "jährlich"}
    for key, (W, label, app_key, look, freqs) in specs.items():
        W = W[ok]
        for f in freqs:
            Wf = W.iloc[::f].reindex(W.index).ffill()
            cash = 1 - Wf.sum(axis=1)
            turn = (Wf.diff().abs().sum(axis=1) + cash.diff().abs()).fillna(0) / 2
            r = (Wf * HP.loc[Wf.index]).sum(axis=1) + cash * rf_c2.loc[Wf.index] - 2 * FEE * turn
            sid = key if f == 1 else f"{key}_{f}M"
            reg.add(id=sid, module="C2", family="Branchenrotation", app=app_key, label=label + ("" if f == 1 else f", {freq_name[f]}e Umschichtung"),
                    r=r, m=m_c2, rf=rf_c2, cost=0.0, turnover=float(12 * turn.mean()), exact=True, lookback=look, rebalance=freq_name[f],
                    note=f"Ø {Wf.gt(0).sum(axis=1).mean():.1f} Branchen, Umschlag {12 * turn.mean():.0%} p. a., Ø Kasse {cash.mean():.0%}")


def run(D: Path, reg) -> None:
    market_timing(D, reg)
    industry_rotation(D, reg)
