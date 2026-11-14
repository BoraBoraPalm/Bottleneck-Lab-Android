# Strategie-Audit und Suche nach verlässlicher Outperformance

Status: **abgeschlossen, Aussage auf den dokumentierten Versuchsaufbau begrenzt**. Testdatum: 14.11.2026. Die App wurde auf ausdrücklichen Auftrag anhand der Ergebnisse geändert.

**Keine geprüfte Methode schlägt den Markt verlässlich.** Von 350 Strategien erfüllt in den USA keine die vorab festgelegten Kriterien; die einzige Ausnahme ist ein Papier-Portfolio aus Schwellenländern, dessen Vorsprung bei realistischen Kosten weitgehend verschwindet.

## Frage und Hypothese

1. Sind die neun Strategien der App und ihre Ein-/Ausstiegsregeln durch historische Daten gestützt?
2. Schlagen andere bekannte Strategien den Markt?
3. Gibt es eine Methode, die den Markt nach Kosten und österreichischer Steuer statistisch verlässlich übertrifft?

Bekannt waren die Fachliteratur und die acht früheren Studien dieses Archivs. „Verlässlich“ ist im [Protokoll](files/protocol.md) über sechs Kriterien definiert, die vor dem Laden der Daten feststanden.

## Nachlesen ohne neue Berechnung

- [Bericht mit Einordnung und Grenzen](files/bericht.md)
- [Alle Ergebnistabellen](files/output/tabellen.md) und [alle 350 Strategien als CSV](files/output/all_strategies.csv)
- [Protokoll mit Kriterien, Kosten, Steuer-Modell und Änderungshistorie](files/protocol.md)
- [Strukturierte Testmetadaten](test.json) und [Datei-/Hashmanifest des Datenpakets](ARTIFACT_MEMBERS.json)

## Daten, Universum und Verfügbarkeit

| Quelle | Inhalt | Stand |
| --- | --- | --- |
| Kenneth French Data Library | US-Portfolios ab 1926/1963 ohne Überlebensverzerrung, 30 Branchen täglich, sieben Regionen ab 1990 | bis 2026-09, abgerufen 14.11.2026 |
| Open Source Asset Pricing (Chen/Zimmermann) | 179 veröffentlichte Signale, wertgewichtete Fünftel | bis 2025-12, Stand ad1dfba5 (byte-gleich zur Studie vom 01.11.2026) |
| Yahoo Finance | 86 ETFs und Fonds, Monatsrenditen aus bereinigten Tageskursen | bis 2026-10 |
| Ergänzung: S&P-500-Mitgliederliste (fja05680/sp500), Yahoo-Kurse von 654 der 858 Mitglieder seit 2009, 12 French-Branchen, 24 Schwellenländerfonds | explorativer Teil | abgerufen 14.11.2026 |

Jede abgerufene Datei steht mit SHA-256 in [files/data/inputs_manifest.json](files/data/inputs_manifest.json) und [files/data/supplement_manifest.json](files/data/supplement_manifest.json). Das vollständige Paket (French-Dateien unverändert, verdichtete OSAP- und Kursdaten, Ergebnisse) liegt auf dem Daten-Branch `research-data/2026-11-14-strategy-audit`; der genaue Commit steht in `test.json`. Im Repository selbst liegen die kompakten Eingaben und alle Ergebnisse.

Nicht verfügbar: AMOMX und PSRM.DE (Yahoo ohne Daten). Die SEC-Schnittstellen lehnen Abrufe aus GitHub Actions ab; Jahresabschlussdaten für den Einzelaktien-Test fehlen deshalb.

## Strategie und Zeitdefinitionen

- **Signalrückblick und Neubildung:** je Strategie in `all_strategies.csv` (Spalten `lookback`, `rebalance`). Quellportfolios behalten die Regeln ihrer Quelle.
- **Prognosehorizont:** keiner; verglichen werden realisierte Portfoliorenditen.
- **Haltedauer:** bis zum nächsten Auswahltermin. Keine Stopps. Bei Timing-Regeln tägliche bzw. monatliche Prüfung mit Handel am Folgetag.
- **Haltedauer-Suche:** nicht durchgeführt. Für Branchenrotation und den Einzelaktien-Test wurden feste Rhythmen von 1, 3 und 12 Monaten nebeneinander berichtet, ohne Auswahl.
- **Kosten:** selbst gebaute Regeln mit tatsächlichem Umschlag × 0,1 % je Seite (Einzelaktien 0,2 %); Quellportfolios mit pauschal 0,3 / 0,5 / 1,0 % pro Jahr je Neubildungsrhythmus, Nebenwerte doppelt.
- **Steuer:** Modell der österreichischen KESt (27,5 %), ausgewiesen als Endvermögen über rollierende 20-Jahres-Fenster.
- **Benchmark:** US-Gesamtmarkt (French), regionaler Markt, bzw. SPY, EFA, EUNL.DE für echte Produkte.

## Validierung

Protokoll, Strategieliste und Kriterien wurden vor dem Laden der Daten in das Repository geschrieben (Commit `9bdf955`). Mehrfachtests: Holm-Korrektur über alle 350 Strategien. Kontrollzeitraum ab 2000 bzw. ab dem Jahr nach der Veröffentlichung eines Signals. Zwei archivierte Studien wurden mit dem neuen Code exakt nachgerechnet (Renditen auf drei Nachkommastellen gleich). Die Rechnung lief in GitHub Actions und lokal auf demselben Eingabepaket mit byte-gleichen Ergebnisdateien.

## Ergebnisse und Interpretation

Siehe [Bericht](files/bericht.md). Kurzfassung:

- Einstufungen: 1 verlässlich (Schwellenländer-Mix, nur auf dem Papier), 13 Hinweise, 314 nicht belegt, 22 Evidenz dagegen.
- Veröffentlichte Signale: im Mittel +1,8 Prozentpunkte pro Jahr in der Originalstichprobe, −0,8 nach der Veröffentlichung.
- Die Strategien der App: Hinweise für Momentum, Trend und Quality; kein Mehrertrag für geringe Schwankung, Value, Bilanzwachstum und Gewinnmomentum; Gegenwind für den Kursteil von Hoch-Tief-Mut.
- Markt-Timing senkt Einbrüche und kostet Rendite.
- Ein jährlicher Depotumschlag kostet nach KESt rund 1,1 Prozentpunkte pro Jahr gegenüber Kaufen und Halten.

## Grenzen

- Bekannte historische Jahre; ein positives Ergebnis wäre ein Hinweis, kein Beweis.
- Kosten und Steuer sind Annahmen bzw. ein vereinfachtes Modell.
- Revidierte French- und Yahoo-Daten; fehlerhafte Yahoo-Kurse neuer UCITS-ETFs (erste sechs Monate verworfen); geschlossene Produkte fehlen.
- Einzelaktien-Test nur mit heute noch geführten Kursen (69 % der Mitglieder von 2010).
- Explorative Teile (Schwellenländer, Einzelaktien, zwölf Branchen) wurden nach Sichtung der Hauptergebnisse festgelegt.
- **Geplant und nicht gerechnet:** Hoch-Tief-Mut mit Qualitätsfilter, Bruttogewinn/Bilanzsumme und Bilanzwachstum an Einzelaktien (keine SEC-Daten). Value nach Kurs/Buchwert, das Gewinn-Quartalsmodell und Frühwachstum sind mit freien Daten nicht zeitpunktgetreu nachbildbar.

Die Ergebnisse widerlegen keine anders gebaute oder anders gehaltene Strategie.

## Reproduktion und Wiederverwendung

Code: [files/code](files/code), Pakete: [files/requirements.txt](files/requirements.txt). Workflow: `.github/workflows/research-strategy-audit.yml` (läuft nur auf Forschungs-Branches oder von Hand, berührt die App nicht). Lauf und Code-Commit stehen in `files/output/code_identity.txt`.

```bash
git fetch origin research-data/2026-11-14-strategy-audit && git worktree add ../audit_data FETCH_HEAD
python research/tests/2026-11-14-strategy-audit/files/code/run_all.py --data ../audit_data/inputs --supplement ../audit_data/supplement --out /tmp/audit_out
python research/tests/2026-11-14-strategy-audit/files/code/make_report.py --out /tmp/audit_out
```

Die Zahlen in der App (`docs/evidence-data.js`) erzeugt `files/code/export_app_evidence.py` aus diesen Ergebnisdateien; `tests/test_evidence.cjs` vergleicht sie mit dem Archiv. Erst gespeicherte Ergebnisse lesen; neu rechnen nur bei neuer Frage, geändertem Protokoll oder nachgewiesenem Fehler.

Ein erster Versuch legte das Eingabepaket an einem Vorab-Release (`research-2026-11-14-strategy-audit`) ab. Dieser Weg wurde verworfen; die Datei dort ist ein nicht verwendeter früherer Abruf und kann gelöscht werden.
