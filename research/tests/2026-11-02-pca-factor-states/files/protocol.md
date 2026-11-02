# PCA und Prognose gemeinsamer historischer Faktor-Zustände

Festlegung am 02.11.2026 vor Berechnung der neuen Zielgrößen und Testkennzahlen. Die früheren Testergebnisse sind bereits bekannt; daher ist dies eine explorative historische Folgestudie, keine neue vollständig unberührte Bestätigung.

## Datengrundlage und Ebenen
- Alle sieben bereitgestellten Testpakete werden in der Herkunfts-/Verwendbarkeitsprüfung berücksichtigt. Fertige künftige Handelsgewinne, Stop-Ausgänge oder Testergebnisse werden niemals zu Eingabefaktoren.
- Hauptpanel: die 100 Unternehmen der vorab veröffentlichten PwC-Liste vom 31.03.2018. Kurse/Devisen und GDELT-Metadaten aus dem vorherigen globalen Stimmungs-Paket. Datenaufnahme vom 01.11.2026 bleibt unverändert; kein neuer, nach Ergebnissen ausgewählter Titel.
- Entscheidungszeitpunkte: wöchentliche Archivmittwoche, 02.01.2019 bis 24.09.2025. Nachrichten bis Mittwoch 12:00 UTC. Kursmerkmale ausschließlich bis vorangegangenen Dienstag. Fehlende Daten bleiben ausdrücklich markiert; keine heutige Bilanz wird rückwirkend verwendet.
- Primär: erwartete Vierwochen-Rendite gegenüber zeitgleichem gleichgewichtetem regionalem Aktienkorb in USD. Regionen mit weniger als fünf verfügbaren Firmen verwenden den historischen globalen Korb. Einstieg erster lokaler Handelstag ab folgendem Montag, Ausstieg erster lokaler Handelstag vier Kalenderwochen später, jeweils höchstens vier Tage Verschiebung. Sekundär identische Auswertung mit zwölf Wochen, rein deskriptiv.
- Keine Zukunftsvariablen aus den bisherigen Paneldateien werden wiederverwendet. Keine vorab auf 2019–2021 gelernten Stimmungskategorien werden als Merkmal genutzt. Rohwerte und rückwärts gerichtete Zustandsänderungen bilden die Eingaben.
- Abspaltungen: DowDuPont-Reihe wird bis Mai 2019 und United Technologies bis April 2020 begrenzt; überschreitende Halteperioden fehlen. Aktuelle Kursrevisionen, Aktiengattungen und nicht rekonstruierte Delistings bleiben Grenzen des Datenmaterials.

## Merkmale
- Technik: Renditen 5/20/60/120/252 Handelstage; Momentum zwischen 252 und 42 Handelstagen; Abstand zu MA50/MA200, 252-Tage-Hoch/-Tief; Drawdown 60 Tage; Volatilität 20/60 Tage, deren Verhältnis, Downside-Volatilität 20 Tage; ATR14 relativ zum Kurs; Volumen 5/20 Tage und 20/60 Tage.
- Marktbedingungen aus bereits bekannten Kursmerkmalen desselben historischen Korbs: mittlere 20-/60-Tage-Rendite, mittlere Volatilität, Anteil über MA200.
- Nachrichten: Ton, positive/negative Wortanteile, Polarität, Streuung, Meldungs-/Quellenzahl, Übersetzungs- und URL-Fokusanteil, Abdeckungsflags, Vierwochenwerte und Änderungen. GDELT-Stichprobe ist kein vollständiger Nachrichtenstrom; Wortton misst nicht direkt Anlegeremotionen.
- Vorab festgelegte Wechselwirkungen: ret20×Marktret60, Momentum252/42×Marktbreite, ATR×Marktvolatilität, Ton×Aufmerksamkeit, Tonänderung×Volatilität und Vierwochenton×Marktret60.
- Firmen- und Regions-Dummies sowie Merkmals-Fehlendflags bleiben in allen linearen Modellen vergleichbare Kontrollvariablen. PCA/PLS wird nur auf numerische Eingaben angewandt, nicht auf künftige Zielwerte oder Identitätscodes.
- Erweiterte Sensitivität: vergangene Monatsrenditen der sechs ursprünglichen Signalportfolios und der French-Faktoren, jeweils letzter freigegebener Monat und kumulierte drei Monate. Vorsichtige rechnerische Verzögerung: Monatsende plus 62 Kalendertage. Originalveröffentlichungen/Vintages sind nicht dokumentiert; diese Erweiterung ist deshalb KEIN strenger Point-in-time-Nachweis und gehört nicht zum Haupttest.

## Modelle und Auswahl
- Nullprognose für den relativen Ertrag.
- Preis-/Volumen-/Markt-Ridge als einfache trainierte Referenz; alpha aus [1,10,100].
- Ridge mit allen Hauptmerkmalen; alpha aus [1,10,100].
- Elastic Net mit allen Merkmalen, l1_ratio=0.5, alpha aus [0.0001,0.001,0.01].
- Principal Component Regression: numerische PCA mit k aus [2,4,8,12,20], danach Ridge alpha=10 plus identische Kontrollvariablen.
- PLS: k aus [2,4,8,12], trainiert ausschließlich auf numerischen Trainingsdaten und Trainingszielen; danach Ridge alpha=10 mit Kontrollen.
- Ein fester kleiner Interaktionsvergleich: HistGradientBoosting, 100 Iterationen, Lernrate 0.05, sieben Blätter, min_samples_leaf=100, L2=10, kein zufälliger interner Early-Stopping-Split. Kein Architektur-Suchlauf.
- Alle Verfahren mit Median-Ersetzung, Begrenzung auf 1./99. Perzentil und Standardisierung nur anhand des jeweiligen Trainingsfensters. Fehlendflags werden separat kontrolliert. Firmen-Dummies ausschließlich im Training gelernt, unbekannte Firmen ignoriert.
- Pro äußerem Prognosejahr: nur bis zum vorangegangenen 31.12. vollständig bekannte Zielrenditen trainieren. Innere zeitliche Auswahl: der letzte vollständige Kalenderjahrgang als Validierung, davor trainieren; auch dort nur bis zum damaligen Jahreswechsel abgeschlossene Ziele. Auswahlkriterium ausschließlich mittlerer quadratischer Prognosefehler im inneren Validierungsjahr.
- Äußere Prognosejahre: 2022, 2023, 2024 und 2025 bis 24.09. Expansives Training ab 2019, jährliche Neuschätzung. Alle Aktien eines Kalenderstichtags bleiben im selben Zeitfenster. Kein zufälliges Zeilensplitting.

## Bewertung und Schlussfolgerungen
- Primärer Endpunkt: Vierwochen-MSE der relativen Rendite. Sieben vorab definierte Vergleiche: fünf Gesamtmodelle jeweils gegen Preis-Ridge; zusätzlich PCA und PLS gegen Gesamt-Ridge. Einseitige Nutzen-Tests, Holm gemeinsam über sieben Vergleiche.
- Unsicherheit: 5000 gepaarte zirkuläre Bootstrap-Wiederholungen über ganze Kalenderwochen in 13-Wochen-Blöcken. Alle Firmen derselben Woche gemeinsam. Sensitivität 8/26 Wochen. Keine Annahme, dass mehrere Trade-Varianten oder überlappende Termine unabhängige Beobachtungen sind.
- Weitere feststehende Kennzahlen: R² gegen Nullprognose, AUC für positiven relativen Ertrag, mittlere stichtagsweise Spearman-Korrelation, Top-20%-Mehrertrag zum Korb, Treffer großer Anstiege (mindestens +10% absolut und positiver relativer Ertrag). Sekundäre Kennzahlen werden nicht zur nachträglichen Modellauswahl verwendet.
- Deskriptiver Handelsvergleich: fester Vierwochen-Takt ab erstem Teststichtag; obere 20% der Prognoseränge je Region, Regionsgewicht proportional zur festen Kohorte, mindestens ein Titel je Region. Gleicher Korb als Benchmark. 10000 EUR Modellkapital, 1 EUR pro Kauf und Verkauf, 0.1% ungünstige Ausführung je Seite; auch für neu zusammengesetzten Benchmark. USD-Erträge werden per EUR/USD-Referenzkurs umgerechnet. Keine Stop-/Limit-Optimierung. Lokal verschiedene Feiertage, FX-Referenzkurse und Datenausfälle machen dies zu einer Näherung, keinem Ausführungsnachweis.
- Stabilität und Interpretation: PCA-Ladungen/erklärte Varianz pro Prognosejahr; Vorhersage-Relevanz über vorab definierte Merkmalsgruppen und gemeinsame Out-of-sample-Ergebnisse. Hohe PCA-Ladung ist weder Vorhersagebeweis noch Kausalbeweis. Keine Auswahl eines Gewinner-Modells nach Testkennzahlen für einen Produktiveinsatz.
- Verbleibende Grenzen: kleine große-Firmen-Kohorte, dünne Nachrichten, revidierte historische Kurse, bereits bekannte historische Testjahre, fehlende firmenspezifische Fundamental-Vintages. Ein neuer Erfolg erfordert einen späteren unabhängig festgelegten oder prospektiven Prüfzeitraum.

## Präzisierung vor der ersten Zielauswertung
- Preis-Ridge erhält auch die drei rein kursbasierten Wechselwirkungen, damit ein Nachrichten-/PCA-Erfolg nicht allein durch deren Fehlen im Vergleich entsteht.
- Gruppen-Weglassdiagnose für Gesamt-Ridge, Elastic Net, PCA und PLS, nur Vierwochen-Hauptpanel: die sieben vorher genannten Gruppen werden einzeln entfernt; gleiche im inneren Zeitfenster gewählte Hyperparameter, alle Vorverarbeitung neu nur im jeweiligen Training. Rein deskriptiv, keine Modellauswahl nach diesen Testergebnissen.
- Portfolio-Quintile werden vor Kenntnis der Rendite aus allen prognostizierbaren Aktien bestimmt. Wenn ein benötigter ausgewählter Titel oder Benchmarktitel keine Zielrendite hat, ist die ganze betreffende Kohorte nicht auswertbar. Ausfälle werden ausgewiesen. Das darf nicht als ununterbrochen handelbarer Kapitalpfad interpretiert werden.
