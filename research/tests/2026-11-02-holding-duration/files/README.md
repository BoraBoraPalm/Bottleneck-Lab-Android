# Haltedauer-Folgestudie, 02.11.2026

Abgeschlossen, explorative historische Auswertung. Die App wurde nicht geändert.

Bericht zuerst: [output/bericht.html](output/bericht.html) oder [output/bericht.md](output/bericht.md). Kompakte Gesamtergebnisse: `output/strategy_summary.csv`; alle korrigierten primären Tests: `output/primary_tests_joint.json`.

- A: 20 Literaturfaktoren/Mischungen, vier Signalaktualisierungsintervalle, jährliche Wahl aus 120 vergangenen Monaten; Bewertung 2014–2025. Keine behauptete Einzeltitel-Haltedauer.
- B: zwölf Handelsregeln mit sechs Intervallen und vergangenheitsbasierter jährlicher Auswahl; Bewertung 2019–2025. Tatsächliche Trades, Zeitreihen, Gebühren, Ausstiege und Konzentration gespeichert.
- C: fünf Prognosemodelle, sieben neu gelernte Zielhorizonte, identische Aktien-Zeitpunkte 2022–2024. Prognosegüte ist keine Portfoliorendite.

Alle verwendeten kompakten Eingaben sind eingefroren. Keine neue Kurs-/Nachrichtenabfrage ist zur Reproduktion nötig. Die ursprünglichen größeren Quelldownloads sind durch SHA-256 und URLs identifiziert; für die Rechnung werden direkt die mitgelieferten, daraus extrahierten Datenarrays bzw. Merkmals-/Zielzeilen verwendet. Vorherige Nachrichten-/Merkmals-Rohdaten bleiben im separat archivierten PCA-/Nachrichtenpaket erhalten, siehe Forschungsindex.

`protocol.md` und `sources/protocol_initial.md` dokumentieren das Protokoll. `VERSION_HISTORY.md` erklärt Codepräzisierungen und die nach Ergebnisprüfung behobene Kaufgrenze; ungültige Zwischenwerte sind separat unter `sources/pre_execution_cap_correction/` erhalten und dürfen nicht als finale Ergebnisse verwendet werden.

Für neue Reproduktion im entpackten Ordner:

```bash
python -m pip install -r requirements.txt
python code/run_academic.py
python code/run_trading.py
python code/run_forecast_horizons.py
python code/summarize_results.py
python code/diagnostics.py
python code/verify.py
python code/make_report.py
```

Zum bloßen Nachsehen gespeicherte Ergebnisse lesen und nicht alles erneut rechnen. Historisch bekannte Testjahre, revidierte Quelldaten, Ausführungsnäherungen und fehlende exakte Fundamental-Vintages bleiben Grenzen. Keine universelle optimale Haltefrist oder gesicherte künftige Marktüberlegenheit gefunden.
