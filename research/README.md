# Forschungs- und Testarchiv

Hier liegen die relevanten Informationen der bisherigen empirischen Studien. **Vor Fragen zu alten Resultaten oder einer neuen Berechnung zuerst hier nachlesen.** Ein Ordner pro Test, unveränderte Originalergebnisse, strukturierte Metadaten und genaue Paket-/Dateihashes.

| Datum/Test | Geprüfter Horizont | Aussage/Grenze |
| --- | --- | --- |
| [Fünfjahres-Backtest der ursprünglichen Handelsregeln](tests/2026-10-31-five-year-backtest) | 20-Handelstage-Ausstiegsannahme; 320 zufällige, teils überlappende Signaltermine | 320 Datumskohorten archiviert; heutige Überlebendenliste begrenzt die Aussage. |
| [ATR-Kauflimit-/Stopp-Sensitivität](tests/2026-10-31-atr-limits-stops) | 20-Handelstage-Tradeversuch | Kauf-/Stoppabstände variiert; die maximale Haltedauer wurde nicht variiert. |
| [12–2-Momentum gegen ursprüngliches Momentum/ATR-Modell](tests/2026-10-31-momentum-12-2) | 20-Handelstage-Ausstieg bei identischen weiteren Bedingungen | 12–2 bezeichnet den Signalrückblick, keine zwölfmonatige Haltedauer. |
| [Akademische Value-/Quality-/Investment-/Momentum-Portfolios](tests/2026-10-31-scientific-factor-study) | Keine individuelle Aktien-Kursprognose; langfristiger Portfoliovergleich | Langfristige Portfolio-, Kosten- und Robustheitsvergleiche; kein eigener Haltedauer-Suchlauf. |
| [Unabhängiger Vergleich der aktuellen Ein-/Ausstiegsregeln](tests/2026-10-31-independent-trade-rules) | Maximal 20 Sessions; zehn gleich große Kapitalsitze | Ein-/Ausstiegsregeln bei gleicher maximaler Dauer verglichen; keine optimierte Dauer je Strategie. |
| [Behavioral-/Informationsstrategien gegen US-Markt](tests/2026-11-01-behavioral-benchmark) | Vergleich fester Quellenportfolios; keine individuelle Aktien-Prognose | Für die festgelegten Portfoliovarianten kein robuster Überlegenheitsnachweis gegen den US-Markt. |
| [Globaler Nachrichtenstimmungs-Pilot](tests/2026-11-01-global-sentiment) | Nächste Archivwoche bzw. folgende Handelswoche | Bessere Nachrichtenkategorien-Prognose; kein zusätzlicher zuverlässiger Kursrichtungsvorteil im Wochenziel. |
| [PCA/PLS und gemeinsame historische Faktor-Zustände](tests/2026-11-02-pca-factor-states) | Vier Wochen primär, zwölf Wochen deskriptiv | Bei vier Wochen kein Modell mit geringerem MSE als Null-Mehrertragsprognose; zwölf Wochen ohne besseren Gesamt-MSE. |

| [Haltedauer, Weiterhalten und Prognosehorizonte – systematische Folgestudie](tests/2026-11-02-holding-duration) | A:1–12Monate Aktualisierung; B:5–252Sitzungen; C:1–52Wochen | Tatsächlich durchgeführte vergangenheitsbasierte Intervallwahl; große Unterschiede, keine universelle optimale Dauer; Einzelpositionsrisiko beachten. **[Nachprüfung 03.11.2026](tests/2026-11-02-holding-duration/REVIEW_2026-11-03.md):** Universums- und vermutete Datenverzerrung im Training, Momentum-Dauerwahl nicht signifikant. |

| [Strategie-Audit und Suche nach verlässlicher Outperformance](tests/2026-11-14-strategy-audit) | Realisierte Portfoliorenditen bis zum nächsten Auswahltermin; feste Rhythmen 1/3/12 Monate nebeneinander, keine Dauerwahl | 350 Strategien nach vorab festgelegtem Protokoll: keine schlägt den US-Markt verlässlich. Hinweise für Momentum, Trend und Quality; Gegenwind für den Kursteil von Hoch-Tief-Mut. Die App zeigt seither je Strategie die Einordnung. |

## Nachprüfungen

- [03.11.2026 – Haltedauer-Studie und Momentum-Definition](tests/2026-11-02-holding-duration/REVIEW_2026-11-03.md): keine Neuberechnung. Alle archivierten Momentum-Tests verwenden den früheren 42-Sitzungen-Abstand; die App rechnet seit 03.11.2026 nach dem Literaturstandard mit 21 Sitzungen.
- 03.11.2026 – übrige Studien (Fünfjahrestest, ATR, 12–2-Vergleich, unabhängige Regeln, akademische Faktoren, Behavioral, Nachrichtenstimmung, PCA/PLS): kein Korrekturbedarf. Ihre bekannten Verzerrungen (heutige überlebende Titel, Großkonzern-Kohorte, bekannte Testjahre) sind jeweils genannt. Da sie positive Ergebnisse begünstigen würden, bleiben die dort gefundenen fehlenden Vorteile stichhaltig. Die akademische Faktorstudie nutzt die French-Portfolios „Prior 12–2“ mit nur einem ausgelassenen Monat, also dieselbe Definition, die die App seit 03.11.2026 verwendet. Ihr Marktvergleich enthält korrekt Mkt-RF + RF.

## Schnellzugriff

- [Maschinenlesbarer Index](index.json)
- [Haltedauer, Rebalancing und Reichweite der bisherigen Aussagen](HOLDING_PERIODS.md)
- [Vorlage für neue Tests](templates/TEST.md)
- [Archiv prüfen](tools/check_archive.py)
- [Bereits berechnetes Vollpaket wiederherstellen](tools/restore_bundle.py)

## Was im Git-Archiv liegt

Pro Test: README mit Frage und Reichweite, `test.json`, unveränderte Berichte/Protokolle, vorhandene Skripte und kompakte Ergebnis-/Eingabedateien unter `files/`, sowie ein vollständiges Mitglieder-/SHA-256-Manifest des ursprünglichen Datenpakets. Abbildungen werden mitgeführt, wenn sie kompakt sind.

Große Kurs-/Nachrichten-/Modell-/Trade-Dateien werden über den genauen vollständigen Datenpaketverweis plus Prüfsumme erhalten. Ab der Studie vom 14.11.2026 kann das Paket auch ein Commit eines Daten-Branches dieses Repositorys sein (`research-data/…`); die Prüfsumme deckt dann die vollständige Mitgliederliste ab. Sie sind nicht neu herunterzuladen oder auszuwerten: das vorhandene Paket lässt sich direkt verifizieren und entpacken. Die Verweise benötigen den Zugang des Eigentümers. Bei älteren Studien ohne mitgelieferten Originalcode wird diese Lücke ausdrücklich genannt; kein Code wurde nachträglich als ursprünglich verwendet ausgegeben.

## Arbeitsregel für alle künftigen Tests

1. Eindeutigen Ordner `research/tests/JJJJ-MM-TT-kurzname/` anlegen; Wiederholungen/Änderungen erhalten eigene Version/ID.
2. Frage, Hypothese, Universum, Datenstand, Quellen/Hashes, Parameter, Kosten und Benchmark vor dem Rechnen festhalten.
3. **Signalrückblick, Prognosehorizont, tatsächliche/maximale Haltedauer, Ausstiegsregel und Rebalancing getrennt dokumentieren.** Festhalten, ob ein Haltezeitensuchlauf tatsächlich erfolgt ist.
4. Zeitliche Training-/Validierungs-/Testgrenzen, abgeschlossene Zielrenditen, verfügbare Daten und Vorverarbeitung festhalten; bekannte Testjahre nicht als neu unberührt ausgeben.
5. Ergebnisse, Unsicherheit/Mehrfachtests, Codeversionen, Fehler/Datenausfälle, Grenzen und noch offene Fragen sichern. Gespeicherte Testresultate nicht überschreiben.
6. `research/index.json` und diese Übersicht aktualisieren; `python research/tools/check_archive.py` ausführen.
7. Vorhandene Ergebnisse und Pakete wiederverwenden; nur bei neuer Fragestellung, geändertem Protokoll, Datenupdate oder nachgewiesenem Fehler neu rechnen. Bei reinen Forschungsaufträgen die App nicht verändern.

Die ursprüngliche Archivierung vom 02.11.2026 selbst führte keine neuen Strategietests aus. Anschließend wurde auf ausdrücklichen Auftrag die separate Haltedauer-Folgestudie durchgeführt und als neuer Test archiviert. Ihre abgeschlossene, begrenzte Reichweite und verbleibenden Lücken stehen in HOLDING_PERIODS.md.
