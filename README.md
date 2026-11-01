# Bottleneck Lab — schlanker weltweiter Aktien-Screener

**Website:** https://boraborapalm.github.io/Bottleneck-Lab-Android/

Ein mobiles, bewusst einfaches Recherchewerkzeug für weltweite Aktien:
zwei Reiter für Strategie-Kandidaten und eine unabhängige Aktiensuche,
dazu Regionsfilter und ein optionaler Trade-Republic-AT-Filter für die Kandidaten.

## Was die App zeigt

- Aktien von unterstützten internationalen Börsen, ergänzt durch offizielle US-Börsenverzeichnisse
- **Reiter „Aktiensuche“:** eigenes Suchfeld mit Suchbutton und Enter, unabhängig von Strategie, Liquiditäts-/Momentumvorauswahl, Region und TR-AT-Filter. Durchsucht das gesamte verfügbare Namensverzeichnis sowie alle vorhandenen Kursdatensätze, mit antippbaren Vorschlägen, Ticker-/ISIN-Treffern, Akzentnormalisierung und begrenzter Tippfehlertoleranz einschließlich benachbarter Buchstabenvertauschungen. Auch Unternehmen ohne Kursdaten werden als Verzeichnistreffer gefunden und entsprechend gekennzeichnet. Charts und Fundamentaldaten bleiben bei vorhandenen Daten aufklappbar; ein Suchtreffer erhält keinen Strategie-Rang. „Kandidaten filtern“ bleibt ein lokaler Filter innerhalb der Kandidatenliste.
- Echte, datierte Tageskurse als **indikativ nach EUR umgerechnete Referenzwerte**
- Per Checkbox kombinierbare Ranglisten-Faktoren: **12–2-Monats-Momentum** (Standard), **geringe ATR(14)-Schwankung relativ zum Kurs** und **Abstand zum 200-Tage-Trend**. Bei mehreren Häkchen werden die Rangprozente 0–100 gleichgewichtet gemittelt. Fehlende Kennzahlen schließen Aktien aus dem Mix aus, statt geschätzte Nullen einzufügen. Mindestens ein Faktor bleibt ausgewählt.
- Zusätzlich optional: **„Hoch-Tief-Mut · Sander-inspiriert“**. Diese Auswahl zeigt *tatsächlich geprüfte* Aktien mit 15–55 % Rückgang vom 252-Handelstage-Hoch, positivem Nettoergebnis, positivem operativem Cashflow, ≥3 % Nettomarge und mindestens −10 % Umsatzentwicklung im jüngsten prüfbaren Jahresabschluss. Finanzdaten stammen aus aktuellen **SEC EDGAR XBRL 10-K-Berichten**, daher derzeit überwiegend US-Emittenten. Score: 50 % relativer Rückgang, 25 % Gewinnmarge und 25 % Umsatzentwicklung. Unternehmensdaten und Geschäftsjahr werden im aufgeklappten Kandidaten angezeigt. Fehlen Unternehmensdaten, wird die Aktie **nicht** als Sander-Kandidat ausgegeben. Kann separat oder mit Momentum/ATR/Trend kombiniert werden.
- **Interpretation:** Dies ist eine explizit *eigene* mechanische Teilannäherung an Beate Sanders Hoch-Tief-Mut-Ansatz, **keine exakte Umsetzung**. Deren wichtige Bestandteile langfristige Diversifikation, Dividenden, Unternehmensbewertung, überzeugendes Geschäftsmodell und Teilverkäufe sind nicht automatisiert. Auch ein starker Rückgang ist kein Beweis für eine günstige Bewertung. Keine belegte Überrendite aus dieser konkreten Screening-Regel.
- Nur Momentum hat in dieser Implementierung eine breitere wissenschaftliche Faktorgrundlage; Trend und 14-Tage-ATR-Schwankung sind **experimentelle Zusatzfaktoren**, für die unser Vergleich keinen gesicherten Mehrertrag zeigte. Die konkrete Mehrfaktorkombination ist **nicht** historisch validiert.
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
Cashflowbeträge stehen in der Berichtswährung USD. KGV und Dividendenrendite
werden mangels zuverlässig vergleichbarer Daten nicht erfunden.

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

## Kursdiagramme in jeder Aktienkarte

Beim Aufklappen wird der Kursverlauf **erst dann** geladen (kein externer TradingView-Embed). Vorgaben: **3 Monate**, schnell umschaltbar zwischen **1M, 3M, 6M, 1J, 3J, 5J und MAX** (höchstens die letzten rund zehn Jahre, soweit Daten vom Anbieter verfügbar sind). Pro Symbol erzeugt die Kursdaten-Pipeline eine separate JSON-Datei unter `docs/charts/<Ticker>.json`; ein GitHub-Actions-Cache behält Kurshistorien aus vorherigen Aktualisierungen. Bei fehlenden Kursreihen erscheint eine klare Meldung. Das Chartangebot wächst daher mit den rotierenden Börsendaten-Aktualisierungen.

Kauf-Limit- und Stop-Loss-Linien werden im Chart **nur bei aktiviertem Schalter „Kauf-Limit & Stop-Loss anzeigen“** eingeblendet. Da die Achse den Originalkurs der jeweiligen Börse zeigt, werden die vorhandenen EUR-Modellwerte mit dem **aktuellen Referenzwechselkurs** zurück in die Kurswährung umgerechnet; sie sind weder historische EUR-Kurse noch tatsächliche Broker-Orders. Die Chartreihe verwendet von Yahoo bezogene split-/dividendenbereinigte Schlusskurse, auf den letzten Originalschlusskurs skaliert. Die Modellgrenzen wurden in unseren bisherigen Tests nicht als gewinnsteigernd validiert.

## Stand der Daten und Grenzen

Die Aktienverzeichnisse umfassen viele mehr Börsenticker, als in einem sechs Stunden laufenden Aktualisierungsfenster abgefragt werden. Der öffentliche GitHub-Workflow prüft regionale Ticker in rotierenden Teilmengen. `universe_size` bezeichnet daher nur gefundene Symbole; `scanned_tickers` nur solche mit brauchbaren historischen Kursabfragen, `eligible_count` nur solche mit den nötigen EUR-/Liquiditäts-/Momentumwerten.

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

In der Aktiensuche können unter **„Strategie prüfen für:“** alle fünf bestehenden
Strategien unabhängig angehakt werden (anfangs alle aktiv). Pro Aktie erscheint
je gewählter Strategie eine textlich begründete Passung: **grün „Passt gut“, gelb
„Passt teilweise“, orange „Passt wenig“, rot „Passt schlecht“** oder **grau „Zu
wenig Daten“**. Diese Häkchen ändern weder die Namenssuche noch die Reihenfolge
oder die sichtbaren Titel; es gibt keinen pauschalen Kauf- oder Gesamtscore.

Die allgemeinen Orientierungsgrenzen sind in der Aktiensuche einsehbar:
Momentum grün ab +20 %, gelb ab 0 %, orange ab −15 %; relative ATR grün bis 2 %,
gelb bis 4 %, orange bis 6 %; Trend grün ab dem 200-Tage-Durchschnitt, gelb bis
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
