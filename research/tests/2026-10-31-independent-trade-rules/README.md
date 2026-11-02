# Unabhängiger Vergleich der aktuellen Ein-/Ausstiegsregeln

Status: **abgeschlossen, Aussage auf den dokumentierten Versuchsaufbau begrenzt**. Testdatum: 2026-10-31; nachträglich am 02.11.2026 im zentralen Archiv gesichert.

Ein-/Ausstiegsregeln bei gleicher maximaler Dauer verglichen; keine optimierte Dauer je Strategie.

| Aspekt | Festgehaltene Definition |
| --- | --- |
| Zeitraum | 2021-11 bis 2026-10 |
| Strategie/Verfahren | Sieben Momentum-, Limit-, Stop- und Review-Varianten |
| Prognose-/Auswertungshorizont | Maximal 20 Sessions; zehn gleich große Kapitalsitze |
| Rebalancing/Ausstieg | Nichtüberlappende 20-Session-Kohorten mit früheren Ausstiegen |
| Haltedauer je Strategie optimiert? | **Nein** |
| Tatsächliche mittlere Haltedauer | Hier nicht als einheitlicher Wert ermittelt; bei früheren Ausstiegen nicht mit der Obergrenze gleichsetzen. |

## Nachlesen ohne neue Berechnung

- [Originalbericht bzw. maßgebliche Ergebnisdatei](files/current_rules_results/current_trading_rules_report.json)
- [Strukturierte Testmetadaten](test.json)
- [Datei-/Hashmanifest des vollständigen Pakets](ARTIFACT_MEMBERS.json)
- [Vollständiges Originalpaket](https://chatgpt.com/library?file_id=libfile_c3afd081f67881918a9b714611ad5457&account_id=personal) – Zugang des Eigentümers erforderlich; umfasst auch nicht in Git abgelegte Daten-/Modell-/Trade-Dateien.

Originalpaket: `Bottleneck_Trading_Rules_Independent_2026.zip`. SHA-256: `6912b52f3f32787ba9095d839e2dc3a92fd4716f18ddcaaccbf6b236ff5e8f43`.

Die Dateien unter `files/` sind **bytegleich aus dem bisherigen Paket übernommen**, nicht neu gerechnet. Ergebnisse und Trade-Details im Vollpaket. Ein verwandter festgehaltener Code im Repository ist verlinkt; seine Bitidentität mit dem Original-Lauf wird nicht behauptet.

## Grenzen

- Heutige überlebende Titel
- Bekannte historische Testjahre
- Historische Brokerverfügbarkeit/Spreads unvollständig

Die Resultate widerlegen keine anders gehaltene Strategie. Signalrückblick, Prognosehorizont, maximale/tatsächliche Haltedauer, Ausstiegsregel und Umschichtungsrhythmus sind getrennte Angaben. Die Quellenportfolios können eigene unterschiedliche Bildungs-/Haltekonventionen haben.

## Daten oder Modelle wiederverwenden

Das vollständige Paket über den obigen Link lokal bereitstellen und vom Repository aus prüfen/entpacken:

```bash
python research/tools/restore_bundle.py 2026-10-31-independent-trade-rules /pfad/zum/Originalpaket.zip --destination .research_cache
```

Das verifiziert das vorhandene Paket und stellt bereits berechnete Dateien wieder her; es startet keinen Backtest. Vor einer Neuberechnung zuerst Bericht, Metadaten und Ergebnisdateien lesen. Die später ergänzte [Haltedauer-Einordnung](../../HOLDING_PERIODS.md) gehört zur Interpretation aller Studien.

## Verwandter Quellcode im Repository

[Festgehaltener Skriptstand vom Archiv-Basiscommit](https://github.com/BoraBoraPalm/Bottleneck-Lab-Android/blob/3db66d587173799d6fc3a0ac8cdedbc03b4d3dda/research/evaluate_current_trade_rules.py). Dieser Bezug ersetzt keinen Nachweis der vollständigen ursprünglichen Laufumgebung.
