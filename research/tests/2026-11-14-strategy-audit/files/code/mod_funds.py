"""Modules C4 and C5: asset-class rules on index funds and real factor products since launch."""
from __future__ import annotations
import json
from pathlib import Path
import numpy as np
import pandas as pd
import lib
import sources as S

KNOWN_EVENTS = ("1987-10", "2008-10", "2008-11", "2020-03")
SEASONING = 6   # calendar months dropped after the first quote (listing glitches)
APP_OF_GROUP = {"Momentum": "momentum", "Quality": "quality", "Value": "value", "Geringe Schwankung": "lowRisk",
                "Nebenwerte": "", "Dividende": "", "Trend/Taktisch": "timing"}


def run(D: Path, reg, rf: pd.Series) -> dict:
    Y = pd.read_csv(D / "yahoo/monthly_returns.csv", index_col=0)
    Y.index = pd.PeriodIndex(Y.index, freq="M")
    audit = json.loads((D / "yahoo/audit.json").read_text())
    info = {"etf_missing": [], "etf_excluded": [], "etf_short": []}

    def usable_from(sym: str):
        """First evaluated month, or None when an unexplained jump remains after seasoning."""
        a = audit.get(sym, {})
        if sym not in Y.columns or "first" not in a:
            info["etf_missing"].append(sym)
            return None
        start = pd.Period(a["first"][:7], "M") + SEASONING + 1
        late = [d for d, v in a.get("moves_over_12pct", []) if abs(v) > 0.20 and pd.Period(d[:7], "M") >= start
                and d[:7] not in KNOWN_EVENTS]
        if late:
            info["etf_excluded"].append(f"{sym}: Tagessprung > 20 % am {', '.join(late[:3])}")
            return None
        return start

    # ---------------- C5: real products
    zero = pd.Series(0.0, Y.index)
    for bench, syms in S.ETF_PAIRS.items():
        b0 = usable_from(bench)
        for sym in syms:
            s0 = usable_from(sym)
            if s0 is None or b0 is None:
                continue
            start = max(s0, b0)
            r = Y[sym].dropna()
            r = r[r.index >= start]
            if len(r) < 36:
                info["etf_short"].append(sym)
                continue
            eur = bench.endswith(".DE")
            a = audit[sym]
            reg.add(id="ETF_" + sym.replace(".", "_"), module="C5", family="Echtes Produkt: " + S.ETF_GROUP[sym],
                    app=APP_OF_GROUP[S.ETF_GROUP[sym]], label=f"{a.get('name') or sym} ({sym}) gegen {bench}",
                    r=r, m=Y[bench], rf=zero if eur else rf, cost=0.0, turnover=0.0, exact=True, full_start=None,
                    holdout_start=None, lookback="Produktregel", rebalance="im Fonds",
                    note=("EUR, Sharpe ohne Zinsabzug; " if eur else "") + f"erster Kurs {a['first']}, ausgewertet ab {start}")
    # ---------------- C4: asset-class rules (month-end signal and execution)
    us, ex, bd = Y["VFINX"], Y["VGTSX"], Y["VBMFX"]
    df = pd.concat([us, ex, bd, rf], axis=1, keys=["us", "ex", "bd", "rf"]).dropna()
    r12 = np.expm1(np.log1p(df).rolling(12).sum())
    choice = np.where(r12.us > r12.rf, np.where(r12.us >= r12.ex, "us", "ex"), "bd")
    choice = pd.Series(choice, df.index).where(r12.us.notna()).shift(1).dropna()
    gem = pd.Series([df.at[i, c] for i, c in choice.items()], choice.index) - 0.002 * choice.ne(choice.shift(1)).astype(float)
    sw = float(choice.ne(choice.shift(1)).iloc[1:].mean() * 12)
    reg.add(id="GEM", module="C4", family="Anlageklassen-Regel", app="timing", label="Global Equities Momentum (Antonacci): US- oder Auslandsaktien, sonst Anleihen",
            r=gem, m=us, rf=rf, cost=0.0, turnover=sw, exact=True, full_start=None, lookback="12 Monate", rebalance="monatliche Prüfung",
            note=f"{sw:.1f} Wechsel p. a.; Anteile: US {choice.eq('us').mean():.0%}, Ausland {choice.eq('ex').mean():.0%}, Anleihen {choice.eq('bd').mean():.0%}; Indexfonds VFINX/VGTSX/VBMFX")
    assets = pd.concat([Y[c] for c in ("VFINX", "VGTSX", "VFITX", "VGSIX", "DBC")], axis=1)
    idx = (1 + assets.fillna(0)).cumprod().where(assets.notna())
    avg = idx.rolling(10).mean()
    held = (idx > avg).astype(float).where(avg.notna())
    W = held.div(avg.notna().sum(axis=1), axis=0).shift(1)
    W = W[avg.notna().sum(axis=1).shift(1) >= 4].fillna(0)
    cash = 1 - W.sum(axis=1)
    turn = (W.diff().abs().sum(axis=1) + cash.diff().abs()).fillna(0) / 2
    gtaa = ((W * assets.reindex(W.index).fillna(0)).sum(axis=1) + cash * rf.reindex(W.index) - 0.002 * turn).dropna()
    reg.add(id="GTAA5", module="C4", family="Anlageklassen-Regel", app="timing", label="GTAA (Faber): fünf Anlageklassen, jede nur über ihrer 10-Monats-Linie",
            r=gtaa, m=us, rf=rf, cost=0.0, turnover=float(12 * turn.mean()), exact=True, full_start=None, lookback="10 Monate", rebalance="monatliche Prüfung",
            note=f"US-Aktien, Auslandsaktien, Staatsanleihen, Immobilien, Rohstoffe (ab 2006); Ø Kasse {cash.mean():.0%}")
    mix = (0.6 * us + 0.4 * bd).dropna()
    reg.add(id="P6040", module="C4", family="Anlageklassen-Regel", app="", label="60 % US-Aktien / 40 % Anleihen, monatlich angepasst",
            r=mix, m=us, rf=rf, cost=0.0, turnover=0.1, exact=True, full_start=None, lookback="–", rebalance="monatlich", note="VFINX/VBMFX")
    world = (0.5 * us + 0.5 * ex).dropna()
    info["c4_vs_world"] = {k: lib.versus(v, world, rf) for k, v in (("GEM", gem), ("GTAA5", gtaa), ("P6040", mix))}
    info["c4_vs_6040"] = {k: lib.versus(v, mix, rf) for k, v in (("GEM", gem), ("GTAA5", gtaa))}
    return info
