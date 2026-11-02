# 12–2-Momentum gegen ursprüngliches Momentum/ATR-Modell

Status: **abgeschlossen, Aussage auf den dokumentierten Versuchsaufbau begrenzt**. Testdatum: 2026-10-31; nachträglich am 02.11.2026 im zentralen Archiv gesichert.

12–2 bezeichnet den Signalrückblick, keine zwölfmonatige Haltedauer.

| Aspekt | Festgehaltene Definition |
| --- | --- |
| Zeitraum | 2021–2026 |
| Strategie/Verfahren | Ursprünglicher 60-Tage-Score versus 12–2-Rückblick-Rang |
| Prognose-/Auswertungshorizont | 20-Handelstage-Ausstieg bei identischen weiteren Bedingungen |
| Rebalancing/Ausstieg | Gemeinsame 20-Session-Handelsannahme |
| Haltedauer je Strategie optimiert? | **Nein** |
| Tatsächliche mittlere Haltedauer | Hier nicht als einheitlicher Wert ermittelt; bei früheren Ausstiegen nicht mit der Obergrenze gleichsetzen. |

## Nachlesen ohne neue Berechnung

- [Originalbericht bzw. maßgebliche Ergebnisdatei](files/momentum_results/momentum_model_comparison.json)
- [Strukturierte Testmetadaten](test.json)
- [Datei-/Hashmanifest des vollständigen Pakets](ARTIFACT_MEMBERS.json)
- [Vollständiges Originalpaket](https://chatgpt.com/library?file_id=libfile_9411fbe17e5081918573115989254416&account_id=personal) – Zugang des Eigentümers erforderlich; umfasst auch nicht in Git abgelegte Daten-/Modell-/Trade-Dateien.

Originalpaket: `Bottleneck_Momentum_12_2_Research.zip`. SHA-256: `013d84f9ebfac711c851b659bf74b15a115d4a810d50c2e5bde08ee1079e2192`.

Die Dateien unter `files/` sind **bytegleich aus dem bisherigen Paket übernommen**, nicht neu gerechnet. Vergleichsresultate und Kurven archiviert; damaliger kompletter Code nicht mitgeliefert.

## Grenzen

- Aktuelle Überlebendenliste
- Kein gesondertes 3-/6-/12-Monats-Halteexperiment
- Kein vollständiger ursprünglicher Versuchscode im ZIP

Die Resultate widerlegen keine anders gehaltene Strategie. Signalrückblick, Prognosehorizont, maximale/tatsächliche Haltedauer, Ausstiegsregel und Umschichtungsrhythmus sind getrennte Angaben. Die Quellenportfolios können eigene unterschiedliche Bildungs-/Haltekonventionen haben.

## Daten oder Modelle wiederverwenden

Das vollständige Paket über den obigen Link lokal bereitstellen und vom Repository aus prüfen/entpacken:

```bash
python research/tools/restore_bundle.py 2026-10-31-momentum-12-2 /pfad/zum/Originalpaket.zip --destination .research_cache
```

Das verifiziert das vorhandene Paket und stellt bereits berechnete Dateien wieder her; es startet keinen Backtest. Vor einer Neuberechnung zuerst Bericht, Metadaten und Ergebnisdateien lesen. Die später ergänzte [Haltedauer-Einordnung](../../HOLDING_PERIODS.md) gehört zur Interpretation aller Studien.
