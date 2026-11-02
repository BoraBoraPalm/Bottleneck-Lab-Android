# Internationales Stimmungsmodell – Pilotversuch

Bericht zuerst öffnen: `output/bericht.html` (selbständig, offline), alternativ `output/bericht.md`.

Die App wurde nicht verändert. Dies ist Forschung mit historischen Daten, kein einsatzbereites Handelssystem.

## Reproduktion ohne erneuten Download

Python 3.12, Versionsstände in requirements.txt. Nach Installation der Pakete im Verzeichnis dieses Projekts:

```bash
python model.py
python verify.py
python robustness.py
python joint_forecast.py
python report.py
```

model.py passt die sechs Kategorien und die primären Modelle nur auf 2019–2021 an. 2022 dient der Diagnose; 2023–2025 ist der Test. Die beiden letzten Modellscripte sind zusätzliche Diagnosen, die erst nach Sichtung der primären Resultate hinzugefügt wurden. Das primäre Kandidatenmodell wurde danach nicht optimiert. Das Verfügbarkeitsmodell in joint_forecast.py berücksichtigt auch ausbleibende Messbarkeit in der Folgewoche.

`data/news_sample.parquet` enthält die verwendete Metadaten-Stichprobe. `data/prices/*.json` sind die Kurs-/FX-Snapshots; `data/price_panel.parquet` und `data/news_features.parquet` sind daraus erzeugte Zwischenwerte. `output/test_predictions.parquet` und `output/joint_state_predictions.parquet` erlauben unabhängige Auswertungen der fixierten Vorhersagen. Die gespeichert geladenen Modelle (joblib) nur aus vertrauenswürdiger Quelle öffnen.

## Optionaler frischer Quellenabruf

```bash
python prices.py
python collect.py
```

collect.py lädt ungefähr 7,7 GB öffentliche komprimierte Archivdaten und behält nur die Firmen-Metadaten (keine Volltexte). Roharchive sind wegen Größe nicht enthalten. Für einen vollständigen Neuabruf ein neues Projektverzeichnis mit den Skripten und leerem data-Verzeichnis verwenden; mitgelieferte Originaldaten zuvor behalten. Yahoo-Daten und historische Unternehmens- bzw. Devisenzuordnungen können sich ändern; neu geladene Ergebnisse müssen nicht exakt der Aufnahme vom 01.11.2026 entsprechen.

Der Datensatz ist eine feste 15-Minuten-Stichprobe pro Woche, kein vollständiger Nachrichtenstrom. Unzureichende Nachrichten erhalten Zustand -1, keine neutrale Stimmung. Die bedingte Stimmungsvorhersage erfordert in beiden Wochen genügend Messungen; die gemeinsame Zusatzdiagnose behandelt fehlende Folgemessungen explizit.

Protokoll und zwei zeitliche Lock-Dateien dokumentieren die Konfiguration vor dem ersten Zieltest. Die zweite Lock-Version korrigiert fehlende Spracharchive und südafrikanische Centkurse. Sie erfolgte vor Einsicht in Modelltestkennzahlen. Alle primären Quellhashes werden von verify.py geprüft.

Keine Handelskosten oder Portfoliorenditen wurden getestet. Datenabdeckung, Bias-Risiken, regionale Grenzen und Quellen stehen im Bericht und in sources.md.
