"""Write the reviewable German report, full tables and a standalone plot."""
import base64
import hashlib
import html
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.ticker import PercentFormatter
import numpy as np
import pandas as pd

from run_study import ROOT, DATA, OUT, SIGNALS, drag, metrics

NAMES = {
    "Mom12m": "Kursmomentum",
    "EarningsSurprise": "Historische EPS-Überraschung",
    "REV6": "Analystenrevisionen",
    "AnnouncementReturn": "Reaktion auf Quartalsmeldungen",
    "Mom12m + EarningsSurprise": "Momentum + EPS-Überraschung",
    "Mom12m + REV6": "Momentum + Analystenrevisionen",
    "Mom12m + AnnouncementReturn": "Momentum + Meldungsreaktion",
    "EarningsSurprise + REV6": "EPS-Überraschung + Analystenrevisionen",
    "EarningsSurprise + AnnouncementReturn": "EPS-Überraschung + Meldungsreaktion",
    "REV6 + AnnouncementReturn": "Revisionen + Meldungsreaktion",
    "Equal four": "Alle vier gleichgewichtet",
    "GP": "Gross Profitability / Quality (Kontrolle)",
    "BM": "Value (Kontrolle)",
    "Momentum + Value + Quality": "Momentum + Value + Quality (Kontrolle)",
    "US Market": "US-Gesamtmarkt (Benchmark)",
}


def pct(x, digits=2):
    return f"{100*x:.{digits}f}".replace(".", ",") + " %"


def num(x, digits=2):
    return f"{x:.{digits}f}".replace(".", ",")


def md_table(headers, rows):
    return "| " + " | ".join(headers) + " |\n| " + " | ".join("---" for _ in headers) + " |\n" + "\n".join("| " + " | ".join(map(str, row)) + " |" for row in rows)


def html_table(headers, rows):
    return '<div class="table-wrap"><table><thead><tr>' + ''.join('<th>'+html.escape(str(x))+'</th>' for x in headers) + '</tr></thead><tbody>' + ''.join('<tr>'+''.join('<td>'+html.escape(str(x))+'</td>' for x in r)+'</tr>' for r in rows) + '</tbody></table></div>'


def make_plot(r):
    plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 10, "axes.spines.top": False,
                         "axes.spines.right": False, "axes.titleweight": "bold"})
    curves = pd.read_csv(OUT / "wealth_net_1pct.csv", index_col=0)
    dates = pd.PeriodIndex(curves.index, freq="M").to_timestamp("M")
    fig, ax = plt.subplots(2, 1, figsize=(11.5, 8), gridspec_kw={"height_ratios": [1.45, 1]})
    colors = {"Mom12m": "#9c646d", "EarningsSurprise": "#2874a6", "EarningsSurprise + REV6": "#16857f",
              "GP": "#6554a4", "Equal four": "#c58b32"}
    for name in ["GP", "EarningsSurprise", "EarningsSurprise + REV6", "Equal four", "Mom12m"]:
        relative = curves[name] / curves["US Market"] * 100
        ax[0].plot(dates, relative, color=colors[name], lw=1.8, label=NAMES[name].replace(" (Kontrolle)", ""))
    ax[0].axhline(100, color="#273746", lw=1.4, ls="--", label="US-Gesamtmarkt = 100")
    ax[0].set_ylabel("Vermögen relativ zum Markt\nStartverhältnis 100")
    ax[0].set_title("Der Vorsprung hängt von Zeitraum und Strategie ab", loc="left", pad=14)
    ax[0].set_ylim(40, 185)
    ax[0].grid(axis="y", alpha=.2)
    ax[0].legend(loc="upper right", ncol=2, frameon=True, facecolor="white", framealpha=.95, fontsize=8.5)
    periods = list(r["subperiods"])[:4]
    x = np.arange(len(periods)); width = .24
    for i, (name, color) in enumerate([("US Market", "#273746"), ("EarningsSurprise + REV6", "#16857f"), ("GP", "#6554a4")]):
        y = [r["subperiods"][p]["benchmark"]["cagr"] if name == "US Market"
             else r["subperiods"][p]["cost_scenarios"]["0.01"][name]["cagr"] for p in periods]
        ax[1].bar(x + (i-1)*width, y, width, color=color, label=NAMES[name].replace(" (Kontrolle)", ""))
    ax[1].set_xticks(x, ["2000–2007", "2008–2013", "2014–2019", "2020–2025"])
    ax[1].yaxis.set_major_formatter(PercentFormatter(1, decimals=0))
    ax[1].set_ylabel("Geometrische Rendite pro Jahr")
    ax[1].set_title("Auch die jüngste Stärke der Revisionen ist kein stabiler Gesamtsieger", loc="left", pad=12)
    ax[1].grid(axis="y", alpha=.2); ax[1].set_axisbelow(True)
    ax[1].legend(loc="upper left", fontsize=8.5, frameon=False)
    fig.suptitle("Einmalige Prüfung verhaltensbasierter Aktienstrategien", fontsize=16, fontweight="bold", x=.08, ha="left")
    fig.text(.08, .025, "US-Aktien · USD · inklusive Dividenden · aktive Portfolios mit 1 % zusätzlichem pauschalem Kostenfaktor pro Jahr.\nForschungsportfolios; keine gemessenen Brokerkosten, keine Steuern. Keine Strategie besitzt einen gesicherten Marktvorsprung.", fontsize=8.5, color="#4b5563")
    fig.subplots_adjust(left=.08, right=.98, top=.90, bottom=.13, hspace=.40)
    fig.savefig(OUT / "comparison.png", dpi=180, facecolor="white")
    plt.close(fig)


def main():
    results = json.loads((OUT / "results.json").read_text())
    extra = json.loads((OUT / "supplement.json").read_text())
    r = results["universes"]["value_weighted_quintiles"]
    rows = r["cost_scenarios"]["0.01"]
    make_plot(r)
    headers = ["Portfolio", "Rendite p.a.", "Volatilität p.a.", "Sharpe", "Max. Monatsend-Einbruch"]
    overview = [[NAMES["US Market"], pct(r["benchmark"]["cagr"]), pct(r["benchmark"]["volatility"]), num(r["benchmark"]["sharpe"]), pct(r["benchmark"]["max_month_end_drawdown"], 1)]]
    for name, m in sorted(rows.items(), key=lambda v: -v[1]["sharpe"]):
        overview.append([NAMES[name], pct(m["cagr"]), pct(m["volatility"]), num(m["sharpe"]), pct(m["max_month_end_drawdown"], 1)])
    overview_frame = pd.DataFrame(overview, columns=headers)
    overview_frame.to_csv(OUT / "overview_german.csv", index=False)
    cashflows = pd.read_csv(OUT / "value_weighted_quintiles_inputs.csv", index_col=0)
    gross = pd.read_csv(OUT / "value_weighted_quintiles_gross_sleeves.csv", index_col=0)
    # Independent arithmetic cross-check against scalar product/mean/std. This
    # validates the reported financial units separately from the engine's log path.
    for name in rows:
        net = drag(gross[name].to_numpy(), .01)
        expected = np.prod(1+net)**(12/len(net)) - 1
        expected_sharpe = np.mean(net-cashflows.RF)/np.std(net-cashflows.RF, ddof=1)*np.sqrt(12)
        assert np.isclose(expected, rows[name]["cagr"], atol=1e-12)
        assert np.isclose(expected_sharpe, rows[name]["sharpe"], atol=1e-12)
    assert all(m["relative_log_hac"]["p_holm_14"] >= .05 for m in rows.values())
    assert all(ci["relative_excess_simultaneous_95"][0] <= 0 <= ci["relative_excess_simultaneous_95"][1]
               for ci in r["bootstrap"]["12"]["strategies"].values())

    sections = []
    def section(title, text): sections.append((title, text))
    section("Ergebnis", "Unter den geprüften psychologisch bzw. informationsbezogen motivierten Ansätzen ist keine statistisch gesicherte Überlegenheit gegenüber dem US-Gesamtmarkt nachgewiesen. Historische EPS-Überraschungen sind risikobereinigt der beste psychologische Einzelansatz im Haupttest. Die gleichgewichtete Kombination aus EPS-Überraschungen und Analystenrevisionen ist der beste psychologische Zweiermix nach Sharpe, bleibt aber unter der Benchmark. Der separat festgelegte Quality-Kontrollansatz besitzt den höchsten beobachteten Sharpe-Wert und den kleinsten Monatsend-Einbruch, jedoch ebenfalls keinen statistisch abgesicherten Marktvorsprung. Ein maximal erfolgversprechendes zukünftiges Portfolio lässt sich daraus nicht bestimmen.")
    section("Auftrag und Abgrenzung", "Einmalige, getrennte Analyse am 1. November 2026. Die App, ihr Frontend, ihre Rankings und ihre Veröffentlichung wurden nicht verändert. Dies ist eine Replikationsprüfung veröffentlichter Forschungsportfolios, kein Test der konkreten App-Aktienliste und keine neue Simulation einzelner Brokerorders. Es werden vier vor 2000 publizierte Signale verglichen, die mit verzögerter Informationsverarbeitung und unterschiedlichen Erwartungen in Verbindung gebracht werden. Der Test beweist keine psychologische Kausalität.")
    section("Datengrundlage", "Open Source Asset Pricing von Chen und Zimmermann, Ausgabe Oktober 2026, Daten bis Dezember 2025; unveränderlicher Datenstand ad1dfba5a6d80c4ce53ce6b8127f5a949dda1e40. Die Portfoliokonstruktion beruht auf CRSP/Compustat/IBES. Benchmark und Risikofaktoren stammen aus Kenneth Frenchs Data Library. Hauptfenster: Januar 2000 bis Dezember 2025, 312 aufeinanderfolgende Monate, identisch für alle Portfolios. Ergebnisse primär in USD, Dividenden sind in den Renditen enthalten. Der US-Gesamtmarkt ist keine Welt-ETF-/Kommer-ETF-Benchmark. Die historischen Portfolios werden neu zusammengesetzt; heutige überlebende Aktien bilden nicht die Ausgangsauswahl. Erfasste Delisting-Renditen sind nach der CIZ-Konvention enthalten; nicht erfasste Delisting-Ergebnisse werden nicht von uns ergänzt.")
    definitions = [
        ["Mom12m", "Kumulierte vorherige elf Monatsrenditen, jüngsten Signalmonat übersprungen; im standardisierten Original-Replikationsportfolio quartalsweise Neuzuordnung (März/Juni/September/Dezember)."],
        ["EarningsSurprise", "Historisches saisonales EPS-Modell: jährliche EPS-Änderung minus vorherigem Drift, standardisiert durch historische Schwankung. Kein Vergleich mit Analystenkonsens. Quelle setzt Quartalsdaten frühestens drei Monate nach Quartalsende an und verschiebt später gemeldete Quartale weiter."],
        ["REV6", "Preisnormierte Veränderungen der mittleren Analysten-Gewinnschätzung. Das Replikationsskript summiert die aktuelle und sechs vorherige Monatsänderungen; die Bezeichnung REV6 wird unverändert aus der Quelle übernommen. Monatliche Neuzuordnung."],
        ["AnnouncementReturn", "Letzte marktbereinigte Kursreaktion im Fenster um eine Quartalsmeldung; erst nach Abschluss des Ereignisfensters dem Signalmonat zugeordnet. Quelle führt das Signal höchstens sechs Monate fort. Monatliche Neuzuordnung. Kein direkter Text-/Social-Media-Sentiment- oder Aufmerksamkeitsmesswert."],
        ["Kontrollen", "Value = Buch-/Marktwert; Quality = Gross Profitability, Bruttogewinn/Bilanzsumme, Finanzunternehmen ausgenommen. Beide neu zugeordnet jährlich im Juni. Zusätzlich ein festes Drittelmix aus Momentum, Value und Quality. Der Quality-Ansatz wurde erst 2013 publiziert; sein Ergebnis vor 2014 ist deshalb keine Nachpublikationsvalidierung."],
    ]
    section("Definitionen und Konstruktion", md_table(["Signal", "Bedeutung"], definitions) + "\n\nHaupttest: jeweils das günstige obere Fünftel der signalverfügbaren Aktien, innerhalb des Fünftels nach vorheriger Marktkapitalisierung gewichtet. Kein Leerverkauf und kein Hebel. Alle sechs 50/50-Paare der vier psychologischen Signale sowie ein Vierermix mit je 25 % wurden vor der Auswertung festgelegt. Teilportfolios können dieselben Aktien enthalten. Dies ist ein Mix von Teilportfoliorenditen, keine Auswahl der Aktien, die gleichzeitig mehrere Kriterien erfüllen. Insgesamt 14 aktive Portfolios plus Benchmark. Die Signalabdeckung unterscheidet sich; es gibt keine einheitliche historische Aktienliste mit vollständigen Analysten-/Bilanzdaten für alle Signale.")
    section("Kosten und Ergebnismaße", "Zentrales Szenario: ein zusätzlicher pauschaler jährlicher Kostenfaktor von 1 % für jedes aktive Portfolio, anteilig monatlich geometrisch abgezogen. Die Benchmark erhält keinen zusätzlichen Kostenabschlag. Zusätzlich wurden 0 / 0,5 / 2 / 4 % geprüft. Das ist eine Sensitivitätsrechnung und kein Nachweis tatsächlich erzielbarer Nettoergebnisse: historische Umschichtungen, Geld-/Brief-Spannen, Brokergebühren, Markteinfluss, österreichische Steuern und Liquiditätsgrenzen sind nicht vollständig bekannt. Berechnung: Netto-Monatsrendite = (1 + Brutto-Monatsrendite) × (1 − jährlicher Kostenfaktor)^(1/12) − 1. Sharpe verwendet die jeweils passende monatliche US-T-Bill-Rendite. Einbrüche werden nur an Monatsenden gemessen; zwischenzeitliche Verluste können größer sein.")
    section("Alle Ergebnisse im Haupttest", md_table(headers, overview))
    infer_rows = []
    for name in ["EarningsSurprise", "EarningsSurprise + REV6", "REV6", "Mom12m", "Equal four", "GP"]:
        ci = r["bootstrap"]["12"]["strategies"][name]["relative_excess_simultaneous_95"]
        infer_rows.append([NAMES[name], pct(rows[name]["geometric_relative_excess"]), pct(ci[0]) + " bis " + pct(ci[1]), num(rows[name]["relative_log_hac"]["p_holm_14"], 3)])
    section("Unsicherheit statt Siegergarantie", "Primäre Inferenz: gepaarte monatliche Logrenditedifferenz zur Benchmark, Newey-West/HAC mit zwölf Monatsverzögerungen; zweiseitige Tests und Holm-Korrektur über alle 14 aktiven Portfolios. Ergänzend CAPM- und Fama-French-5-plus-Momentum-Alpha, ebenfalls mit familienweiser Korrektur. Ein gemeinsamer zirkulärer Block-Bootstrap erhält die zeitliche und gegenseitige Abhängigkeit der Portfolios: 10.000 Wiederholungen, Blocklängen 6/12/24 Monate. Die Tabelle zeigt simultane 95%-Intervalle über alle 14 Portfolios bei zwölf Monaten. Alle Intervalle enthalten null. Die Korrektur gilt für diese Untersuchung, nicht für sämtliche vorherigen Versuche in der Finanzliteratur.\n\n" + md_table(["Portfolio", "Relative Mehrrendite p.a.", "Simultanes 95%-Intervall", "Holm-p"], infer_rows) + "\n\nRelative Mehrrendite ist die annualisierte Veränderung des Vermögensverhältnisses zum Markt, nicht die Differenz zweier CAGR in Prozentpunkten. Fehlende Signifikanz beweist keine Wirkungslosigkeit. Sie bedeutet, dass dieser Test den Vorteil nicht verlässlich nachweist. Punktweise Sharpe-Differenzintervalle und Bootstrap-Ranghäufigkeiten stehen in results.json; Ranghäufigkeiten sind keine Wahrscheinlichkeiten künftiger Überlegenheit.")
    sel = r["fixed_development_selection"]
    wf = r["walk_forward"]
    section("Chronologische Nachprüfung", f"Die Auswahl anhand der Jahre 2000–2013 bestimmt ausschließlich nach damaligem Sharpe den EPS-Überraschungsansatz. Ohne anschließende Parameteränderung erzielt er 2014–2025 nach dem Kostenfaktor {pct(sel['evaluation']['cagr'])} p.a.; die Benchmark erreicht {pct(sel['evaluation_benchmark']['cagr'])}. Eine separat festgelegte jährliche Wahl des besten Ansatzes anhand der jeweils vorherigen zehn Jahre erzielt 2010–2025 {pct(wf['metrics']['cagr'])} statt {pct(wf['benchmark']['cagr'])} für den Markt. Auch das Wechseln zur zuletzt besten Strategie liefert hier keinen Vorteil. Dies sind retrospektive chronologische Prüfungen: Die Jahre sind weder der Forschung noch dem Analysten heute tatsächlich unbekannt. Die letzte echte Prospektivprüfung müsste nach dem heutigen Festlegen der Regeln beginnen.")
    period_rows = []
    for key, pr in list(r["subperiods"].items())[:4]:
        period_rows.append([key.replace("_", " bis "), pct(pr["benchmark"]["cagr"])] + [pct(pr["cost_scenarios"]["0.01"][n]["cagr"]) for n in ["EarningsSurprise", "REV6", "EarningsSurprise + REV6", "GP"]])
    section("Beständigkeit über Zeiträume", md_table(["Zeitraum", "Markt", "EPS", "Revisionen", "EPS + Revisionen", "Quality"], period_rows) + "\n\nDie besonders hohen jüngsten Revisionsrenditen sind kein Beleg für die Wahl genau dieses Zeitraums als zukünftigen Maßstab. Die Hauptperiode und ihre Teilfenster wurden vor der Auswertung fixiert. Rollierende Fenster in results.json überlappen und sind keine unabhängigen Versuche.")
    robustness_rows = []
    for universe in results["universes"]:
        u = results["universes"][universe]["cost_scenarios"]["0.01"]
        for n in ["EarningsSurprise", "EarningsSurprise + REV6", "GP", "Mom12m"]:
            robustness_rows.append([universe, NAMES[n], pct(u[n]["cagr"]), num(u[n]["sharpe"])])
    section("Andere Konstruktionen und unabhängige Kontrolle", "Die Hauptauswertung wurde mit einem Ausschluss der Aktien unter dem jeweiligen NYSE-20%-Größenschwellenwert wiederholt. Diese Datei behält Originalgewichtung und Original-Quantile der Studien bei, überwiegend Gleichgewichtung; sie ist daher ein gezielter Konstruktions-Stresstest und keine isolierte Änderung nur der Größe. Zusätzlich wurden jährliche große FF93-Portfolios geprüft. Die Quellcodeprüfung zeigt: dort werden alle Signale nur im Juni neu zugeordnet. Sie sind für schnelle Nachrichten-/Momentumstrategien deshalb lediglich eine strukturelle Sensitivität. Kein Universum wurde nachträglich zum neuen Haupttest erklärt.\n\n" + md_table(["Konstruktion", "Portfolio", "Rendite p.a.", "Sharpe"], robustness_rows) + "\n\nNach dem Hauptlauf kam ein unabhängiger Kontrollvergleich mit Kenneth Frenchs monatlich umgeschichteten Momentum-Portfolios hinzu. Alle vier dabei betrachteten Varianten sind offengelegt, die Mehrfachtestkorrektur wurde ergänzend auf 18 Portfolios erweitert. Diese Kontrollen sind explorativ; sie führen zu keiner Änderung der festgelegten Hauptstrategien.\n\n" + md_table(["Monatliche Momentum-Kontrolle", "Rendite p.a.", "Sharpe", "Max. Monatsend-Einbruch"], [[n, pct(v["cagr"]), num(v["sharpe"]), pct(v["max_month_end_drawdown"], 1)] for n, v in extra["momentum"].items()]))
    costs = []
    for c, values in r["cost_scenarios"].items():
        costs.append([pct(float(c), 1)] + [pct(values[n]["cagr"]) for n in ["EarningsSurprise", "EarningsSurprise + REV6", "Equal four", "GP"]])
    section("Kostensensitivität", md_table(["Zusätzlicher Kostenfaktor p.a.", "EPS", "EPS + Revisionen", "Alle vier", "Quality"], costs) + "\n\nDer beobachtete Brutto-Vorsprung des EPS-Ansatzes verschwindet rechnerisch bereits bei etwa " + pct(rows["EarningsSurprise"]["break_even_annual_extra_cost"]) + " jährlichem Zusatzabzug; beim EPS-/Revisionsmix bei " + pct(rows["EarningsSurprise + REV6"]["break_even_annual_extra_cost"]) + ". Diese Grenzen sind historische Rechnungen, keine Schätzungen tatsächlicher Brokerkosten.")
    section("Zusätzliche EUR-Sicht", "Für österreichische Leser wurden alle USD-Vermögenspfade einheitlich mit monatlichen USD/EUR-Referenzkursen umgerechnet, vollständig ungesichert. Die verwendeten Frankfurter-Kurse sind gemischte Mittelkursdaten offizieller Quellen, keine ausführbaren Brokerkurse. Es wurde bewusst kein EUR-Sharpe ausgewiesen, weil kein entsprechender EUR-Geldmarktsatz verwendet wurde. Bei identischer Umrechnung bleibt die relative Vermögensentwicklung zum selben Benchmarkpfad unverändert.\n\n" + md_table(["Portfolio", "Rendite p.a. in EUR", "Max. Monatsend-Einbruch in EUR"], [[NAMES[n], pct(extra["currency"][n]["cagr"]), pct(extra["currency"][n]["max_month_end_drawdown"], 1)] for n in ["US Market", "EarningsSurprise", "EarningsSurprise + REV6", "Equal four", "GP"]]))
    section("Nicht seriös mitgetestet", "Ein direkter Angst-/Gier-, Medien- oder Social-Media-Timingansatz wurde nicht als geprüfter Sieger dargestellt. Für einen fairen Test fehlen hier geprüfte historische Veröffentlichungszeitpunkte, damals verfügbare Datenschnappschüsse und vollständige Quellenabdeckung. Die aktuelle Baker-Wurgler-Reihe wird revidiert und ihre Konstruktionsmethode wurde 2026 verändert; eine bloße zeitliche Verschiebung der heutigen Indexreihe beseitigt diesen Einwand nicht. Der AnnouncementReturn-Ansatz misst die bereits beobachtete Kursreaktion auf Quartalsmeldungen und ersetzt keinen vollständigen Sentiment-Test. Ein historisch geschätztes SUE ist außerdem keine Analystenkonsens-Überraschung und nicht der Net-Income-Indikator der App.")
    section("Verbleibende Grenzen", "Vollständig ohne Bias ist diese Untersuchung nicht zertifizierbar. Die zugrunde liegenden Kurs-/Bilanz-/Analystendaten können rückwirkend korrigiert sein; ein vollständiger Audit zeitgenössischer kommerzieller Datenschnappschüsse war nicht möglich. Die Quellen verwenden festgelegte Verfügbarkeitsverzögerungen und haben einen früheren Look-ahead-Fehler in AnnouncementReturn 2024 korrigiert. Die vorhandenen Signale sind aus bereits veröffentlichter Literatur gewählt. Die Zahl aller früheren Ideenversuche ist unbekannt. Ein Vergleich gegen den gesamten US-Markt kann auch Größen-, Branchen- und Datenabdeckungsunterschiede enthalten; Risikoalphas und alternative Konstruktionen mindern, beseitigen aber nicht sämtliche Vergleichsprobleme. Bei Strategiewechseln im Walk-forward-Test fallen in der Wirklichkeit weitere unbekannte Kosten an. Die alten Einzelaktienversuche mit heutiger Überlebendenauswahl wurden nicht als Beweis für einen unverzerrten Vorteil übernommen.")
    section("Praktische Einordnung", "Für weitere Forschung sind historische EPS-Überraschungen sowie deren einfacher 50/50-Mix mit Analystenrevisionen die sinnvollsten Kandidaten dieser psychologischen Vorauswahl. Quality ist der überzeugendste deskriptive Kontrollansatz in dieser Stichprobe. Weder die stärksten letzten Jahre noch die höchste volle Historienrendite rechtfertigen die Behauptung eines maximal erfolgversprechenden zukünftigen Ansatzes. Der getestete Vierermix, das Nachlaufen der zuletzt besten Strategie und zusätzliche Signalkomplexität liefern hier keinen belastbaren Nutzen gegenüber der Benchmark. Die Untersuchung rechtfertigt keine Änderung der App auf eine angeblich bewiesene Gewinnerstrategie.")
    sources = [
        ("Open Source Asset Pricing, Daten Oktober 2026", "https://www.openassetpricing.com/data/"),
        ("Fixierter Datensatz und Dokumentation", "https://huggingface.co/datasets/OpenSourceAP/CrossSection/tree/ad1dfba5a6d80c4ce53ce6b8127f5a949dda1e40"),
        ("Quellcode-Audit, Stand 9f053398c4995651d822e90d81526d0644c6f3e5", "https://github.com/OpenSourceAP/CrossSection/tree/9f053398c4995651d822e90d81526d0644c6f3e5"),
        ("Kenneth French Data Library", "https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/data_library.html"),
        ("Chen und Zimmermann, Open Source Cross-Sectional Asset Pricing", "https://www.federalreserve.gov/econres/feds/open-source-cross-sectional-asset-pricing.htm"),
        ("McLean/Pontiff 2016, Nachpublikationsrenditen", "https://doi.org/10.1111/jofi.12365"),
        ("Baker-Wurgler, Konstruktions-/Revisionshinweise 2026", "https://github.com/BWInvestorSentimentIndex/BakerandWurglerInvestorSentimentIndex"),
        ("Frankfurter, Wechselkursmethodik", "https://frankfurter.dev/"),
    ]
    section("Quellen und Reproduzierbarkeit", "\n".join(f"- [{name}]({url})" for name, url in sources) + "\n\nDie kompakten Eingabetabellen, Monatsrenditen aller Kandidaten, vollständigen Ergebnisse und Prüfskripte liegen diesem Paket bei. protocol.json wurde vor dem Berechnen der Zielperiodenresultate fixiert (SHA-256 " + results["protocol_sha256"] + "). download_data.py lädt die größeren Originaldateien mit festgehaltenen Prüfsummen nach. Die beiden später ergänzten Diagnosen sind separat als supplement.py und supplement.json gekennzeichnet. Es handelt sich um eine einmalige historische Analyse, keine laufende Beobachtung oder Automatisierung.")

    title = "Einmalige Prüfung: Psychologie und Informationsverarbeitung am Aktienmarkt"
    md = "# " + title + "\n\nStand: 1. November 2026 · Daten: 2000–2025 · App unverändert\n\n"
    md += "![Vergleich](output/comparison.png)\n\n"
    for heading, content in sections:
        md += "## " + heading + "\n\n" + content + "\n\n"
    (ROOT / "REPORT.md").write_text(md)

    # Build self-contained HTML without JavaScript or external requests.
    def to_html(content):
        chunks = content.split("\n\n")
        out = []
        for chunk in chunks:
            if chunk.startswith("| "):
                lines = chunk.splitlines(); head = [x.strip() for x in lines[0].strip("|").split("|")]
                vals = [[x.strip() for x in line.strip("|").split("|")] for line in lines[2:]]
                out.append(html_table(head, vals))
            elif chunk.startswith("- ["):
                out.append("<ul>" + "".join('<li><a href="'+html.escape(url, quote=True)+'">'+html.escape(n)+'</a></li>' for n, url in sources) + "</ul>")
            else:
                out.append("<p>" + html.escape(chunk) + "</p>")
        return "".join(out)
    picture = base64.b64encode((OUT / "comparison.png").read_bytes()).decode()
    body = ''.join('<section><h2>'+html.escape(h)+'</h2>'+to_html(c)+'</section>' for h, c in sections)
    page = '''<!doctype html><html lang="de"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Einmalige Strategieprüfung 2026</title><style>body{font:16px/1.65 system-ui,sans-serif;color:#1e293b;background:#f4f6fa;margin:0}main{max-width:1080px;background:white;margin:32px auto;padding:48px;border-radius:18px}h1{font-size:32px;line-height:1.2;color:#112b40}h2{margin-top:38px;font-size:23px;color:#135f66}p{max-width:94ch}table{border-collapse:collapse;font-size:13px;width:100%}th,td{padding:10px 12px;border-bottom:1px solid #dbe2ea;text-align:left;vertical-align:top}th{background:#eaf1f5}tr:nth-child(even){background:#f7fafc}.table-wrap{overflow:auto}img{width:100%;height:auto}small{color:#64748b}a{color:#126e80}section:first-of-type{background:#eef7f5;border-radius:12px;padding:8px 24px}@media(max-width:640px){main{margin:0;padding:24px;border-radius:0}h1{font-size:26px}th,td{padding:8px}}</style><main><small>1. November 2026 · Daten 2000–2025 · einmalige Analyse · App unverändert</small><h1>''' + html.escape(title) + '</h1><img alt="Strategien relativ zum US-Markt und Renditen nach Teilperioden" src="data:image/png;base64,'+picture+'">'+body+'</main></html>'
    (ROOT / "REPORT.html").write_text(page)
    print("Report and chart written; independent arithmetic and inference checks passed.")


if __name__ == "__main__":
    main()
