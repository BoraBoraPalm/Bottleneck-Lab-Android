# Globaler Nachrichtenstimmungs-Pilot

Status: **abgeschlossen, Aussage auf den dokumentierten Versuchsaufbau begrenzt**. Testdatum: 2026-11-01; nachträglich am 02.11.2026 im zentralen Archiv gesichert.

Bessere Nachrichtenkategorien-Prognose; kein zusätzlicher zuverlässiger Kursrichtungsvorteil im Wochenziel.

| Aspekt | Festgehaltene Definition |
| --- | --- |
| Zeitraum | Lernen 2019–2021, Diagnose 2022, Test 2023–2025 |
| Strategie/Verfahren | Sechs Nachrichtenmuster, Prognose der Folgekategorie sowie relativer Rendite und Handelsaktivität |
| Prognose-/Auswertungshorizont | Nächste Archivwoche bzw. folgende Handelswoche |
| Rebalancing/Ausstieg | Kein validiertes Handelsportfolio; Wochen-Zielgrößen mit Informationspuffer |
| Haltedauer je Strategie optimiert? | **Nein** |
| Tatsächliche mittlere Haltedauer | Hier nicht als einheitlicher Wert ermittelt; bei früheren Ausstiegen nicht mit der Obergrenze gleichsetzen. |

## Nachlesen ohne neue Berechnung

- [Originalbericht bzw. maßgebliche Ergebnisdatei](files/output/bericht.md)
- [Strukturierte Testmetadaten](test.json)
- [Datei-/Hashmanifest des vollständigen Pakets](ARTIFACT_MEMBERS.json)
- [Vollständiges Originalpaket](https://chatgpt.com/library?file_id=libfile_f3dbb35d015c8191856387bb0bb2ff16&account_id=personal) – Zugang des Eigentümers erforderlich; umfasst auch nicht in Git abgelegte Daten-/Modell-/Trade-Dateien.

Originalpaket: `Stimmungsmodell_Globaler_Pilot_2026.zip`. SHA-256: `6710f7fbf0580491a4329548fc0d472400e0efd670527797e23290c0fe1f93a8`.

Die Dateien unter `files/` sind **bytegleich aus dem bisherigen Paket übernommen**, nicht neu gerechnet. Vollständiges Modellpaket mit Metadaten-/Kurs-Snapshots, Code, Vorhersagen und Prüfungen verfügbar.

## Grenzen

- Wöchentliche 15-Minuten-Stichprobe statt vollständigem Nachrichtenstrom
- Artikelton ist keine direkte Anlegeremotion
- Dünne und regional ungleiche Abdeckung
- Kein Haltehorizont-Vergleich von Stunden bis Monaten

Die Resultate widerlegen keine anders gehaltene Strategie. Signalrückblick, Prognosehorizont, maximale/tatsächliche Haltedauer, Ausstiegsregel und Umschichtungsrhythmus sind getrennte Angaben. Die Quellenportfolios können eigene unterschiedliche Bildungs-/Haltekonventionen haben.

## Daten oder Modelle wiederverwenden

Das vollständige Paket über den obigen Link lokal bereitstellen und vom Repository aus prüfen/entpacken:

```bash
python research/tools/restore_bundle.py 2026-11-01-global-sentiment /pfad/zum/Originalpaket.zip --destination .research_cache
```

Das verifiziert das vorhandene Paket und stellt bereits berechnete Dateien wieder her; es startet keinen Backtest. Vor einer Neuberechnung zuerst Bericht, Metadaten und Ergebnisdateien lesen. Die später ergänzte [Haltedauer-Einordnung](../../HOLDING_PERIODS.md) gehört zur Interpretation aller Studien.
