# ATR-Kauflimit-/Stopp-Sensitivität

Status: **abgeschlossen, Aussage auf den dokumentierten Versuchsaufbau begrenzt**. Testdatum: 2026-10-31; nachträglich am 02.11.2026 im zentralen Archiv gesichert.

Kauf-/Stoppabstände variiert; die maximale Haltedauer wurde nicht variiert.

| Aspekt | Festgehaltene Definition |
| --- | --- |
| Zeitraum | 2021–2026 mit zeitlichem Trainings-/Testabschnitt |
| Strategie/Verfahren | 20 festgelegte Buy-ATR-/Stop-ATR-Kombinationen |
| Prognose-/Auswertungshorizont | 20-Handelstage-Tradeversuch |
| Rebalancing/Ausstieg | 20-Session-Kohorten; ATR-Stopp kann früher schließen |
| Haltedauer je Strategie optimiert? | **Nein** |
| Tatsächliche mittlere Haltedauer | Hier nicht als einheitlicher Wert ermittelt; bei früheren Ausstiegen nicht mit der Obergrenze gleichsetzen. |

## Nachlesen ohne neue Berechnung

- [Originalbericht bzw. maßgebliche Ergebnisdatei](files/limits_results/threshold_summary.json)
- [Strukturierte Testmetadaten](test.json)
- [Datei-/Hashmanifest des vollständigen Pakets](ARTIFACT_MEMBERS.json)
- [Vollständiges Originalpaket](https://chatgpt.com/library?file_id=libfile_e4ca48b909fc819186a4bc128f46a91d&account_id=personal) – Zugang des Eigentümers erforderlich; umfasst auch nicht in Git abgelegte Daten-/Modell-/Trade-Dateien.

Originalpaket: `Bottleneck_Lab_ATR_Grenzen_Sensitivitaet.zip`. SHA-256: `87fd42d218749448dd957b68aec95fb979f0062ba6d0adfd6f755271414933b2`.

Die Dateien unter `files/` sind **bytegleich aus dem bisherigen Paket übernommen**, nicht neu gerechnet. Ergebnisse aller 20 Varianten vorhanden; vollständiger damaliger Versuchscode fehlt im ZIP.

## Grenzen

- Aktuelle überlebende US-Aktien statt damaliger Mitgliedschaften
- Historische Brokerhandelbarkeit unbekannt
- Kein vollständiger damaliger Quellcode im Paket

Die Resultate widerlegen keine anders gehaltene Strategie. Signalrückblick, Prognosehorizont, maximale/tatsächliche Haltedauer, Ausstiegsregel und Umschichtungsrhythmus sind getrennte Angaben. Die Quellenportfolios können eigene unterschiedliche Bildungs-/Haltekonventionen haben.

## Daten oder Modelle wiederverwenden

Das vollständige Paket über den obigen Link lokal bereitstellen und vom Repository aus prüfen/entpacken:

```bash
python research/tools/restore_bundle.py 2026-10-31-atr-limits-stops /pfad/zum/Originalpaket.zip --destination .research_cache
```

Das verifiziert das vorhandene Paket und stellt bereits berechnete Dateien wieder her; es startet keinen Backtest. Vor einer Neuberechnung zuerst Bericht, Metadaten und Ergebnisdateien lesen. Die später ergänzte [Haltedauer-Einordnung](../../HOLDING_PERIODS.md) gehört zur Interpretation aller Studien.
