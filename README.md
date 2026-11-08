# Bottleneck Lab — schlanker weltweiter Aktien-Screener

**Website:** https://boraborapalm.github.io/Bottleneck-Lab-Android/

Ein mobiles, bewusst einfaches Recherchewerkzeug für weltweite Aktien:
zwei Reiter für Strategie-Kandidaten und eine unabhängige Aktiensuche,
dazu Regionsfilter und ein optionaler Trade-Republic-AT-Filter für die Kandidaten.

## Was die App zeigt

- Aktien von unterstützten internationalen Börsen, ergänzt durch offizielle US-Börsenverzeichnisse
- **Reiter „Aktiensuche“:** eigenes Suchfeld mit Suchbutton und Enter, unabhängig von Strategie, Liquiditäts-/Momentumvorauswahl, Region und TR-AT-Filter. Durchsucht das gesamte verfügbare Namensverzeichnis sowie alle vorhandenen Kursdatensätze, mit antippbaren Vorschlägen, Ticker-/ISIN-Treffern, Akzentnormalisierung und begrenzter Tippfehlertoleranz einschließlich benachbarter Buchstabenvertauschungen. Auch Unternehmen ohne Kursdaten werden als Verzeichnistreffer gefunden und entsprechend gekennzeichnet. Charts und Fundamentaldaten bleiben bei vorhandenen Daten aufklappbar; ein Suchtreffer erhält keinen Strategie-Rang. „Kandidaten filtern“ bleibt ein lokaler Filter innerhalb der Kandidatenliste.
- Echte, datierte Tageskurse als **indikativ nach EUR umgerechnete Referenzwerte**
- Per Checkbox kombinierbare Ranglisten-Faktoren: **12–2-Monats-Momentum** (Standard; bereinigte Kursrendite von 252 bis 21 Handelstage vor dem Stichtag, also wie bei Jegadeesh/Titman und Fama/French nur ohne den jüngsten Monat – bis 03.11.2026 wurden 42 Handelstage ausgelassen), **geringe annualisierte Renditeschwankung über 252 Handelstage** und **Abstand zum 200-Tage-Trend**. Bei mehreren Häkchen werden die Rangprozente 0–100 gleichgewichtet gemittelt. Fehlende Kennzahlen schließen Aktien aus dem Mix aus, statt geschätzte Nullen einzufügen. Mindestens ein Faktor bleibt ausgewählt.
- Zusätzlich optional: **„Hoch-Tief-Mut · Sander-inspiriert“**. Diese Auswahl zeigt *tatsächlich geprüfte* Aktien mit 15–55 % Rückgang vom 252-Handelstage-Hoch, positivem Nettoergebnis, positivem operativem Cashflow, ≥3 % Nettomarge und mindestens −10 % Umsatzentwicklung im jüngsten prüfbaren Jahresabschluss. Finanzdaten stammen aus aktuellen **SEC EDGAR XBRL 10-K-Berichten**, daher derzeit überwiegend US-Emittenten. Score: 50 % relativer Rückgang, 25 % Gewinnmarge und 25 % Umsatzentwicklung. Unternehmensdaten und Geschäftsjahr werden im aufgeklappten Kandidaten angezeigt. Fehlen Unternehmensdaten, wird die Aktie **nicht** als Sander-Kandidat ausgegeben. Kann separat oder mit Momentum/Renditevolatilität/Trend kombiniert werden.
- **Interpretation:** Dies ist eine explizit *eigene* mechanische Teilannäherung an Beate Sanders Hoch-Tief-Mut-Ansatz, **keine exakte Umsetzung**. Deren wichtige Bestandteile langfristige Diversifikation, Dividenden, Unternehmensbewertung, überzeugendes Geschäftsmodell und Teilverkäufe sind nicht automatisiert. Auch ein starker Rückgang ist kein Beweis für eine günstige Bewertung. Keine belegte Überrendite aus dieser konkreten Screening-Regel.
- Momentum, Gross Profitability, Value, konservatives Investment und Gewinnüberraschungen haben eine wissenschaftliche Faktorgrundlage. Unsere konkreten Datenwege, Farbgrenzen, Auswahl und Kombination sind **nicht** historisch als renditesteigernd validiert. Auch längerfristige Low Volatility ist nicht mit einem gehebelten Long/Short-Low-Beta-Portfolio gleichzusetzen.
- Nur Titel mit einer EUR-Referenznotierung ab 2 € und durchschnittlich mindestens 2 Mio. € täglichen 20-Tage-Handelsumsatz, sofern die Daten existieren
- „Auswahl“: bis zu 20 Kandidaten nach dem gewählten Faktor-Mix mit höchstens vier je Region; „Alle geprüften“: bis zu 75 Treffer der Filter
- Trade Republic Österreich: nur eindeutige ISIN-Treffer in der offiziellen Instrumentenliste (keine Echtzeit-Handelsfreigabe)

Die App zeigt zusätzlich **Einstieg/Ausstieg prüfen** sowie **Kurssturz-Warnungen**: Ein möglicher Neueinstieg wird nur nach Tagesschluss bei positivem 12–2-Monats-Momentum, Kurs über dem 200-Tage-Durchschnitt und ohne deutliche Korrektur angezeigt; als Gesamtmarkt-Filter dient der US-notierte ACWI-ETF. Für bestehende Positionen empfiehlt die Anzeige eine **Prüfung** bei Kurs unter 200-Tage-Durchschnitt oder starken Rückgängen (mindestens 15 % in 21 Handelstagen oder 25 % unter dem 252-Tage-Hoch). Die Parameter sind vorab festgelegte Risiko-Heuristiken, **nicht** durch diesen konkreten Backtest nachgewiesen profitabel. Einstieg frühestens am folgenden Handelstag nach Prüfung echter Brokerkurse. EUR-Referenzkurs, 200-Tage-Trendgrenze, Crash-Schwellen und eine rein hypothetische 2,5-ATR-Risikoschwelle für *neue* Käufe erscheinen je Aktie. Keine automatisierte Überwachung oder Stop-Orders. Ein Stop schützt nicht zuverlässig vor Kurslücken.

Es werden **keine tatsächlichen Käufe, Stop-Loss-Orders oder künftige Renditen** prognostiziert. Die alte 60-Tage-Score- und ATR-Handelslogik ist entfernt, weil sie in den bisherigen Tests keinen belastbaren Vorteil gezeigt hat. Auch das neue Momentum-Screening ist **nicht als profitabel validiert**. Die akademischen Faktoruntersuchungen betrafen hauptsächlich US-Daten und sind kein Beweis für diese weltweite konkrete Aktienliste.

## Hoch-Tief-Mut-Screen: Daten, Grenzen, Rechte

Datenquelle: [SEC EDGAR CompanyFacts API](https://www.sec.gov/search-filings/edgar-application-programming-interfaces), XBRL und offizielle SEC-Ticker/CIK-Zuordnung. Jährliche 10-K-/10-K/A-Berichte werden auf **Fiskaljahr-Geschäftszahlen (335–385 Tage)** geprüft, mit echtem Filing-Datum, Geschäftsjahresende und vergleichbarer Einheit USD. Für diesen Sander-Filter fallen Quartalsdaten, unbestätigte Drittanbieter-Schätzungen sowie Unternehmen ohne Finanznachweise heraus. Frühwachstum nutzt separat geprüfte Quartalsdaten. Um API-Grenzen einzuhalten, werden pro Aktualisierung nur bis zu 60 SEC-Unternehmen geprüft und verifizierte Daten nach sieben Tagen erneut zur Aktualisierung vorgesehen (bestehende Daten bei vorübergehendem Ausfall höchstens 28 Tage weitergeführt). Die Abdeckung wächst mit Datenaktualisierungen. Ist die SEC nicht erreichbar, werden keine erfundenen Fundamentalwerte ausgegeben.

**Beate Sander persönlich beschrieb** breite Diversifikation, langfristiges Halten, antizyklische Nachkäufe gut aufgestellter Unternehmen und gelegentliche Teilverkäufe. Interviews: [herCAREER](https://www.her-career.com/beate-sander-ich-koenne-ja-auch-auf-kreuzfahrten-unterwegs-sein-aber-ich-arbeite-lieber-so-viel-wie-eine-junge-startup-gruenderin/) und [Trading-Ideen](https://www.trading-ideen.de/wordpress/interview-mit-beate-sander/). Die Prozentgrenzen im Screener stammen **von uns**, nicht aus einer von Sander veröffentlichten festen Formel.

## Fundamentaldaten mit vier Farbstufen

Jede Aktienkarte zeigt unabhängig vom Strategie-Mix eine kompakte Vorschau für
Umsatzwachstum, Nettomarge und operative Cashflow-Marge. Beim Aufklappen folgen
acht Kennzahlen mit Wert, Textbewertung, Quelle und Geschäftsjahresende:

| Kennzahl | Grün: sehr gut | Gelb: geht so | Orange: eher schwach | Rot: Vorsicht |
| --- | --- | --- | --- | --- |
| Umsatzwachstum zum Vorjahr | ≥10 % | ≥0 % bis <10 % | ≥−10 % bis <0 % | <−10 % |
| Gewinnwachstum zum Vorjahr | ≥15 % | ≥0 % bis <15 % | ≥−20 % bis <0 % | <−20 % oder laufender Verlust |
| Nettogewinnmarge | ≥15 % | ≥5 % bis <15 % | ≥0 % bis <5 % | <0 % |
| Operative Cashflow-Marge | ≥15 % | ≥5 % bis <15 % | ≥0 % bis <5 % | <0 % |
| Freie Cashflow-Marge | ≥10 % | ≥3 % bis <10 % | ≥0 % bis <3 % | <0 % |
| Eigenkapitalquote | ≥40 % | ≥20 % bis <40 % | ≥10 % bis <20 % | <10 % |
| Umlaufvermögen / kurzfristige Verbindlichkeiten | ≥2× | ≥1,2× bis <2× | ≥1× bis <1,2× | <1× |
| Gesamte Verbindlichkeiten / Eigenkapital | ≤1× | >1× bis ≤2× | >2× bis ≤4× | >4× oder EK ≤0 |

Die Grenzen sind **eigene grobe Orientierung**, keine wissenschaftlich validierte
Aktienbewertung und kein Branchenvergleich. Die Farbe bewertet ausschließlich
die jeweilige Kennzahl, weder den Aktienpreis noch einen Kauf. Banken,
Versicherungen und REITs erhalten bei erkennbarer Branche keine Standardampel
für Cashflow- und Bilanzquoten. Die Branchenzuordnung ist nicht vollständig.

Gewinnwachstum wird nur bei positivem Vorjahresgewinn als Prozentwert berechnet.
Ein Wechsel vom Verlust zum Gewinn ist eine gelb markierte „Gewinnwende“.
Freier Cashflow = operativer Cashflow minus ausgewiesene Sachinvestitionen;
fehlende Sachinvestitionen werden nicht als null angenommen. Bilanzdaten müssen
zum gleichen Geschäftsjahresende passen; später erneut berichtete 10-Q-Bilanzwerte
zu genau diesem Stichtag sind zulässig. Absolute Umsatz-, Gewinn- und
Cashflowbeträge stehen in der Berichtswährung USD. Ein datiertes KGV erscheint inzwischen bei der Value-Option als TTM-Kontext des
Anbieters; fehlende Werte und Dividendenrenditen werden nicht erfunden.

Fehlende Kennzahlen bleiben grau. Bei einem Geschäftsjahresende vor mehr als
550 Tagen werden alle Farbbewertungen ausgesetzt; künftige oder ungeprüfte
Berichtsdatierungen zeigen auch keine Zahlen. Teilweise verfügbare Jahreszahlen
bleiben sichtbar, qualifizieren aber nur bei Erfüllung **aller** bisherigen
Anforderungen für den unveränderten Sander-Filter.

Die Datenabfrage rotiert über Momentumaktien, Sander-Kandidaten **und** Aktien mit hoher aktueller Dreimonats-Kursstärke,
mit maximal 60 Unternehmensabfragen je Aktualisierung, höchstens drei parallel,
sieben Tagen Aktualisierungsintervall für verifizierte Daten (höchstens 28 Tage Ausfallreserve) und zwei Tagen Abstand nach erfolglosen
Abfragen. Neue Bilanzfelder werden auch bei älteren Caches nachgeladen. Die
aktuelle SEC-/TGMCharts-Quelle umfasst hauptsächlich US-Unternehmen; bei
nicht abgedeckten internationalen Aktien steht ein ausdrücklicher Hinweis.

Grundlagen und Definitionen: [SEC – Geschäftsberichte lesen](https://www.sec.gov/reportspubs/investor-publications/investorpubsbegfinstmtguidehtm.html)
und [SEC – XBRL-APIs](https://www.sec.gov/search-filings/edgar-application-programming-interfaces).
Die Farbgrenzen stammen von uns, nicht von der SEC oder Beate Sander.

## EU-Fundamentaldaten aus ESEF-Jahresberichten

Für Aktien mit einer ISIN aus der EU bzw. dem EWR (z. B. FR, DE, AT, NL) lädt die Pipeline je Lauf bis zu 25 offizielle ESEF-Jahresfinanzberichte. Seit 2021 müssen Emittenten an EU-Börsen diese maschinenlesbar nach IFRS veröffentlichen. Quelle ist die frei zugängliche Sammlung [filings.xbrl.org](https://filings.xbrl.org/about.html) von XBRL International; die ISIN wird über [GLEIF](https://www.gleif.org/) eindeutig der LEI des Emittenten zugeordnet.

- Verwendet werden nur Werte des Konzerns (LEI des Emittenten) ohne Segment- oder sonstige Dimensionen: Jahreszeiträume von 335–385 Tagen, die am Berichtsstichtag enden, und Bilanzwerte genau zu diesem Stichtag. Vorjahreswerte stammen aus den Vergleichszahlen desselben Berichts.
- Nettogewinn und Eigenkapital sind die Anteile der Eigentümer des Mutterunternehmens, wie bei den SEC-Feldern. Ist eine Kennzahl nicht getaggt (häufig: Gesamtverbindlichkeiten oder Bruttogewinn), bleibt sie leer; es wird nichts abgeleitet. Widersprüchliche doppelte Werte bleiben ebenfalls leer.
- Beträge stehen in der Berichtswährung (meist EUR). Kennzahlen, Farben, Quality (Bruttogewinn/Bilanzsumme), konservatives Bilanzwachstum und der Hoch-Tief-Mut-Filter verwenden dieselben Regeln wie bei SEC-Daten. Value (datiertes KBV) und Quartalsdaten gibt es für diese Quelle nicht.
- Als Berichtsdatum gilt das Aufnahmedatum in der Sammlung, nicht der offizielle Veröffentlichungstag. Geprüfte Berichte werden nach 21 Tagen erneut abgefragt und höchstens 60 Tage weitergeführt; nach einem erfolglosen Versuch wird drei Tage gewartet. Vorrang haben Aktien ohne Daten, liquide Titel und Aktien der Trade-Republic-AT-Liste.
- Banken und Versicherungen weisen oft keinen klassischen Umsatz aus. Schweizer oder britische Unternehmen ohne EU-Notierung sind nicht enthalten.

## Frühwachstum / Multibagger-Kandidaten (zusätzliche Checkbox)

Die Option funktioniert allein oder im bestehenden gleichgewichteten Strategie-Mix.
Sie ist **eine eigene experimentelle Vorauswahl**, keine vollständige CAN-SLIM-
Umsetzung und kein kalibrierter „10×-Detektor“. Standard bleibt Momentum.

Die neue Vorauswahl verwendet drei aufeinanderfolgende diskrete Quartale samt
passenden Vorjahresquartalen: Umsatzwachstum zuletzt mindestens 20 %, Mittel der
beiden vorherigen Raten mindestens 10 % und letzte Beschleunigung mindestens
2 Prozentpunkte. Das jüngste Quartal darf höchstens 180 Tage alt sein.
Zusätzlich erforderlich: positiver operativer Jahres-Cashflow (Jahresende
höchstens 550 Tage alt), letzte Quartals-Nettomarge mindestens null **oder**
Verbesserung um mindestens 3 Prozentpunkte gegenüber dem Vorjahresquartal,
positive 63-Tage-Kursrendite, Outperformance gegenüber ACWI und höchstens
15 % Abstand unter dem vorherigen 63-Tage-Schlusshoch. Erkennbare Banken,
Versicherungen und REITs werden aus dieser allgemeinen Cashflow-Regel ausgeschlossen.

| Getrennter Regelwert | Gewicht im Frühwachstumswert | Verwendete Angaben |
| --- | --- | --- |
| Wachstum | 45 % | Letzte Umsatzrate 50 %, Dreiquartalsmittel 30 %, letzte Beschleunigung 20 % |
| Finanzielle Qualität | 30 % | Letzte Nettomarge 40 %, deren Änderung gegenüber dem Vorjahresquartal 20 %, operative Jahres-Cashflow-Marge 40 % |
| Kursbestätigung | 25 % | Relative 63-/126-Tage-Rendite gegenüber ACWI 35/25 %, Abstand zum vorherigen 63-Tage-Hoch 25 %, relativer letzter Handelsumsatz 15 % |

Die festen linearen Abbildungsgrenzen auf 0–100 stehen vollständig in der
aufklappbaren Methodik der App und in `scripts/growth_radar.py`. Diese Grenzen
wurden **nicht** auf bekannte Gewinner optimiert. Ein bereits gestiegener Kurs
ist allein keine Qualifikation. Der gemischte Strategierang verwendet weiterhin
Rangprozente; der darunter gezeigte Frühwachstums-Regelwert ist kein Rangprozent
und keine Gewinnwahrscheinlichkeit.

Kursdaten benötigen 127 gültige split-/dividendenbereinigte Handelstage; daher
können auch jüngere Börsennotierungen ohne 12–2-Momentum erscheinen. Sobald
Momentum zusätzlich gewählt wird, gilt dessen volle Historienanforderung.
Aktien- und ACWI-Kursdatum müssen übereinstimmen. Der Handelsumsatzvergleich
verwendet Kurs × Aktienvolumen, um reine Aktiensplits nicht als Volumenexplosion
zu interpretieren. Neue Kursfelder werden aus alten Kurs-Caches nachgeladen.

Quartalsdaten kommen aus **SEC EDGAR 10-K/10-Q USD-XBRL** oder dem bereits
verwendeten [TGMCharts-Relay](https://tgmcharts.com/developers/docs/statements),
mit Datum und Provenienz je verwendetem Wert. Direkte SEC-Daten benötigen
70–105 Tage Laufzeit; Halbjahres-, Jahres- und YTD-Beträge sind keine Quartale.
Q4-/YTD-Ableitungen des Relays sind ausdrücklich gekennzeichnet und benötigen
die dokumentierte Herkunft der zwei Eingangsfilings. Vorjahresvergleiche
benötigen denselben Umsatz-Tag und vergleichbare Quartalslängen. Veröffentlichungen
nach dem letzten Aktienkurs werden nicht verwendet. Die Pipeline ist damit
weiterhin **kein Point-in-Time-Backtest**; spätere, bereits veröffentlichte
Restatements können heutige Vergleiche verändern.

Bewertung, Gewinnüberraschungen/Prognoseanhebungen, Wettbewerbsvorteil und
Aktienverwässerung bleiben ausdrücklich **ungeprüft**, ohne ersatzweise Punkte.
Die Cashflow-Regel ist keine vollständige Bilanz-/Finanzierungsprüfung und erfasst
keine Unternehmen mit negativem Jahres-Cashflow. Die Abdeckung ist überwiegend
US-beschränkt und wächst in den begrenzten Aktualisierungsläufen. Fehlende
Daten schließen einen Titel aus diesem Filter aus. Ein überlebensbiasfreier
historischer Test mit damals verfügbaren Daten bleibt erforderlich, bevor ein
konkreter Renditevorteil behauptet werden könnte.

## Vier zusätzliche literaturmotivierte Optionen

Die Kandidatenliste und die unabhängige Aktiensuche bieten zusätzlich:

| Option | Rangmerkmal (höher = höherer Rang) | Pflichtdaten |
| --- | --- | --- |
| Profitabilität / Quality | Jahres-Bruttogewinn / Bilanzsumme | Gleicher Jahresstichtag, aktueller SEC-USD-Bericht; für erkennbare Finanzunternehmen keine pauschale Gross-Profit-Definition |
| Value · Bewertung | Buchwert/Börsenwert = 1 / KBV | Datiertes TGMCharts-KBV für klassifizierte Stammaktien, aktueller USD-Jahresbericht und konsistenter USD-Schlusskurs |
| Gewinnmomentum · Quartalsmodell | Standardisierte Abweichung des Quartals-Gesamtgewinns vom eigenen saisonalen Modell | 13 lückenlose Quartalsgewinne derselben USD-/Tag-Basis, dokumentierte Provenienz |
| Konservatives Bilanzwachstum | Negative jährliche Änderung der Bilanzsumme | Zwei positive Bilanzsummen im Abstand von 350–385 Tagen |

Quality ist hier bewusst das konkrete **Gross-Profitability-Merkmal**, kein
vollständiger Quality-Minus-Junk-Index. Der operative Cashflow relativ zur
Bilanzsumme wird zusätzlich als Kontext gezeigt. Value verwendet die vom
Anbieter dokumentierte common-equity-P/B-Definition. Bewertungs- und Aktienkursdatum
müssen übereinstimmen; eine Kursabweichung von mehr als 2 % führt zum Verzicht
auf die Bewertung. Die Summary muss einem klassifizierten Stammaktien-Unternehmen
zugeordnet sein; Fonds, Warrants, Preferreds usw. sind unzulässig. KGV, Gewinn-
und FCF-Rendite sind ausschließlich zusätzlich gekennzeichnete TTM-Anbieterwerte.
Es werden keine Marktwerte aus mehrdeutigen Aktienzahlen oder unangepassten EPS
selbst erfunden. Quellenangabe und TGMCharts-Link erscheinen bei den Daten.

Das **eigene Gewinnmomentum-Modell** hat einen saisonalen Erwartungswert:
`NetIncome[q−4] + Mittelwert(ΔNetIncome der vorherigen 8 Quartale)`. Die aktuelle Differenz
wird durch die Stichproben-Standardabweichung jener acht früheren Änderungen
standardisiert. Die aktuelle Beobachtung ist nicht Teil der Mittelwert-/Streuungs-
schätzung. Damit wird ausdrücklich **kein Analystenkonsens** und kein tatsächlicher
Analysten-Beat vorgetäuscht. Die EPS-SUE-/PEAD-Literatur wird **nicht exakt repliziert**:
Das Modell verwendet Gesamtgewinne, berücksichtigt keine Aktienverwässerung oder
Rückkäufe und kann durch Sondereffekte stark beeinflusst sein. Eine reine Änderung
der Aktienzahl durch einen Split verändert den Gesamtgewinn nicht. TGMCharts darf
diskret fehlende Quartalsgewinne durch dokumentierte, gleich definierte Jahres-/YTD-
Differenzen mit zwei Quellbelegen liefern; die Anzahl solcher Quartale wird angezeigt.
Jahres- oder YTD-Beträge selbst gelten niemals als Quartal, Quartals-EPS werden
nicht aus Jahres-EPS abgeleitet. Bei Lücken, einem Definitionswechsel oder fehlender
Streuung bleibt die Option grau und rangiert nicht.
Das jüngste Quartal muss höchstens 180 Tage alt sein, sein Filing höchstens
120 Tage. Quartalsdaten des Anbieters werden für maximal fünf Fiskaljahre geladen;
die Abdeckung ist dennoch nicht garantiert. Ein Filing-Datum ist
nicht zwingend das frühere Datum einer Pressemitteilung. Spätere, bereits bekannte
Restatements können heutige Vergleiche verändern; dies ist kein Point-in-Time-Backtest.

Die neue **12-Monats-Schwankung** ersetzt das frühere ATR-Rangmerkmal:
Stichproben-Standardabweichung der letzten 252 logarithmischen Tagesrenditen
bereinigter Schlusskurse × √252. Sie benötigt 253 Preise und misst Volatilität,
**kein Beta**. Das ATR(14) für die bereits vorhandenen optionalen Kauf-/Stop-
Beispielrechnungen bleibt als eigenes Maß bestehen. Alte Preis-Caches bekommen
die neuen Felder durch begrenzte priorisierte Nachabfragen.

Die vier neuen Faktoren werden ohne vorab optimierte Gewichte in den bestehenden
Rangmixer eingespeist. Farbgrenzen stehen in der App vollständig offen: Quality
≥30/15/0 %; Value KBV ≤2/4/8; Gewinn-Modellabweichung ≥1/0/−1. Bilanzwachstum grün nur bei 0–5 %,
gelb −20–15 %, orange −40–30 %, sonst rot; eine Bilanzschrumpfung wird nicht als
automatisch sehr gut dargestellt. In der Rangliste entspricht die Richtung
weiterhin dem negativen Vermögenswachstum; Unternehmensaufspaltungen und andere
Sondereffekte erfordern zusätzliche Prüfung. Diese Ampeln sind eigene Einordnungen,
keine aus den Papers abgeleiteten Kaufgrenzen. Fehlende Pflichtdaten sind grau.

Die Datenpipeline ergänzt innerhalb ihres Budgets jährlich Bruttogewinn und
Vorjahres-Bilanzsumme; ein Schemawechsel lädt alte Caches nach. Zusätzlich sind
maximal 60 tägliche Summary-Abfragen mit drei parallelen Unternehmen vorgesehen.
Gültige, zum Schlussdatum passende Summary-Caches werden wiederverwendet.

Forschungsbezug: [Novy-Marx (2013)](https://doi.org/10.1016/j.jfineco.2013.01.003),
[Fama/French (2015)](https://doi.org/10.1016/j.jfineco.2014.10.010) und
[Chan/Jegadeesh/Lakonishok (1996)](https://doi.org/10.1111/j.1540-6261.1996.tb05222.x).
Die Faktor-Literatur ist **kein Nachweis** für unsere spezielle, überwiegend
US-fundamental abgedeckte Long-only-Liste, ihre Ampeln, Handelskosten oder Steuern.

## Anlagehorizont und Strategie-Zeitplan

Über beiden Reitern steht **„Dein Anlagehorizont“**: offen, 1–4 Wochen, etwa 3/6/12 Monate oder länger als ein Jahr. Der Horizont ordnet Strategiehinweise ein. Der deutlich beschriftete Übernahmebutton setzt im geöffneten Reiter eine Einzelstrategie: bei 3/6 Monaten den Trend, bei 12 Monaten Momentum. In der Kandidatenliste bestimmt diese Wahl die Aktienrangfolge; in der unabhängigen Aktiensuche ändert sie die angezeigten Strategieprüfungen, niemals die Namens-Treffer. Weitere Häkchen bleiben manuell möglich. Horizonte und beide Strategieauswahlen werden lokal auf dem Gerät gespeichert; unbrauchbare oder gesperrte Speicherung verhindert die Nutzung nicht.

Die Zeitangaben stammen aus der [archivierten Haltedauer-Folgestudie](research/tests/2026-11-02-holding-duration), nicht aus einem neu erfundenen Optimum für jede Aktie. Verwendet werden die aus vergangenen Daten gewählten Intervalle, keine nachträglichen Sieger des ganzen Testzeitraums: Momentum meist 252 Sitzungen (6 von 7 Jahren); Trend 120 (5 Jahre) oder 60 Sitzungen (2 Jahre); geringe Schwankung meist 252 Sitzungen (5 Jahre), aber Median der abgeschlossenen Trades nur 120 Sitzungen. Beobachtete Prüfintervalle, tatsächliche Haltedauer und Signalrückblick bleiben getrennt. Nicht abgeschlossene Positionen sind in den Haltemedianen zensiert.

Jede Strategieauswahl und Kandidatenkarte zeigt einen Zeithinweis, in Suchtreffern steht er bei der jeweiligen Strategiepassung. Für einen Mix wird kein gemeinsames Mittel oder scheinbar optimales Verkaufsdatum berechnet. Die hohen Weiterhalte-Renditen aus dem Test waren teils stark konzentriert; Weiterhalten bedeutet außerdem keinen erzwungenen Verkauf zum nächsten Prüftermin. Die allgemeine App-Rangliste ist nicht identisch mit dem historischen Zehn-Aktien-Portfolio und dessen Gewichtungs-/Ausführungsregeln.

Quality, Value und Bilanzwachstum zeigen ausdrücklich **Portfolioaktualisierung statt Aktien-Haltedauer**. Sander, Frühwachstum und das eigene Gewinn-Quartalsmodell bleiben hinsichtlich optimaler Haltedauer ungeprüft. Deshalb gibt es für kurze oder überjährige Horizonte keinen automatisch übernommenen Strategievorschlag. Fehlende Evidenz verändert die bestehenden Aktienmerkmale und deren Farben nicht. Der frühere 12–2-Momentum-Standard bleibt ohne gespeicherte eigene Auswahl erhalten.

## Kursdiagramme in jeder Aktienkarte

Beim Aufklappen wird der Kursverlauf **erst dann** geladen (kein externer TradingView-Embed). Vorgaben: **3 Monate**, schnell umschaltbar zwischen **1M, 3M, 6M, 1J, 3J, 5J und MAX** (höchstens die letzten rund zehn Jahre, soweit Daten vom Anbieter verfügbar sind). Pro Symbol erzeugt die Kursdaten-Pipeline eine separate JSON-Datei unter `docs/charts/<Ticker>.json`; ein GitHub-Actions-Cache behält Kurshistorien aus vorherigen Aktualisierungen. Bei fehlenden Kursreihen erscheint eine klare Meldung. Gespeichert werden nur Kursreihen der Aktien, die im aktuellen Datenstand enthalten sind; ältere Dateien entfernt die Pipeline, damit die Website unter der GitHub-Pages-Größengrenze bleibt.

Kauf-Limit- und Stop-Loss-Linien werden im Chart **nur bei aktiviertem Schalter „Kauf-Limit & Stop-Loss anzeigen“** eingeblendet. Da die Achse den Originalkurs der jeweiligen Börse zeigt, werden die vorhandenen EUR-Modellwerte mit dem **aktuellen Referenzwechselkurs** zurück in die Kurswährung umgerechnet; sie sind weder historische EUR-Kurse noch tatsächliche Broker-Orders. Die Chartreihe verwendet von Yahoo bezogene split-/dividendenbereinigte Schlusskurse, auf den letzten Originalschlusskurs skaliert. Die Modellgrenzen wurden in unseren bisherigen Tests nicht als gewinnsteigernd validiert.

## Depot-Check (eigene Käufe gegen einen Benchmark)

Im Reiter **Depot-Check** trägst du beliebig viele Positionen ein: Aktie (Name, Ticker oder ISIN), Kaufdatum und Verkaufsdatum oder „noch im Depot“, optional die Stückzahl. Kauf- und Verkaufskurs werden als Tagesschlusskurs vorgeschlagen (erster Handelstag ab dem Datum) und lassen sich mit den eigenen Kursen überschreiben. „+ Position hinzufügen“ legt weitere Zeilen an; alles bleibt nur auf dem Gerät gespeichert.

„Mit Benchmark vergleichen“ wählt je Aktie automatisch den passenden Markt nach dem Land des Emittenten (z. B. DAX für deutsche, STOXX Europe 600 für übrige europäische, S&P 500 für US-Aktien, MSCI ACWI als Rückfall) oder nutzt einen manuell gewählten bzw. frei eingegebenen Benchmark (Yahoo-Symbol, z. B. `IWDA.AS` oder `^GDAXI`). Gezeigt werden Rendite der Aktie und des Benchmarks über dieselben Tage, beide in EUR und inklusive Dividenden, die Differenz in Prozentpunkten (Out- bzw. Underperformance), annualisierte Werte ab einem Jahr sowie der Zeitverlauf (100 = Kauftag). Bei mehreren Positionen vergleicht die Summe, was aus demselben Geld zu denselben Zeitpunkten im jeweiligen Benchmark geworden wäre; ohne Stückzahl zählt jede Position mit 1.000 €.

- Rendite: bereinigte Schlusskurse (Dividenden wieder angelegt, Splits berücksichtigt), umgerechnet mit historischen Wechselkursen (`XXXEUR=X`; Pence, Agorot und Cent werden umgerechnet). Eigene Kurse ersetzen den Schlusskurs des Tages: bereinigte Rendite × (eigener Verkaufskurs / Schlusskurs) ÷ (eigener Kaufkurs / Schlusskurs).
- Benchmarks: breite ETFs bzw. Performanceindizes inklusive Dividenden. Der Datenlauf lädt sie täglich nach `docs/benchmarks/` und prüft ihre Verfügbarkeit; die automatische Wahl nutzt nur verfügbare Reihen.
- Grenzen: höchstens rund zehn Jahre zurück; Gebühren und Steuern sind nicht enthalten; vergangene Wertentwicklung ist keine Prognose.

## Kurs auf Knopfdruck in der Aktiensuche

Hat ein Suchtreffer keinen gespeicherten Kurs, lädt **„Kurs jetzt laden“** (oder das Aufklappen der Karte) den letzten abgeschlossenen Tagesschlusskurs über einen optionalen Cloudflare Worker im Gratis-Tarif (`cloudflare/`). Angezeigt werden Schlusskurs mit Datum, EUR-Referenzwert, 12–2-Momentum aus der geladenen Reihe und der Kursverlauf, ausdrücklich ohne Strategie-, Liquiditäts- oder Fundamentalprüfung. Die Antwort gilt bis 30 Minuten nach dem nächsten regulären Börsenschluss und wird so lange auf dem Gerät wiederverwendet (Speicher, Browser-Cache, höchstens zwölf Abrufe). Fehler werden nie gespeichert. Ohne Worker funktioniert die App unverändert.

## Stand der Daten und Grenzen

Die Aktienverzeichnisse umfassen viele mehr Börsenticker, als in einem sechs Stunden laufenden Aktualisierungsfenster abgefragt werden. Der öffentliche GitHub-Workflow prüft regionale Ticker in rotierenden Teilmengen, dazu je Lauf bis zu 150 Verzeichnisaktien aus der offiziellen Trade-Republic-AT-Liste, die am längsten nicht geprüft wurden. Euronext-Zeilen des Verzeichnisses werden nur dann Paris, Brüssel oder Lissabon zugeordnet, wenn Börsenland und ISIN-Land übereinstimmen; Wien, Amsterdam, Prag, Budapest und Bukarest sind eindeutig angebunden. `universe_size` bezeichnet daher nur gefundene Symbole; `scanned_tickers` nur solche mit brauchbaren historischen Kursabfragen, `eligible_count` nur solche mit den nötigen EUR-/Liquiditäts-/Momentumwerten.

Datenquellen: [Adanos – globales Aktienverzeichnis](https://github.com/adanos-software/free-ticker-database), Nasdaq Trader, inoffizielle Yahoo-Finance-Tageskurse (US-Fallback Stooq), Frankfurter-Referenzwechselkurse sowie [TR AT – offizielle Wertpapierliste](https://assets.traderepublic.com/assets/files/AT/Instrument_Universe_AT_en.pdf). Fehlende Daten bleiben fehlend. Kurse sind **keine** tatsächlichen Trade-Republic-Geld-/Briefpreise. Kein Zugriff auf das Brokerkonto, keine Käufe oder Verkäufe. Delistings, Splits, Dividenden, Gebühren und österreichische Besteuerung werden nicht als historische Trading-Performance modelliert.

## Betrieb

Das unabhängige Namensverzeichnis wird je Datenlauf als `docs/search-index.json`
aus den bereits entdeckten Aktien erzeugt und erst beim Öffnen der Aktiensuche
geladen. Es enthält ausschließlich öffentliche Identitäts-/Börsenangaben,
keine simulierten Kurse oder Datenabdeckungsversprechen. Bei einem Ladefehler
bleibt die Suche über alle vorhandenen Kursdatensätze mit entsprechendem Hinweis
nutzbar. Bis zu fünf Namensvorschläge und 30 Ergebnisse halten die mobile Ansicht
übersichtlich. Suchbegriffe werden lokal verarbeitet; es wird keine externe
Suchabfrage pro Tastendruck versendet. Die Reiter sind per Tastatur bedienbar;
`#search` öffnet die Aktiensuche direkt.

In der Aktiensuche können unter **„Strategie prüfen für:“** alle neun bestehenden
Strategien unabhängig angehakt werden (anfangs alle aktiv). Pro Aktie erscheint
je gewählter Strategie eine textlich begründete Passung: **grün „Passt gut“, gelb
„Passt teilweise“, orange „Passt wenig“, rot „Passt schlecht“** oder **grau „Zu
wenig Daten“**. Diese Häkchen ändern weder die Namenssuche noch die Reihenfolge
oder die sichtbaren Titel; es gibt keinen pauschalen Kauf- oder Gesamtscore.

Die allgemeinen Orientierungsgrenzen sind in der Aktiensuche einsehbar:
Momentum grün ab +20 %, gelb ab 0 %, orange ab −15 %; annualisierte
252-Tage-Renditevolatilität grün bis 20 %, gelb bis 35 %, orange bis 50 %; Trend grün ab dem 200-Tage-Durchschnitt, gelb bis
5 % darunter, orange bis 15 % darunter. Schlechtere Werte sind rot. Bei Sander
und Frühwachstum werden die bereits vorhandenen Pflichtbedingungen einzeln
geprüft: alle erfüllt grün, mindestens 75 % gelb, mindestens 50 % orange, sonst
rot. Unvollständige oder veraltete Pflichtdaten ergeben grau statt einer
negativen Bewertung. Dies ist eine transparente Einordnung der Merkmale zu
unseren Regeln, keine validierte Gewinnprognose oder Geschäftsmodellbewertung.

Der aktive Workflow ist `.github/workflows/market-data-pages.yml`; er läuft alle sechs Stunden und bei relevanten Änderungen. Die Website kommt aus `docs/index.html`, die generierte Daten-Datei heißt `docs/snapshot.json`. Manuell starten: GitHub → Actions → **Bottleneck Lab · Simplified Global Snapshot** → **Run workflow**. Die Website-Schaltfläche „Aktualisieren“ lädt nur den zuletzt veröffentlichten Snapshot erneut, sie startet keine Datenabfrage.

Die Offline-Tests prüfen geografische Symbolübersetzung, EUR-Konvertierung, die Broker-ISIN-Verifizierung, 12–2-Monats-Momentum, die regionale Auswahl und den Verzicht auf alte Scores; ein Frontend-Check schützt vor doppeltem Code hinter der HTML-Datei.

## Alte Versionen

Frühere Reiter, deren alte **nicht validierte** Kauf-/Stop-Signalmodelle, Forschungs-Backtests, die frühere Android-APK und deren Quellcode bleiben durch die Git-Commit-Historie rekonstruierbar. Diese historischen, nicht ausreichend validierten Ansätze gehören bewusst **nicht** mehr zum aktuellen App-Build.


## Dokumentierte Forschungs- und Strategietests

Die bisherigen Studien sind unter [research/tests](research/tests) mit eigenem Ordner pro Test dokumentiert. [research/README.md](research/README.md) bietet den Index und die aktuell geltenden Grenzen; [die Haltedauer-Prüfung](research/HOLDING_PERIODS.md) trennt Signalrückblick, Prognosehorizont, tatsächliche Haltedauer und Rebalancing. Die ursprünglichen Ergebnisse sind archiviert, damit sie vor weiteren Berechnungen nachgelesen werden können.

