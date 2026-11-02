# Akademische Value-/Quality-/Investment-/Momentum-Portfolios

Status: **abgeschlossen, Aussage auf den dokumentierten Versuchsaufbau begrenzt**. Testdatum: 2026-10-31; nachträglich am 02.11.2026 im zentralen Archiv gesichert.

Langfristige Portfolio-, Kosten- und Robustheitsvergleiche; kein eigener Haltedauer-Suchlauf.

| Aspekt | Festgehaltene Definition |
| --- | --- |
| Zeitraum | Quellen ab 1963; je Auswertung andere vollständige Zeitfenster bis 2026-09 |
| Strategie/Verfahren | Zwölf vorab festgelegte akademische Faktor-/Markt-Mischungen |
| Prognose-/Auswertungshorizont | Keine individuelle Aktien-Kursprognose; langfristiger Portfoliovergleich |
| Rebalancing/Ausstieg | Quellkonventionen; Monatsrendite ist keine pauschale Einzeltitel-Haltedauer |
| Haltedauer je Strategie optimiert? | **Nein** |
| Tatsächliche mittlere Haltedauer | Hier nicht als einheitlicher Wert ermittelt; bei früheren Ausstiegen nicht mit der Obergrenze gleichsetzen. |

## Nachlesen ohne neue Berechnung

- [Originalbericht bzw. maßgebliche Ergebnisdatei](files/factor_robustness/full_factor_study.json)
- [Strukturierte Testmetadaten](test.json)
- [Datei-/Hashmanifest des vollständigen Pakets](ARTIFACT_MEMBERS.json)
- [Vollständiges Originalpaket](https://chatgpt.com/library?file_id=libfile_a7a7e430a70c81918a7eae4dddd4b40c&account_id=personal) – Zugang des Eigentümers erforderlich; umfasst auch nicht in Git abgelegte Daten-/Modell-/Trade-Dateien.

Originalpaket: `Bottleneck_Scientific_Factor_Study.zip`. SHA-256: `7e5f0c62b96fe3de496c48eee11bdc15303da7f60dbff51434b910d0d63846c0`.

Die Dateien unter `files/` sind **bytegleich aus dem bisherigen Paket übernommen**, nicht neu gerechnet. Originalkennzahlen und vollständige Vergleichstabelle vorhanden; Quelldaten-URLs im Ergebnis, ursprünglicher vollständiger Code fehlt.

## Grenzen

- Faktorportfolios sind keine direkt ausführbaren Einzeltiteltrades
- Revidierte historische Daten
- Keine umfassenden Kosten/Steuern
- Monatliche Auswertungs- und rollende Erfolgsfenster nicht mit Haltedauer verwechseln

Die Resultate widerlegen keine anders gehaltene Strategie. Signalrückblick, Prognosehorizont, maximale/tatsächliche Haltedauer, Ausstiegsregel und Umschichtungsrhythmus sind getrennte Angaben. Die Quellenportfolios können eigene unterschiedliche Bildungs-/Haltekonventionen haben.

## Daten oder Modelle wiederverwenden

Das vollständige Paket über den obigen Link lokal bereitstellen und vom Repository aus prüfen/entpacken:

```bash
python research/tools/restore_bundle.py 2026-10-31-scientific-factor-study /pfad/zum/Originalpaket.zip --destination .research_cache
```

Das verifiziert das vorhandene Paket und stellt bereits berechnete Dateien wieder her; es startet keinen Backtest. Vor einer Neuberechnung zuerst Bericht, Metadaten und Ergebnisdateien lesen. Die später ergänzte [Haltedauer-Einordnung](../../HOLDING_PERIODS.md) gehört zur Interpretation aller Studien.
