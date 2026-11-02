# Haltedauer und Reichweite der bisherigen Tests

Stand 02.11.2026, nach Abschluss der [Haltedauer-Folgestudie](tests/2026-11-02-holding-duration). **Die systematische vergangenheitsbasierte Intervallwahl wurde jetzt für 20 Literaturfamilien und zwölf Preisregeln durchgeführt.** Prognosemodelle wurden zusätzlich für sieben Horizonte neu gelernt. Die früheren Originaltests bleiben unverändert; die anfängliche reine Archivierung hatte noch keine neuen Renditetests gestartet.

## Was tatsächlich geprüft wurde

| Studie | Prognose/Haltung/Ausstieg | Was daraus nicht folgt |
| --- | --- | --- |
| Ursprünglicher Fünfjahres-, ATR-, 12–2-Momentum- und unabhängiger Regeltest | Maximal 20 Handelssitzungen; Limitfüllung, Stopps und Review-Regeln können die tatsächliche Haltedauer verkürzen. | 20 Tage sind nicht die ermittelte beste oder durchschnittliche Dauer jeder Strategie. |
| Globaler Nachrichtenpilot | Nächste Nachrichtenwoche bzw. relative Rendite/Aktivität der folgenden Handelswoche. | Ein negativer Wochen-Kurstest widerlegt keine unmittelbarere oder längerfristige Wirkung. |
| PCA/PLS-Faktortest | Vier Wochen primär, zwölf Wochen sekundär. | Keine vollständige Suche von Tagen bis Jahren und keine optimale Dauer je Originalstrategie. |
| Finanzielle PCA-Diagnose | Vollständiges Schließen und Neueröffnen alle vier Wochen. | Das ist eine konservative Kostenannahme, keine notwendige Handelsweise eines Signals. Bei weiter ausgewählten Titeln kann Weiterhalten Orders sparen. |
| Akademische Faktorstudien | Quellregeln der jeweiligen Faktorportfolios; Monatsrenditen und langfristige Auswertungsfenster. | Monatliche Beobachtung, Rebalancing, Haltedauer des einzelnen Titels und Anlagezeitraum sind unterschiedliche Größen. |

## Begriffe trennen

- **Signalrückblick:** Welche vergangenen Monate/Tage ein Merkmal berechnet. „12–2“ ist eine Rückblickdefinition, keine vorgeschriebene Haltedauer.
- **Prognosehorizont:** Wie weit in die Zukunft die Zielrendite gemessen wird. Ändert er sich, müssen Modell und Zielgrößen dafür neu trainiert/validiert werden.
- **Maximale Haltedauer:** Eine Ausstiegsobergrenze; bei Stopps, Review oder späterer Limitfüllung ist die realisierte Dauer kürzer.
- **Tatsächliche mittlere Haltedauer:** Erst aus Ein-/Ausstiegszeiten der konkreten Politik berechenbar. Sie ist nicht automatisch deren beste Dauer.
- **Rebalancing/Umschichtung:** Wie oft Gewichte/Signale geprüft werden. Monatliche Prüfung kann mit vielen Monaten Halten derselben Aktie vereinbar sein.
- **Ausstiegspolitik:** Fester Termin, Stopp, Signalverlust oder andere vorher definierte Regel. Verschiedene Politiken können unterschiedliche Haltedauerverteilungen erzeugen.

## Korrigierte Aussagegrenze

Die bisherigen negativen Ergebnisse gelten für die dokumentierten Daten, Märkte, Zielgrößen und Halte-/Ausstiegsregeln. Sie belegen nicht, dass jede untersuchte Grundidee bei beliebiger anderer Haltedauer nutzlos ist. Die neue Folgestudie zeigt nun große historische Renditeunterschiede bei einzelnen Preisregeln. Daraus folgt noch kein universell günstiger oder künftig garantierter Horizont.

Ein günstiger Bereich kann strategieabhängig sein; ein einziger stabiler „optimaler Mittelwert“ für alle Marktphasen oder Aktien ist nicht vorauszusetzen. Höhere kumulierte Rendite bei längerem Halten allein ist kein fairer Optimierungsmaßstab. Kapitalbindung, annualisierter Mehrertrag, Risiko, Kosten, Ausfall-/Stopprisiko und Benchmark müssen zusammen betrachtet werden.

## In der neuen Folgestudie tatsächlich umgesetzt (zuvor geplanter Schritt)

1. Pro Strategie einen kleinen begründeten Halte-/Ausstiegsraster vorab festlegen, passend zur Signal- und Datenauflösung. Rückblick, Haltedauer und Rebalancing getrennt variieren.
2. In jedem zeitlichen Lernfenster die Dauer/Politik nur anhand damals abgeschlossener Daten wählen. Auch diese Wahl liegt in einer inneren zeitlichen Validierung; der spätere Test bleibt außen vor.
3. Für jeden Horizont passende Zielrenditen, Informationspuffer, Label-Reifegrenzen und vergleichbare Benchmarks verwenden. Überlappungen und Mehrfachtests berücksichtigen.
4. Reale Umschichtungen von bloßem erneuten Signalprüfen trennen; weiter ausgewählte Titel nicht grundlos vollständig verkaufen und zurückkaufen. Feste Gebühren und angenommene Spreads transparent halten.
5. Nach Kosten auf gemeinsamen Zeiträumen, annualisiert und risikobezogen vergleichen; robuste Bereiche und Stabilität über Jahre berichten, nicht nur einen nachträglichen Spitzenwert.
6. Bekannte frühere Testergebnisse nicht als unberührte Bestätigung ausgeben. Eine positive neue historische Folgestudie braucht weitere unabhängige/prospektive Bestätigung.

## Literaturhinweis, kein aktuelles Optimum

Jegadeesh & Titman (1993) untersuchten Momentum mit Haltedauern von drei bis zwölf Monaten. Das illustriert die Bedeutung des Horizonts; es bestimmt nicht die beste Dauer unserer heutigen Strategie oder garantiert deren Rentabilität. Quelle: https://doi.org/10.1111/j.1540-6261.1993.tb04702.x .

## Ergebnisse der abgeschlossenen Folgestudie und verbleibende Grenzen

- A: Native Signal-/Portfolioaktualisierung alle 1/3/6/12 Monate, Bewertung 2014–2025, jährliche Wahl aus 120 vergangenen Monaten. Die Quelle liefert keine gemessenen individuellen Aktien-Haltedauern. Kein signifikanter zusätzlicher Intervallnutzen nach gemeinsamer Korrektur; Gross-Profit-Quality 15,01 % gegenüber Original 14,99 %, Markt 13,20 % CAGR.
- B: Zwölf Regeln mit sechs festen Intervallen von 5/10/20/60/120/252 US-Sitzungen und jährlicher Wahl aus fünf vergangenen Jahren, Bewertung 2019–2025. Signalrückblick, Kohortentakt, tatsächliche Ein-/Ausstiegstage und bloßes Prüfen/Weiterhalten werden getrennt. 1 EUR je Order plus 0,1 % je Seite. Momentum-Marktorder 19,82 % gegenüber 12,65 % bei 20 Sitzungen; Trend-Marktorder 21,57 % gegenüber 14,25 %; ACWI 13,65 %. Momentum-Weiterhalten mit 28,91 % hatte zeitweise 61,20 % in einer Position. Diese Punktwerte belegen keine gesicherte Marktüberlegenheit.
- C: Fünf Modelle, sieben neu gelernte Horizonte von 1/2/4/8/12/26/52 Wochen, identische 15.240 Aktien-Zeitpunkte 2022–2024. PCA/PLS bei allen Horizonten negatives R²; Baummodell bei 52 Wochen +10,11 % R² gegen Null-Mehrertrag. Das deskriptive 52-Wochen-Blockintervall enthält null. Keine ausgeführte finanzielle 52-Wochen-Strategie.
- Zwölf adaptive B-Pfade exakt aus eingefrorenen Eingaben reproduziert; 1211 Integritäts-/Zeit-/Reproduktionsprüfungen bestanden. Nach erster Ergebnisprüfung gefundene Ausführungsgrenze korrigiert, alle B-Varianten neu gerechnet; alte Fassung separat aufbewahrt.
- Universelle zukünftige optimale mittlere Haltedauer, prospektive Validierung und vollständige historische App-Fundamentalfilter bleiben offen. Frühere bekannte Testjahre, revidierte Daten, lange Zielüberlappungen und globale Ausführungsannahmen verhindern den Anspruch absoluter Biasfreiheit.

Neue Berechnungen nur für eine neue Frage, neue Daten oder konkrete Fehler. Zum Nachsehen Ergebnisse/Code/Daten aus dem archivierten Paket wiederverwenden.
