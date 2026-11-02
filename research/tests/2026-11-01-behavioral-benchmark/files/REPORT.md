# Einmalige Prüfung: Psychologie und Informationsverarbeitung am Aktienmarkt

Stand: 1. November 2026 · Daten: 2000–2025 · App unverändert

![Vergleich](output/comparison.png)

## Ergebnis

Unter den geprüften psychologisch bzw. informationsbezogen motivierten Ansätzen ist keine statistisch gesicherte Überlegenheit gegenüber dem US-Gesamtmarkt nachgewiesen. Historische EPS-Überraschungen sind risikobereinigt der beste psychologische Einzelansatz im Haupttest. Die gleichgewichtete Kombination aus EPS-Überraschungen und Analystenrevisionen ist der beste psychologische Zweiermix nach Sharpe, bleibt aber unter der Benchmark. Der separat festgelegte Quality-Kontrollansatz besitzt den höchsten beobachteten Sharpe-Wert und den kleinsten Monatsend-Einbruch, jedoch ebenfalls keinen statistisch abgesicherten Marktvorsprung. Ein maximal erfolgversprechendes zukünftiges Portfolio lässt sich daraus nicht bestimmen.

## Auftrag und Abgrenzung

Einmalige, getrennte Analyse am 1. November 2026. Die App, ihr Frontend, ihre Rankings und ihre Veröffentlichung wurden nicht verändert. Dies ist eine Replikationsprüfung veröffentlichter Forschungsportfolios, kein Test der konkreten App-Aktienliste und keine neue Simulation einzelner Brokerorders. Es werden vier vor 2000 publizierte Signale verglichen, die mit verzögerter Informationsverarbeitung und unterschiedlichen Erwartungen in Verbindung gebracht werden. Der Test beweist keine psychologische Kausalität.

## Datengrundlage

Open Source Asset Pricing von Chen und Zimmermann, Ausgabe Oktober 2026, Daten bis Dezember 2025; unveränderlicher Datenstand ad1dfba5a6d80c4ce53ce6b8127f5a949dda1e40. Die Portfoliokonstruktion beruht auf CRSP/Compustat/IBES. Benchmark und Risikofaktoren stammen aus Kenneth Frenchs Data Library. Hauptfenster: Januar 2000 bis Dezember 2025, 312 aufeinanderfolgende Monate, identisch für alle Portfolios. Ergebnisse primär in USD, Dividenden sind in den Renditen enthalten. Der US-Gesamtmarkt ist keine Welt-ETF-/Kommer-ETF-Benchmark. Die historischen Portfolios werden neu zusammengesetzt; heutige überlebende Aktien bilden nicht die Ausgangsauswahl. Erfasste Delisting-Renditen sind nach der CIZ-Konvention enthalten; nicht erfasste Delisting-Ergebnisse werden nicht von uns ergänzt.

## Definitionen und Konstruktion

| Signal | Bedeutung |
| --- | --- |
| Mom12m | Kumulierte vorherige elf Monatsrenditen, jüngsten Signalmonat übersprungen; im standardisierten Original-Replikationsportfolio quartalsweise Neuzuordnung (März/Juni/September/Dezember). |
| EarningsSurprise | Historisches saisonales EPS-Modell: jährliche EPS-Änderung minus vorherigem Drift, standardisiert durch historische Schwankung. Kein Vergleich mit Analystenkonsens. Quelle setzt Quartalsdaten frühestens drei Monate nach Quartalsende an und verschiebt später gemeldete Quartale weiter. |
| REV6 | Preisnormierte Veränderungen der mittleren Analysten-Gewinnschätzung. Das Replikationsskript summiert die aktuelle und sechs vorherige Monatsänderungen; die Bezeichnung REV6 wird unverändert aus der Quelle übernommen. Monatliche Neuzuordnung. |
| AnnouncementReturn | Letzte marktbereinigte Kursreaktion im Fenster um eine Quartalsmeldung; erst nach Abschluss des Ereignisfensters dem Signalmonat zugeordnet. Quelle führt das Signal höchstens sechs Monate fort. Monatliche Neuzuordnung. Kein direkter Text-/Social-Media-Sentiment- oder Aufmerksamkeitsmesswert. |
| Kontrollen | Value = Buch-/Marktwert; Quality = Gross Profitability, Bruttogewinn/Bilanzsumme, Finanzunternehmen ausgenommen. Beide neu zugeordnet jährlich im Juni. Zusätzlich ein festes Drittelmix aus Momentum, Value und Quality. Der Quality-Ansatz wurde erst 2013 publiziert; sein Ergebnis vor 2014 ist deshalb keine Nachpublikationsvalidierung. |

Haupttest: jeweils das günstige obere Fünftel der signalverfügbaren Aktien, innerhalb des Fünftels nach vorheriger Marktkapitalisierung gewichtet. Kein Leerverkauf und kein Hebel. Alle sechs 50/50-Paare der vier psychologischen Signale sowie ein Vierermix mit je 25 % wurden vor der Auswertung festgelegt. Teilportfolios können dieselben Aktien enthalten. Dies ist ein Mix von Teilportfoliorenditen, keine Auswahl der Aktien, die gleichzeitig mehrere Kriterien erfüllen. Insgesamt 14 aktive Portfolios plus Benchmark. Die Signalabdeckung unterscheidet sich; es gibt keine einheitliche historische Aktienliste mit vollständigen Analysten-/Bilanzdaten für alle Signale.

## Kosten und Ergebnismaße

Zentrales Szenario: ein zusätzlicher pauschaler jährlicher Kostenfaktor von 1 % für jedes aktive Portfolio, anteilig monatlich geometrisch abgezogen. Die Benchmark erhält keinen zusätzlichen Kostenabschlag. Zusätzlich wurden 0 / 0,5 / 2 / 4 % geprüft. Das ist eine Sensitivitätsrechnung und kein Nachweis tatsächlich erzielbarer Nettoergebnisse: historische Umschichtungen, Geld-/Brief-Spannen, Brokergebühren, Markteinfluss, österreichische Steuern und Liquiditätsgrenzen sind nicht vollständig bekannt. Berechnung: Netto-Monatsrendite = (1 + Brutto-Monatsrendite) × (1 − jährlicher Kostenfaktor)^(1/12) − 1. Sharpe verwendet die jeweils passende monatliche US-T-Bill-Rendite. Einbrüche werden nur an Monatsenden gemessen; zwischenzeitliche Verluste können größer sein.

## Alle Ergebnisse im Haupttest

| Portfolio | Rendite p.a. | Volatilität p.a. | Sharpe | Max. Monatsend-Einbruch |
| --- | --- | --- | --- | --- |
| US-Gesamtmarkt (Benchmark) | 8,28 % | 15,67 % | 0,47 | -50,3 % |
| Gross Profitability / Quality (Kontrolle) | 9,00 % | 15,28 % | 0,52 | -41,8 % |
| Historische EPS-Überraschung | 8,26 % | 15,79 % | 0,47 | -50,9 % |
| Momentum + Value + Quality (Kontrolle) | 8,36 % | 16,91 % | 0,45 | -49,2 % |
| EPS-Überraschung + Analystenrevisionen | 8,56 % | 17,64 % | 0,45 | -52,0 % |
| Value (Kontrolle) | 8,94 % | 21,97 % | 0,42 | -57,1 % |
| Analystenrevisionen | 8,58 % | 20,63 % | 0,41 | -53,3 % |
| EPS-Überraschung + Meldungsreaktion | 7,65 % | 16,96 % | 0,41 | -52,5 % |
| Alle vier gleichgewichtet | 7,63 % | 17,51 % | 0,40 | -52,2 % |
| Revisionen + Meldungsreaktion | 7,89 % | 18,97 % | 0,40 | -55,2 % |
| Momentum + EPS-Überraschung | 7,25 % | 16,65 % | 0,39 | -50,9 % |
| Momentum + Analystenrevisionen | 7,48 % | 18,73 % | 0,38 | -52,1 % |
| Reaktion auf Quartalsmeldungen | 6,82 % | 19,14 % | 0,34 | -61,8 % |
| Momentum + Meldungsreaktion | 6,51 % | 18,42 % | 0,33 | -57,9 % |
| Kursmomentum | 5,95 % | 18,96 % | 0,30 | -54,4 % |

## Unsicherheit statt Siegergarantie

Primäre Inferenz: gepaarte monatliche Logrenditedifferenz zur Benchmark, Newey-West/HAC mit zwölf Monatsverzögerungen; zweiseitige Tests und Holm-Korrektur über alle 14 aktiven Portfolios. Ergänzend CAPM- und Fama-French-5-plus-Momentum-Alpha, ebenfalls mit familienweiser Korrektur. Ein gemeinsamer zirkulärer Block-Bootstrap erhält die zeitliche und gegenseitige Abhängigkeit der Portfolios: 10.000 Wiederholungen, Blocklängen 6/12/24 Monate. Die Tabelle zeigt simultane 95%-Intervalle über alle 14 Portfolios bei zwölf Monaten. Alle Intervalle enthalten null. Die Korrektur gilt für diese Untersuchung, nicht für sämtliche vorherigen Versuche in der Finanzliteratur.

| Portfolio | Relative Mehrrendite p.a. | Simultanes 95%-Intervall | Holm-p |
| --- | --- | --- | --- |
| Historische EPS-Überraschung | -0,01 % | -2,36 % bis 2,39 % | 1,000 |
| EPS-Überraschung + Analystenrevisionen | 0,26 % | -2,98 % bis 3,62 % | 1,000 |
| Analystenrevisionen | 0,28 % | -5,12 % bis 5,98 % | 1,000 |
| Kursmomentum | -2,15 % | -6,61 % bis 2,53 % | 1,000 |
| Alle vier gleichgewichtet | -0,60 % | -3,02 % bis 1,88 % | 1,000 |
| Gross Profitability / Quality (Kontrolle) | 0,66 % | -2,51 % bis 3,94 % | 1,000 |

Relative Mehrrendite ist die annualisierte Veränderung des Vermögensverhältnisses zum Markt, nicht die Differenz zweier CAGR in Prozentpunkten. Fehlende Signifikanz beweist keine Wirkungslosigkeit. Sie bedeutet, dass dieser Test den Vorteil nicht verlässlich nachweist. Punktweise Sharpe-Differenzintervalle und Bootstrap-Ranghäufigkeiten stehen in results.json; Ranghäufigkeiten sind keine Wahrscheinlichkeiten künftiger Überlegenheit.

## Chronologische Nachprüfung

Die Auswahl anhand der Jahre 2000–2013 bestimmt ausschließlich nach damaligem Sharpe den EPS-Überraschungsansatz. Ohne anschließende Parameteränderung erzielt er 2014–2025 nach dem Kostenfaktor 12,57 % p.a.; die Benchmark erreicht 13,20 %. Eine separat festgelegte jährliche Wahl des besten Ansatzes anhand der jeweils vorherigen zehn Jahre erzielt 2010–2025 10,93 % statt 14,07 % für den Markt. Auch das Wechseln zur zuletzt besten Strategie liefert hier keinen Vorteil. Dies sind retrospektive chronologische Prüfungen: Die Jahre sind weder der Forschung noch dem Analysten heute tatsächlich unbekannt. Die letzte echte Prospektivprüfung müsste nach dem heutigen Festlegen der Regeln beginnen.

## Beständigkeit über Zeiträume

| Zeitraum | Markt | EPS | Revisionen | EPS + Revisionen | Quality |
| --- | --- | --- | --- | --- | --- |
| 2000-01 bis 2007-12 | 2,12 % | 3,46 % | 4,73 % | 4,21 % | 0,35 % |
| 2008-01 bis 2013-12 | 7,12 % | 6,39 % | 4,33 % | 5,46 % | 9,38 % |
| 2014-01 bis 2019-12 | 11,57 % | 8,24 % | 2,78 % | 5,55 % | 12,10 % |
| 2020-01 bis 2025-12 | 14,84 % | 17,06 % | 25,26 % | 21,38 % | 17,92 % |

Die besonders hohen jüngsten Revisionsrenditen sind kein Beleg für die Wahl genau dieses Zeitraums als zukünftigen Maßstab. Die Hauptperiode und ihre Teilfenster wurden vor der Auswertung fixiert. Rollierende Fenster in results.json überlappen und sind keine unabhängigen Versuche.

## Andere Konstruktionen und unabhängige Kontrolle

Die Hauptauswertung wurde mit einem Ausschluss der Aktien unter dem jeweiligen NYSE-20%-Größenschwellenwert wiederholt. Diese Datei behält Originalgewichtung und Original-Quantile der Studien bei, überwiegend Gleichgewichtung; sie ist daher ein gezielter Konstruktions-Stresstest und keine isolierte Änderung nur der Größe. Zusätzlich wurden jährliche große FF93-Portfolios geprüft. Die Quellcodeprüfung zeigt: dort werden alle Signale nur im Juni neu zugeordnet. Sie sind für schnelle Nachrichten-/Momentumstrategien deshalb lediglich eine strukturelle Sensitivität. Kein Universum wurde nachträglich zum neuen Haupttest erklärt.

| Konstruktion | Portfolio | Rendite p.a. | Sharpe |
| --- | --- | --- | --- |
| value_weighted_quintiles | Historische EPS-Überraschung | 8,26 % | 0,47 |
| value_weighted_quintiles | EPS-Überraschung + Analystenrevisionen | 8,56 % | 0,45 |
| value_weighted_quintiles | Gross Profitability / Quality (Kontrolle) | 9,00 % | 0,52 |
| value_weighted_quintiles | Kursmomentum | 5,95 % | 0,30 |
| liquid_original | Historische EPS-Überraschung | 8,60 % | 0,42 |
| liquid_original | EPS-Überraschung + Analystenrevisionen | 9,07 % | 0,43 |
| liquid_original | Gross Profitability / Quality (Kontrolle) | 8,66 % | 0,50 |
| liquid_original | Kursmomentum | 6,11 % | 0,29 |
| annual_big_sensitivity_only | Historische EPS-Überraschung | 8,18 % | 0,47 |
| annual_big_sensitivity_only | EPS-Überraschung + Analystenrevisionen | 8,29 % | 0,46 |
| annual_big_sensitivity_only | Gross Profitability / Quality (Kontrolle) | 8,23 % | 0,48 |
| annual_big_sensitivity_only | Kursmomentum | 7,20 % | 0,39 |

Nach dem Hauptlauf kam ein unabhängiger Kontrollvergleich mit Kenneth Frenchs monatlich umgeschichteten Momentum-Portfolios hinzu. Alle vier dabei betrachteten Varianten sind offengelegt, die Mehrfachtestkorrektur wurde ergänzend auf 18 Portfolios erweitert. Diese Kontrollen sind explorativ; sie führen zu keiner Änderung der festgelegten Hauptstrategien.

| Monatliche Momentum-Kontrolle | Rendite p.a. | Sharpe | Max. Monatsend-Einbruch |
| --- | --- | --- | --- |
| French monthly large top30 | 7,35 % | 0,41 | -48,7 % |
| French monthly small top30 | 10,63 % | 0,49 | -54,9 % |
| French monthly top10 | 8,41 % | 0,40 | -51,7 % |
| French monthly decile9 | 6,63 % | 0,37 | -51,8 % |

## Kostensensitivität

| Zusätzlicher Kostenfaktor p.a. | EPS | EPS + Revisionen | Alle vier | Quality |
| --- | --- | --- | --- | --- |
| 0,0 % | 9,36 % | 9,66 % | 8,72 % | 10,10 % |
| 0,5 % | 8,81 % | 9,11 % | 8,17 % | 9,55 % |
| 1,0 % | 8,26 % | 8,56 % | 7,63 % | 9,00 % |
| 2,0 % | 7,17 % | 7,47 % | 6,54 % | 7,90 % |
| 4,0 % | 4,98 % | 5,27 % | 4,37 % | 5,69 % |

Der beobachtete Brutto-Vorsprung des EPS-Ansatzes verschwindet rechnerisch bereits bei etwa 0,99 % jährlichem Zusatzabzug; beim EPS-/Revisionsmix bei 1,26 %. Diese Grenzen sind historische Rechnungen, keine Schätzungen tatsächlicher Brokerkosten.

## Zusätzliche EUR-Sicht

Für österreichische Leser wurden alle USD-Vermögenspfade einheitlich mit monatlichen USD/EUR-Referenzkursen umgerechnet, vollständig ungesichert. Die verwendeten Frankfurter-Kurse sind gemischte Mittelkursdaten offizieller Quellen, keine ausführbaren Brokerkurse. Es wurde bewusst kein EUR-Sharpe ausgewiesen, weil kein entsprechender EUR-Geldmarktsatz verwendet wurde. Bei identischer Umrechnung bleibt die relative Vermögensentwicklung zum selben Benchmarkpfad unverändert.

| Portfolio | Rendite p.a. in EUR | Max. Monatsend-Einbruch in EUR |
| --- | --- | --- |
| US-Gesamtmarkt (Benchmark) | 7,64 % | -58,3 % |
| Historische EPS-Überraschung | 7,62 % | -57,1 % |
| EPS-Überraschung + Analystenrevisionen | 7,92 % | -54,1 % |
| Alle vier gleichgewichtet | 6,99 % | -58,9 % |
| Gross Profitability / Quality (Kontrolle) | 8,35 % | -53,8 % |

## Nicht seriös mitgetestet

Ein direkter Angst-/Gier-, Medien- oder Social-Media-Timingansatz wurde nicht als geprüfter Sieger dargestellt. Für einen fairen Test fehlen hier geprüfte historische Veröffentlichungszeitpunkte, damals verfügbare Datenschnappschüsse und vollständige Quellenabdeckung. Die aktuelle Baker-Wurgler-Reihe wird revidiert und ihre Konstruktionsmethode wurde 2026 verändert; eine bloße zeitliche Verschiebung der heutigen Indexreihe beseitigt diesen Einwand nicht. Der AnnouncementReturn-Ansatz misst die bereits beobachtete Kursreaktion auf Quartalsmeldungen und ersetzt keinen vollständigen Sentiment-Test. Ein historisch geschätztes SUE ist außerdem keine Analystenkonsens-Überraschung und nicht der Net-Income-Indikator der App.

## Verbleibende Grenzen

Vollständig ohne Bias ist diese Untersuchung nicht zertifizierbar. Die zugrunde liegenden Kurs-/Bilanz-/Analystendaten können rückwirkend korrigiert sein; ein vollständiger Audit zeitgenössischer kommerzieller Datenschnappschüsse war nicht möglich. Die Quellen verwenden festgelegte Verfügbarkeitsverzögerungen und haben einen früheren Look-ahead-Fehler in AnnouncementReturn 2024 korrigiert. Die vorhandenen Signale sind aus bereits veröffentlichter Literatur gewählt. Die Zahl aller früheren Ideenversuche ist unbekannt. Ein Vergleich gegen den gesamten US-Markt kann auch Größen-, Branchen- und Datenabdeckungsunterschiede enthalten; Risikoalphas und alternative Konstruktionen mindern, beseitigen aber nicht sämtliche Vergleichsprobleme. Bei Strategiewechseln im Walk-forward-Test fallen in der Wirklichkeit weitere unbekannte Kosten an. Die alten Einzelaktienversuche mit heutiger Überlebendenauswahl wurden nicht als Beweis für einen unverzerrten Vorteil übernommen.

## Praktische Einordnung

Für weitere Forschung sind historische EPS-Überraschungen sowie deren einfacher 50/50-Mix mit Analystenrevisionen die sinnvollsten Kandidaten dieser psychologischen Vorauswahl. Quality ist der überzeugendste deskriptive Kontrollansatz in dieser Stichprobe. Weder die stärksten letzten Jahre noch die höchste volle Historienrendite rechtfertigen die Behauptung eines maximal erfolgversprechenden zukünftigen Ansatzes. Der getestete Vierermix, das Nachlaufen der zuletzt besten Strategie und zusätzliche Signalkomplexität liefern hier keinen belastbaren Nutzen gegenüber der Benchmark. Die Untersuchung rechtfertigt keine Änderung der App auf eine angeblich bewiesene Gewinnerstrategie.

## Quellen und Reproduzierbarkeit

- [Open Source Asset Pricing, Daten Oktober 2026](https://www.openassetpricing.com/data/)
- [Fixierter Datensatz und Dokumentation](https://huggingface.co/datasets/OpenSourceAP/CrossSection/tree/ad1dfba5a6d80c4ce53ce6b8127f5a949dda1e40)
- [Quellcode-Audit, Stand 9f053398c4995651d822e90d81526d0644c6f3e5](https://github.com/OpenSourceAP/CrossSection/tree/9f053398c4995651d822e90d81526d0644c6f3e5)
- [Kenneth French Data Library](https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/data_library.html)
- [Chen und Zimmermann, Open Source Cross-Sectional Asset Pricing](https://www.federalreserve.gov/econres/feds/open-source-cross-sectional-asset-pricing.htm)
- [McLean/Pontiff 2016, Nachpublikationsrenditen](https://doi.org/10.1111/jofi.12365)
- [Baker-Wurgler, Konstruktions-/Revisionshinweise 2026](https://github.com/BWInvestorSentimentIndex/BakerandWurglerInvestorSentimentIndex)
- [Frankfurter, Wechselkursmethodik](https://frankfurter.dev/)

Die kompakten Eingabetabellen, Monatsrenditen aller Kandidaten, vollständigen Ergebnisse und Prüfskripte liegen diesem Paket bei. protocol.json wurde vor dem Berechnen der Zielperiodenresultate fixiert (SHA-256 6ae37388d3b46bd1e24cfcd071aa3722bf6f811fc0fd899684d8bb94e5a90a80). download_data.py lädt die größeren Originaldateien mit festgehaltenen Prüfsummen nach. Die beiden später ergänzten Diagnosen sind separat als supplement.py und supplement.json gekennzeichnet. Es handelt sich um eine einmalige historische Analyse, keine laufende Beobachtung oder Automatisierung.

