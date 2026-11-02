# Einmalige Prüfung verhaltensbasierter Aktienstrategien

Öffne **REPORT.html** für den vollständigen deutschsprachigen Bericht mit Grafik.
Er benötigt keine Internetverbindung und verändert keine App. **REPORT.md** ist
derselbe Bericht als Text. Das Ergebnis ist eine historische Forschungsprüfung,
keine Garantie künftiger Markterträge.

## Ergebnis auf einen Blick

Für die vier psychologisch/informationsbezogen motivierten Signale und ihre
festen Kombinationen ist kein statistisch gesicherter Marktvorsprung nachgewiesen.
EPS-Überraschungen und ihr einfacher Mix mit Analystenrevisionen sind die besten
psychologischen Kandidaten dieser Auswahl. Der Quality-Kontrollansatz ist im
Hauptfenster risikobereinigt numerisch am stärksten, ebenfalls ohne gesicherten
Vorteil. Mehr Signale und ein Wechsel zur zuletzt besten Strategie halfen nicht.

## Reproduzieren

Python 3.12 verwenden; Paketversionen stehen in `environment.json`.

```bash
python -m pip install -r requirements.txt
python run_study.py
python supplement.py
python make_report.py
```

Die kompakten ausgewählten Originalrenditen in `output/*_inputs.csv` reichen für
die komplette Neuberechnung der Kennzahlen, Tests und Abbildungen. Der Runner
erkennt automatisch, ob die großen ursprünglichen Parquet-Dateien fehlen, und
verwendet dann diese ausgewählten Tabellen. Es werden keine Renditen simuliert
oder fehlende Aktienrenditen erfunden.

Für einen vollständigen erneuten Parse der größeren Originalportfoliodateien:

```bash
python download_data.py
python run_study.py
python supplement.py
python make_report.py
```

Der optionale Download ist mit SHA-256 abgesichert. Später veränderte Quellen
werden nicht stillschweigend als ursprünglicher Datenstand akzeptiert.

## Inhalt

- `protocol.json`: vor Auswertung fixierte Signale, Kombinationen, Perioden,
  Kostenannahmen und Unsicherheitsverfahren.
- `run_study.py`: Datenprüfung, Renditen, Risiko, Kosten, HAC, Holm, gepaarter
  Block-Bootstrap, chronologische Auswahl und Walk-forward.
- `supplement.py`: nach dem Hauptlauf hinzugefügte, ausdrücklich explorative
  unabhängige monatliche Momentum-Kontrolle und gemeinsame EUR-Umrechnung.
- `make_report.py`: unabhängige Arithmetikprüfungen, Grafiken und Bericht.
- `output/results.json`: vollständige Ergebnisse aller Konstruktionen und Kosten.
- `output/supplement.json`: alle ergänzenden Kontrollergebnisse.
- `output/*_inputs.csv`: tatsächlich verwendete Quellrenditen, nicht nur Endwerte.
- `output/*_gross_sleeves.csv`: alle festen Kandidaten vor Kostenabschlag.
- `output/wealth_net_1pct.csv`: vollständige Vermögenspfade bei 1%-Szenario.
- `output/comparison.png`: eigenständige Grafik.
- `data/sources.json`: Original-URLs, Dateigrößen und Prüfsummen.
- `source_audit.md`: nachvollziehbare Befunde zu Datenverfügbarkeit und Konstruktion.
- `CHECKSUMS.sha256`: Prüfsummen des vollständigen kompakten Pakets.

## Daten und Rechte

Primäre Daten: Chen, Andrew Y. und Tom Zimmermann (2022), *Open Source
Cross-Sectional Asset Pricing*, Critical Finance Review 11(2), 207–264.
Ausgabe Oktober 2026, Daten bis Dezember 2025, Datensatz unter CC BY 4.0:
https://www.openassetpricing.com/data/

Benchmark/Risikofaktoren und unabhängige Momentum-Kontrolle:
Kenneth French Data Library:
https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/data_library.html

Wechselkurse: Frankfurter, gemischte Referenz-Mittelkurse offizieller Quellen:
https://frankfurter.dev/

Die originalen externen Quellcodes werden nicht im Paket weiterverteilt;
`source_audit.md` verweist auf den genau geprüften öffentlichen Commit.

## Wichtige Grenzen

Die Quellen verwenden revidierte Historien und festgelegte Verfügbarkeitslags.
Ein vollständiger damaliger Datenschnappschuss-Audit fehlt. Die Untersuchung ist
retrospektiv, die Signale sind aus der Literatur bekannt. Kosten sind Szenarien,
keine vollständig gemessenen Ausführungskosten; österreichische Steuern fehlen.
Die Monatsend-Einbrüche erfassen keine zusätzlichen Verluste innerhalb eines
Monats. Alle Details und nicht getesteten Sentiment-Ansätze stehen im Bericht.

Keine Änderung der App und keine laufende Automatisierung.
