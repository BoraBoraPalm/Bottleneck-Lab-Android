# PCA/PLS und gemeinsame historische Faktor-Zustände

Status: **abgeschlossen, Aussage auf den dokumentierten Versuchsaufbau begrenzt**. Testdatum: 2026-11-02; nachträglich am 02.11.2026 im zentralen Archiv gesichert.

Bei vier Wochen kein Modell mit geringerem MSE als Null-Mehrertragsprognose; zwölf Wochen ohne besseren Gesamt-MSE.

| Aspekt | Festgehaltene Definition |
| --- | --- |
| Zeitraum | Vorwärtsprognosen 2022 bis September 2025; expandierendes Training ab 2019 |
| Strategie/Verfahren | 44 Merkmale; Preis-Ridge, Gesamt-Ridge, Elastic Net, PCA, PLS, kleines Boosting; Zusatz mit 24 Faktorindikatoren |
| Prognose-/Auswertungshorizont | Vier Wochen primär, zwölf Wochen deskriptiv |
| Rebalancing/Ausstieg | Finanzdiagnose: alle vier Wochen vollständiges Schließen und Neueröffnen; keine umsatzsparende Signalhaltung |
| Haltedauer je Strategie optimiert? | **Nein** |
| Tatsächliche mittlere Haltedauer | Hier nicht als einheitlicher Wert ermittelt; bei früheren Ausstiegen nicht mit der Obergrenze gleichsetzen. |

## Nachlesen ohne neue Berechnung

- [Originalbericht bzw. maßgebliche Ergebnisdatei](files/output/bericht.md)
- [Strukturierte Testmetadaten](test.json)
- [Datei-/Hashmanifest des vollständigen Pakets](ARTIFACT_MEMBERS.json)
- [Vollständiges Originalpaket](https://chatgpt.com/library?file_id=libfile_e1d24544f9808191bdfc75b76d32962a&account_id=personal) – Zugang des Eigentümers erforderlich; umfasst auch nicht in Git abgelegte Daten-/Modell-/Trade-Dateien.

Originalpaket: `PCA_Faktoren_Gesamtstudie_2026.zip`. SHA-256: `4ddd8f16666541a06abe8e9cf795864dbb17d48c2244279e2f58c3049ad92400`.

Die Dateien unter `files/` sind **bytegleich aus dem bisherigen Paket übernommen**, nicht neu gerechnet. Vollständiger Code, Modelle, Zeit-/Reproduktionsprüfungen und Roh-/Eingabesnapshots im Vollpaket vorhanden.

## Grenzen

- Keine Strategie-spezifische Haltedauer-Suche
- Vollständige Vierwochen-Rundläufe sind konservative Kostenannahme
- Fehlende Fundamental-Vintages
- Bekannte historische Testjahre; nur Großkonzern-Kohorte

Die Resultate widerlegen keine anders gehaltene Strategie. Signalrückblick, Prognosehorizont, maximale/tatsächliche Haltedauer, Ausstiegsregel und Umschichtungsrhythmus sind getrennte Angaben. Die Quellenportfolios können eigene unterschiedliche Bildungs-/Haltekonventionen haben.

## Daten oder Modelle wiederverwenden

Das vollständige Paket über den obigen Link lokal bereitstellen und vom Repository aus prüfen/entpacken:

```bash
python research/tools/restore_bundle.py 2026-11-02-pca-factor-states /pfad/zum/Originalpaket.zip --destination .research_cache
```

Das verifiziert das vorhandene Paket und stellt bereits berechnete Dateien wieder her; es startet keinen Backtest. Vor einer Neuberechnung zuerst Bericht, Metadaten und Ergebnisdateien lesen. Die später ergänzte [Haltedauer-Einordnung](../../HOLDING_PERIODS.md) gehört zur Interpretation aller Studien.
