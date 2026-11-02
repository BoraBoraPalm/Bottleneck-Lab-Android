# Behavioral-/Informationsstrategien gegen US-Markt

Status: **abgeschlossen, Aussage auf den dokumentierten Versuchsaufbau begrenzt**. Testdatum: 2026-11-01; nachträglich am 02.11.2026 im zentralen Archiv gesichert.

Für die festgelegten Portfoliovarianten kein robuster Überlegenheitsnachweis gegen den US-Markt.

| Aspekt | Festgehaltene Definition |
| --- | --- |
| Zeitraum | 2000–2025 |
| Strategie/Verfahren | Momentum, Earnings Surprise, Analystenrevisionen, Announcement Return; alle sechs Paare und weitere Kontrollen |
| Prognose-/Auswertungshorizont | Vergleich fester Quellenportfolios; keine individuelle Aktien-Prognose |
| Rebalancing/Ausstieg | Quellkonventionen und vorab feste Mischungen; Monatsbeobachtungen sind keine einheitliche Aktien-Haltedauer |
| Haltedauer je Strategie optimiert? | **Nein** |
| Tatsächliche mittlere Haltedauer | Hier nicht als einheitlicher Wert ermittelt; bei früheren Ausstiegen nicht mit der Obergrenze gleichsetzen. |

## Nachlesen ohne neue Berechnung

- [Originalbericht bzw. maßgebliche Ergebnisdatei](files/REPORT.md)
- [Strukturierte Testmetadaten](test.json)
- [Datei-/Hashmanifest des vollständigen Pakets](ARTIFACT_MEMBERS.json)
- [Vollständiges Originalpaket](https://chatgpt.com/library?file_id=libfile_eb7efca016688191a682289a9e09e551&account_id=personal) – Zugang des Eigentümers erforderlich; umfasst auch nicht in Git abgelegte Daten-/Modell-/Trade-Dateien.

Originalpaket: `Behavioral_Strategien_Benchmark_2026.zip`. SHA-256: `64cdb711abfe1a3eb2046269480fcd1ec76d9a24a716396800bf28b47a8998bf`.

Die Dateien unter `files/` sind **bytegleich aus dem bisherigen Paket übernommen**, nicht neu gerechnet. Skripte, monatliche Eingaben, Protokoll und Ergebnisse verfügbar; genaue Quellenregeln erhalten.

## Grenzen

- Quellen-Vintages und Anpassungen
- Illustrative jährliche Kosten statt tatsächlichem Orderfluss
- Keine eigene Dauerwahl für jede Originalstrategie

Die Resultate widerlegen keine anders gehaltene Strategie. Signalrückblick, Prognosehorizont, maximale/tatsächliche Haltedauer, Ausstiegsregel und Umschichtungsrhythmus sind getrennte Angaben. Die Quellenportfolios können eigene unterschiedliche Bildungs-/Haltekonventionen haben.

## Daten oder Modelle wiederverwenden

Das vollständige Paket über den obigen Link lokal bereitstellen und vom Repository aus prüfen/entpacken:

```bash
python research/tools/restore_bundle.py 2026-11-01-behavioral-benchmark /pfad/zum/Originalpaket.zip --destination .research_cache
```

Das verifiziert das vorhandene Paket und stellt bereits berechnete Dateien wieder her; es startet keinen Backtest. Vor einer Neuberechnung zuerst Bericht, Metadaten und Ergebnisdateien lesen. Die später ergänzte [Haltedauer-Einordnung](../../HOLDING_PERIODS.md) gehört zur Interpretation aller Studien.
