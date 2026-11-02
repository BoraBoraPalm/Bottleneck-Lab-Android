# Fünfjahres-Backtest der ursprünglichen Handelsregeln

Status: **abgeschlossen, Aussage auf den dokumentierten Versuchsaufbau begrenzt**. Testdatum: 2026-10-31; nachträglich am 02.11.2026 im zentralen Archiv gesichert.

320 Datumskohorten archiviert; heutige Überlebendenliste begrenzt die Aussage.

| Aspekt | Festgehaltene Definition |
| --- | --- |
| Zeitraum | 2021-11 bis 2026-10 |
| Strategie/Verfahren | 60-Tage-Momentum/ATR-Rang, ATR-Kauflimit und Stopp |
| Prognose-/Auswertungshorizont | 20-Handelstage-Ausstiegsannahme; 320 zufällige, teils überlappende Signaltermine |
| Rebalancing/Ausstieg | Nichtüberlappende 20-Session-Kohorten plus gesonderte überlappende Zufallstermine |
| Haltedauer je Strategie optimiert? | **Nein** |
| Tatsächliche mittlere Haltedauer | Hier nicht als einheitlicher Wert ermittelt; bei früheren Ausstiegen nicht mit der Obergrenze gleichsetzen. |

## Nachlesen ohne neue Berechnung

- [Originalbericht bzw. maßgebliche Ergebnisdatei](files/results/report.json)
- [Strukturierte Testmetadaten](test.json)
- [Datei-/Hashmanifest des vollständigen Pakets](ARTIFACT_MEMBERS.json)
- [Vollständiges Originalpaket](https://chatgpt.com/library?file_id=libfile_7f26d8bebe048191976b08afcb65337b&account_id=personal) – Zugang des Eigentümers erforderlich; umfasst auch nicht in Git abgelegte Daten-/Modell-/Trade-Dateien.

Originalpaket: `Bottleneck_Lab_5Jahre_Backtest_komplett.zip`. SHA-256: `8ee8128a914a7bc06bb7fe21b77ca627a3b73b4d46700a5814b623fc4ad578aa`.

Die Dateien unter `files/` sind **bytegleich aus dem bisherigen Paket übernommen**, nicht neu gerechnet. Originalpaket sichert Ergebnisse und Trades, aber keinen vollständigen ausführbaren Versuchscode.

## Grenzen

- Kein historisch korrektes Aktienuniversum
- Zufallstermine teils überlappend
- Keine vollständigen ursprünglichen Code-/Rohdaten im ZIP

Die Resultate widerlegen keine anders gehaltene Strategie. Signalrückblick, Prognosehorizont, maximale/tatsächliche Haltedauer, Ausstiegsregel und Umschichtungsrhythmus sind getrennte Angaben. Die Quellenportfolios können eigene unterschiedliche Bildungs-/Haltekonventionen haben.

## Daten oder Modelle wiederverwenden

Das vollständige Paket über den obigen Link lokal bereitstellen und vom Repository aus prüfen/entpacken:

```bash
python research/tools/restore_bundle.py 2026-10-31-five-year-backtest /pfad/zum/Originalpaket.zip --destination .research_cache
```

Das verifiziert das vorhandene Paket und stellt bereits berechnete Dateien wieder her; es startet keinen Backtest. Vor einer Neuberechnung zuerst Bericht, Metadaten und Ergebnisdateien lesen. Die später ergänzte [Haltedauer-Einordnung](../../HOLDING_PERIODS.md) gehört zur Interpretation aller Studien.
