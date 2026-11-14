# Protokoll: Strategie-Audit und Suche nach verlässlicher Outperformance

Festgelegt am 14.11.2026, **bevor** Daten dieser Studie geladen oder ausgewertet wurden. Spätere Änderungen stehen unten unter „Änderungen nach Festlegung“ und sind dort als explorativ markiert.

## Frage

1. Sind die neun Strategien der App und ihre Ein-/Ausstiegsregeln durch historische Daten gestützt?
2. Schlagen andere bekannte Strategien den Markt?
3. Gibt es eine Methode, die den Markt statistisch **verlässlich** übertrifft, nach Kosten und österreichischer Steuer?

## Vorwissen (keine unberührte Prüfung)

Die Fachliteratur und die acht früheren Studien dieses Archivs sind bekannt, darunter: Momentum und Quality/Value/Momentum-Mischungen lagen 1965–1999 deutlich vor dem US-Markt, seit 2000 nicht mehr statistisch gesichert. Alle historischen Jahre sind bekannt. Ein positives Ergebnis wäre deshalb ein Hinweis, kein Beweis für die Zukunft.

## Daten

| Quelle | Inhalt | Verwendung |
| --- | --- | --- |
| Kenneth French Data Library | US-Portfolios (CRSP, ohne Überlebensverzerrung) ab 1926/1963, Branchen (täglich), Regionen ab 1990 | Faktor-Portfolios, Markt, Branchenrotation, Timing |
| Open Source Asset Pricing (Chen/Zimmermann), Stand ad1dfba5 wie Studie 2026-11-01 | 212 veröffentlichte Signale, wertgewichtete Fünftel, bis 2025-12 | Audit der App-Strategien, breite Suche |
| Yahoo Finance (bereinigte Tageskurse) | ETFs und Fonds | Echte Produkte seit Auflage, Anlageklassen-Regeln |

Abruf über GitHub Actions; jede Datei mit SHA-256 im Manifest. French- und Yahoo-Daten werden vom Anbieter laufend revidiert.

## Vergleichsmaßstab und Kennzahlen

- Benchmark: US-Gesamtmarkt (French Mkt-RF + RF); Regionen gegen den jeweiligen French-Regionenmarkt; ETFs gegen SPY, EFA bzw. EUNL.DE in gleicher Währung. Der relative Abstand zweier Anlagen gleicher Währung ist in Euro derselbe.
- Hauptmaß: mittlere monatliche Log-Mehrrendite gegenüber dem Benchmark, annualisiert, **nach Kosten**; t-Wert nach Newey-West (12 Monatsverzögerungen); einseitiger p-Wert für „besser als der Markt“.
- Zusätzlich: Rendite p. a., Schwankung, Sharpe, größter Einbruch (Monatsende), CAPM-Alpha, Anteil rollierender 5-/10-/20-Jahres-Fenster mit Vorsprung, Break-even-Kosten.
- Mehrfachtests: Holm-Korrektur über **alle** in dieser Studie bewerteten Strategien; für die Signal-Suche zusätzlich Benjamini-Hochberg.

## Kosten

- Selbst gebaute Regeln (Timing, Branchenrotation, Anlageklassen): tatsächlicher Umschlag × 0,1 % je Seite.
- Fertige Quellportfolios ohne Umschlagsangabe (French, OSAP): pauschal 1,0 % p. a. bei monatlicher, 0,5 % p. a. bei viertel-/halbjährlicher, 0,3 % p. a. bei jährlicher Neubildung; kurzfristige Umkehr 3,0 % p. a.; Nebenwerte-Portfolios doppelt. Sensitivität 0 % und 2 % p. a.

## Steuer (Österreich, Modell)

KESt 27,5 % auf Dividenden (Annahme 2 % p. a.) und realisierte Kursgewinne; Verlustausgleich nur im selben Kalenderjahr; Endverkauf versteuert. Angenommener jährlicher Umschlag: 30 % (jährliche Neubildung), 100 % (viertel-/halbjährlich), 200 % (monatlich); Timing-Regeln exakt. Benchmark: Kaufen und Halten. Ausgewiesen als Steuerhürde und als Endvermögen nach Steuer über rollierende 20-Jahres-Fenster.

## Zeiträume

US gesamt ab 1963-07 (kursbasierte Regeln zusätzlich ab 1927). **Kontrollzeitraum:** ab 2000-01, bei veröffentlichten Signalen ab dem Jahr nach der Veröffentlichung, falls später. **Jüngster Zeitraum:** letzte 180 Monate.

## Module (vollständige Liste, vorab)

**A – Audit der App-Strategien** über die nächstliegenden veröffentlichten Long-only-Portfolios: Momentum (French Prior 12–2, OSAP Mom12m), geringe Schwankung (French VAR/RESVAR/BETA, OSAP IdioVol3F, RealizedVol, MaxRet), Trend (OSAP TrendFactor, High52, Mom6m), Hoch-Tief-Mut (French Langfrist-/Kurzfrist-Verlierer, OSAP LRreversal, MRreversal, STreversal, Gegenseite von High52), Frühwachstum (OSAP RevenueSurprise, NumEarnIncrease, EarningsStreak, MeanRankRevGrowth), Quality (French OP, OSAP GP), Value (French BE/ME, E/P, CF/P, OSAP BM), Gewinnmomentum (OSAP EarningsSurprise, AnnouncementReturn, REV6), Bilanzwachstum (French INV, OSAP AssetGrowth).

**B – Breite Suche** über alle 212 OSAP-Signale (oberstes wertgewichtetes Fünftel): Gesamtzeitraum, Stichprobe der Originalarbeit, Zeit nach Veröffentlichung. Dazu der Test „in der Vergangenheit beste Strategien auswählen“: jedes Jahresende die 5/10/20 Signale mit dem höchsten t-Wert der letzten 10/15/20 Jahre gleichgewichtet für zwölf Monate halten (neun Varianten, ab 1980), einmal nur mit damals schon veröffentlichten Signalen. Dazu die Gleichgewichtung aller veröffentlichten Signale.

**C1 – Markt-Timing** (US-Markt täglich ab 1926, Signal nach Schluss, Handel am Folgetag): 200-Tage-Linie; 10-Monats-Linie; 12-Monats-Momentum gegen T-Bills; die Ein-/Ausstiegsregel der App; Schwankungssteuerung (ohne und mit Hebel 1,5); Halloween; Monatswechsel.

**C2 – Branchenrotation** (30 French-Branchen täglich ab 1926, je 6 Branchen gleichgewichtet, monatlich): Momentum 12–2, 12–1, 6–1; Abstand zur 200-Tage-Linie; geringe Schwankung; Nähe zum 52-Wochen-Hoch; Rückgang 15–55 % vom Hoch; Momentum je Schwankung; App-Mix aus Momentum, Trend und Schwankung; jede Branche nur über ihrer 200-Tage-Linie; Momentum mit T-Bill-Filter. Für Momentum 12–2, Trend, Schwankung und App-Mix zusätzlich viertel- und jährliche Umschichtung.

**C3 – Faktor-Mischungen** (French, US): Einzelportfolios für Momentum, Value, Quality, Investment, geringe Schwankung, Größe, Dividende, Gewinn-/Cashflow-Rendite, Aktienrückkäufe, Accruals, Umkehr; Mischungen QVM, QVM + Schwankung, Momentum + Schwankung, Quality + Momentum, Value + Momentum, Fünfer-Mix, Momentum bzw. QVM mit 10-Monats-Filter, Faktor-Momentum. Wiederholung für Industrieländer ohne USA, Europa, Japan, Asien-Pazifik, Nordamerika, Schwellenländer.

**C4 – Anlageklassen** (Indexfonds über Yahoo): Global Equities Momentum (Antonacci), GTAA mit 10-Monats-Linie (Faber), 60/40.

**C5 – Echte Faktor-Produkte seit Auflage**: vorab festgelegte Liste aus US-, internationalen und UCITS-ETFs/Fonds gegen SPY, EFA bzw. EUNL.DE. Geschlossene Produkte fehlen (begünstigt die Strategien).

## „Verlässlich“: vorab festgelegte Kriterien

- **K1** Gesamtzeitraum: Mehrrendite nach Kosten > 0, einseitiger p-Wert nach Holm < 0,05.
- **K2** Kontrollzeitraum: Mehrrendite nach Kosten > 0, einseitiger p-Wert < 0,05.
- **K3** Vorsprung in ≥ 80 % der rollierenden 10-Jahres-Fenster und in ≥ 60 % der Fenster, die 2010 oder später enden.
- **K4** Mehrrendite nach Kosten > 0 in den letzten 180 Monaten.
- **K5** Soweit Daten vorhanden: außerhalb der USA Mehrrendite > 0 mit p < 0,10.
- **K6** Nach Steuer-Modell: Median des 20-Jahres-Endvermögens über dem Benchmark.

Einstufung: **verlässlich** = K1–K4 und K6 (und K5, wenn prüfbar). **Hinweise, nicht verlässlich** = K1, oder K2 und K4. **Evidenz dagegen** = Mehrrendite signifikant negativ (p < 0,05). Sonst **nicht belegt**. Für defensive Regeln zusätzlich **risikomindernd**: höherer Sharpe und mindestens zehn Prozentpunkte kleinerer größter Einbruch als der Markt, im Gesamt- und im Kontrollzeitraum.

## Abbruchregel der Suche

Die Liste oben ist vollständig. Eine Suche ohne Ende findet mit Sicherheit einen Zufallstreffer. Erfüllt nichts die Kriterien, ist das das Ergebnis. Nachträgliche Varianten werden als explorativ gekennzeichnet und können nicht „verlässlich“ werden.

## Zeitangaben je Strategie

Signalrückblick, Neubildungsrhythmus und Haltedauer stehen je Zeile in den Ergebnisdateien. Eine eigene Haltedauer-Suche findet nur in C2 statt (1/3/12 Monate, alle Varianten berichtet, keine nachträgliche Auswahl). Quellportfolios behalten die Regeln ihrer Quelle; daraus folgt keine Haltedauer einzelner Aktien.

## Änderungen nach Festlegung

Vor der ersten Auswertung von Renditen (14.11.2026), nach Sichtung von Dateiformaten und Abdeckung:

1. **Signal-Suche:** Die Quelldatei mit wertgewichteten Fünfteln enthält 179 der 212 Signale (keine Fünftel für binäre/diskrete Signale). Modul B prüft diese 179.
2. **„Evidenz dagegen“** wird an der Mehrrendite **vor** Kosten gemessen (einseitig p < 0,05), damit nicht allein der Kostenabschlag ein marktähnliches Portfolio dorthin einordnet.
3. **Yahoo-Kursfehler:** Mehrere UCITS-ETFs zeigen in den ersten Wochen nach der Xetra-Notierung Tagessprünge über 25 %. Für jedes Produkt in C5 werden deshalb die ersten sechs Kalendermonate nach dem ersten Kurs verworfen. Bleibt danach ein Tagessprung über 20 %, der kein bekanntes Marktereignis ist (Oktober 1987, Oktober/November 2008, März 2020), wird das Produkt ausgeschlossen und genannt.
4. **AMOMX** liefert bei Yahoo keine Daten und entfällt.
5. **Eingabepaket:** Workflow-Artefakte sind aus der Arbeitsumgebung nicht abrufbar. Das eingefrorene Eingabepaket liegt deshalb auf dem Daten-Branch `research-data/2026-11-14-strategy-audit`; jede weitere Rechnung nutzt genau diesen Stand. Ein erster Versuch legte das Paket als Datei an einem Vorab-Release ab; dieser Weg wurde verworfen, die Datei dort ist ein nicht verwendeter früherer Abruf.
6. **Ausführung in C2 und C4:** In C2 (Tagesdaten) wird am ersten Handelstag nach dem Signal zum Schlusskurs gehandelt; der Benchmark wird über dieselben Halteintervalle gemessen. In C4 liegen aus Yahoo nur Monatsrenditen im Paket; Signal und Ausführung erfolgen dort zum selben Monatsschlusskurs (übliche Konvention, leicht zugunsten der Regel).
