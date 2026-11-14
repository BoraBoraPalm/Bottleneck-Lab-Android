#!/usr/bin/env python3
"""Write every result table of the study as one German Markdown file (no interpretation, no selection)."""
from __future__ import annotations
import argparse, json, math
from pathlib import Path
import pandas as pd

APP = {"momentum": "12–2-Momentum", "lowRisk": "Geringe Schwankung", "trend": "200-Tage-Trend", "sander": "Hoch-Tief-Mut",
       "growth": "Frühwachstum", "quality": "Quality", "value": "Value", "earnings": "Gewinnmomentum",
       "investment": "Bilanzwachstum", "entryexit": "Ein-/Ausstiegsregel", "mix": "Mischungen", "timing": "Timing",
       "high52": "52-Wochen-Hoch", "riskmom": "Momentum je Schwankung", "search": "Auswahl vergangener Sieger"}


def num(v, d=1, pct=True, sign=False):
    if v is None or (isinstance(v, float) and not math.isfinite(v)):
        return "–"
    x = 100 * v if pct else v
    s = f"{x:+.{d}f}" if sign else f"{x:.{d}f}"
    return s.replace(".", ",").replace("-", "−")


def table(df: pd.DataFrame, cols: list[tuple]) -> str:
    head = "| " + " | ".join(c[0] for c in cols) + " |\n| " + " | ".join("---" for _ in cols) + " |\n"
    body = ""
    for _, r in df.iterrows():
        body += "| " + " | ".join(str(c[1](r)) for c in cols) + " |\n"
    return head + body + "\n"


MAIN = [("Strategie", lambda r: r.label), ("ab", lambda r: r["first"]), ("Rendite p. a.", lambda r: num(r.cagr)),
        ("Markt", lambda r: num(r.bench_cagr)), ("Mehrrendite vor Kosten", lambda r: num(r.gross_active, sign=True)),
        ("nach Kosten", lambda r: num(r.active, sign=True)), ("t", lambda r: num(r.t, 2, False)),
        ("p nach Holm", lambda r: num(r.p_holm, 3, False)), ("seit 2000¹", lambda r: num(r.hold_active, sign=True)),
        ("t", lambda r: num(r.hold_t, 2, False)), ("letzte 15 J.", lambda r: num(r.recent_active, sign=True)),
        ("10-J.-Fenster vorn", lambda r: num(r.win10, 0) + " %"), ("nach Steuer²", lambda r: num(r.tax_median_pa, sign=True)),
        ("größter Einbruch", lambda r: num(r.maxdd, 0) + " % (Markt " + num(r.bench_maxdd, 0) + " %)"),
        ("Einstufung", lambda r: r.verdict + (" · risikomindernd" if r.risk_reducing else ""))]
NOTE = ("¹ Kontrollzeitraum: ab 2000, bei veröffentlichten Signalen ab dem Jahr nach der Veröffentlichung, falls später; bei echten Produkten "
        "der ganze Zeitraum. ² Median des Unterschieds im 20-Jahres-Endvermögen nach österreichischer KESt, pro Jahr; Modell laut Protokoll. "
        "Mehrrendite = annualisierte mittlere Log-Differenz zum Benchmark.\n\n")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    O = Path(ap.parse_args().out)
    df = pd.read_csv(O / "all_strategies.csv")
    df["app"] = df["app"].fillna("")
    s = json.loads((O / "summary.json").read_text())
    md = "# Ergebnistabellen: Strategie-Audit vom 14.11.2026\n\nAutomatisch aus den Ergebnisdateien erzeugt. Alle bewerteten Strategien, ohne Auswahl. Einordnung und Grenzen stehen im Bericht.\n\n"
    md += f"Bewertet: {s['strategies_evaluated']} Strategien. Einstufungen: " + ", ".join(f"{k}: {v}" for k, v in s["verdict_counts"].items()) + ". "
    md += (f"Nominal p < 0,05: {s['nominal_p_below_5pct']}; nach Benjamini-Hochberg: {s['bh_below_5pct']}; nach Holm (K1): {s['criteria_pass_counts']['K1']}.\n\n" + NOTE)
    md += "## 1 · Die Strategien der App und ihre nächsten Vergleichsportfolios\n\n"
    for key in ("momentum", "trend", "lowRisk", "quality", "value", "investment", "earnings", "growth", "sander", "entryexit"):
        part = df[(df.app == key) & ~df.module.isin(["C5", "C3-Regionen"])].sort_values("t", ascending=False)
        md += f"### {APP[key]}\n\n" + table(part, MAIN)
    md += "## 2 · Alle übrigen selbst gebauten Regeln und Mischungen\n\n"
    rest = df[df.module.isin(["C1", "C2", "C3", "C4"]) & ~df.app.isin(["momentum", "trend", "lowRisk", "quality", "value", "investment", "earnings", "growth", "sander", "entryexit"])]
    md += table(rest.sort_values(["module", "t"], ascending=[True, False]), MAIN)
    md += "## 3 · Regionen (French, große Werte, in USD)\n\n" + table(df[df.module == "C3-Regionen"].sort_values(["family", "t"], ascending=[True, False]), MAIN)
    md += "## 4 · Vergangene Sieger auswählen\n\n" + table(df[df.family == "Vergangene Sieger auswählen"].sort_values("t", ascending=False), MAIN)
    o = s["osap"]
    md += ("## 5 · Suche über veröffentlichte Signale (Open Source Asset Pricing)\n\n"
           f"{o['signals']} Signale, oberstes wertgewichtetes Fünftel gegen den US-Markt. Mittlere Mehrrendite vor Kosten in der Stichprobe der Originalarbeit: "
           f"{num(o['mean_gross_active_insample'], 2, sign=True)} % p. a.; nach der Veröffentlichung: {num(o['mean_gross_active_postpub'], 2, sign=True)} % p. a. "
           f"({num(o['share_positive_gross_postpub'], 0)} % der Signale positiv; {o['with_both_periods']} Signale mit beiden Zeiträumen). "
           f"Nach Kosten nominal signifikant: {o['insample_net_p_below_5pct']} in der Originalstichprobe, {o['postpub_net_p_below_5pct']} nach Veröffentlichung, "
           f"{o['postpub_net_holm_below_5pct']} nach Holm.\n\nDie 30 Signale mit dem höchsten t-Wert im Gesamtzeitraum:\n\n")
    md += table(df[df.id.str.startswith("OSAP_")].sort_values("t", ascending=False).head(30), MAIN)
    md += "Vollständige Liste mit Stichproben- und Nachveröffentlichungswerten: `osap_scan.csv`.\n\n"
    md += "## 6 · Echte Produkte seit Auflage\n\nErste sechs Monate verworfen. Vergleich mit SPY, EFA bzw. EUNL.DE in gleicher Währung.\n\n"
    c5 = df[df.module == "C5"].copy()
    c5["grp"] = c5.family.str.replace("Echtes Produkt: ", "")
    md += table(c5.sort_values(["grp", "t"], ascending=[True, False]),
                [("Gruppe", lambda r: r.grp), ("Produkt", lambda r: r.label), ("ab", lambda r: r["first"]), ("Monate", lambda r: int(r.months)),
                 ("Rendite p. a.", lambda r: num(r.cagr)), ("Benchmark", lambda r: num(r.bench_cagr)), ("Mehrrendite", lambda r: num(r.active, sign=True)),
                 ("t", lambda r: num(r.t, 2, False)), ("5-J.-Fenster vorn", lambda r: num(r.win5, 0) + " %"), ("Einstufung", lambda r: r.verdict)])
    g = c5.groupby("grp").agg(n=("active", "size"), mittel=("active", "mean"), median=("active", "median"), vorn=("active", lambda x: int((x > 0).sum())))
    md += table(g.reset_index(), [("Gruppe", lambda r: r.grp), ("Produkte", lambda r: int(r.n)), ("davon vorn", lambda r: int(r.vorn)),
                                  ("Mittel p. a.", lambda r: num(r.mittel, sign=True)), ("Median p. a.", lambda r: num(r["median"], sign=True))])
    f = s["funds"]
    md += f"Nicht verfügbar: {', '.join(f['etf_missing']) or '–'}. Ausgeschlossen: {', '.join(f['etf_excluded']) or '–'}. Zu kurz: {', '.join(f['etf_short']) or '–'}.\n\n"
    md += "## 7 · Steuerhürde (österreichische KESt, Modell)\n\nUS-Markt gegen sich selbst: gleicher Ertrag vor Steuer, aber ein Teil des Depots wird jedes Jahr mit Gewinn umgeschichtet. Median über rollierende 20-Jahres-Fenster.\n\n"
    h = pd.read_csv(O / "tax_hurdle.csv")
    md += table(h, [("Daten ab", lambda r: r["from"]), ("Umschlag p. a.", lambda r: num(r.turnover_per_year, 0) + " %"), ("Fenster", lambda r: int(r.windows)),
                    ("Nachteil p. a.", lambda r: num(r.median_after_tax_gap_pa, 2, sign=True)), ("Endvermögen relativ", lambda r: num(r.median_wealth_ratio_20y, 0) + " %")])
    md += "## 8 · Explorative Ergänzungen (nach Sichtung der Hauptergebnisse festgelegt; nicht in der Holm-Familie)\n\n"
    if (O / "exploratory_emerging.csv").is_file():
        e = pd.read_csv(O / "exploratory_emerging.csv")
        md += "### E · Schwellenländer\n\n" + table(e, [("Art", lambda r: r.kind), ("Portfolio/Fonds", lambda r: r["name"]), ("Variante", lambda r: r.variant),
              ("ab", lambda r: r["first"]), ("Monate", lambda r: int(r.months)), ("Rendite p. a.", lambda r: num(r.cagr)), ("Benchmark", lambda r: num(r.bench_cagr)),
              ("Mehrrendite", lambda r: num(r.active, sign=True)), ("t", lambda r: num(r.t, 2, False)), ("5-J.-Fenster vorn", lambda r: num(r.win5, 0) + " %")])
    if (O / "exploratory_stocks.csv").is_file():
        st = pd.read_csv(O / "exploratory_stocks.csv")
        md += ("### S · Regeln der App an S&P-500-Aktien (ab 2011)\n\nGleichgewichtet, Signal zum Monatsschluss, 0,2 % Kosten je Seite. Vergleich: Gleichgewichtung aller auswertbaren "
               "Mitglieder. Kurse nicht mehr notierter Aktien fehlen; das begünstigt die Strategien.\n\n")
        md += table(st, [("Regel", lambda r: r.label), ("Ø Aktien", lambda r: num(r.avg_names, 0, False)), ("Umschlag p. a.", lambda r: num(r.turnover_pa, 0) + " %"),
              ("Rendite p. a.", lambda r: num(r.cagr)), ("alle Mitglieder", lambda r: num(r.bench_cagr)), ("Mehrrendite", lambda r: num(r.active, sign=True)),
              ("t", lambda r: num(r.t, 2, False)), ("5-J.-Fenster vorn", lambda r: num(r.win5, 0) + " %"), ("größter Einbruch", lambda r: num(r.maxdd, 0) + " %"),
              ("gegen SPY", lambda r: num(r.active_vs_spy, sign=True)), ("t", lambda r: num(r.t_vs_spy, 2, False))])
        cov = pd.read_csv(O / "exploratory_stocks_coverage.csv", index_col=0)
        md += "Abdeckung (Jahresmittel): " + "; ".join(f"{y}: {int(r.evaluated)} von {int(r.listed)}" for y, r in cov.iterrows() if int(y) % 3 == 2 or int(y) == cov.index.max()) + ".\n\n"
        x = s["exploratory"]["stocks"]
        md += (f"Gleichgewichtung aller auswertbaren Mitglieder gegen SPY: {num(x['universe_equal_weight_vs_spy']['active'], sign=True)} % p. a. "
               f"Wegen Kurssprüngen über 200 % ausgeschlossen: {', '.join(x['excluded_for_daily_jump_over_200pct']) or '–'}. "
               f"Positionen ohne späteren Kurs (mit 0 % gezählt): {x['positions_without_later_price']}. "
               f"Jahreszahlen der SEC verfügbar: {'ja' if x['annual_facts_available'] else 'nein – die Regeln mit Unternehmenszahlen wurden nicht gerechnet'}.\n\n")
    if (O / "exploratory_sectors.csv").is_file():
        se = pd.read_csv(O / "exploratory_sectors.csv")
        md += "### Branchenrotation mit zwölf groben Branchen (je drei gehalten, ab 1963)\n\n"
        md += table(se, [("Regel", lambda r: r.label), ("Rendite p. a.", lambda r: num(r.cagr)), ("Markt", lambda r: num(r.bench_cagr)), ("Mehrrendite", lambda r: num(r.active, sign=True)),
              ("t", lambda r: num(r.t, 2, False)), ("seit 2000", lambda r: num(r.since2000_active, sign=True)), ("t", lambda r: num(r.since2000_t, 2, False)),
              ("letzte 15 J.", lambda r: num(r.last15y_active, sign=True)), ("10-J.-Fenster vorn", lambda r: num(r.win10, 0) + " %"), ("Hinweis", lambda r: r.note)])
    (O / "tabellen.md").write_text(md)
    print(f"tabellen.md: {len(md)} Zeichen")


if __name__ == "__main__":
    main()
