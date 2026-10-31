# Bottleneck Lab — schlanker weltweiter Aktien-Screener

**Website:** https://boraborapalm.github.io/Bottleneck-Lab-Android/

Ein mobiles, bewusst einfaches Recherchewerkzeug für weltweite Aktien:
eine Liste, eine Suche, ein Regionsfilter und ein optionaler Trade-Republic-AT-Filter.

## Was die App zeigt

- Aktien von unterstützten internationalen Börsen, ergänzt durch offizielle US-Börsenverzeichnisse
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

Datenquelle: [SEC EDGAR CompanyFacts API](https://www.sec.gov/search-filings/edgar-application-programming-interfaces), XBRL und offizielle SEC-Ticker/CIK-Zuordnung. Jährliche 10-K-/10-K/A-Berichte werden auf **Fiskaljahr-Geschäftszahlen (335–385 Tage)** geprüft, mit echtem Filing-Datum, Geschäftsjahresende und vergleichbarer Einheit USD. Quartalsdaten, unbestätigte Drittanbieter-Schätzungen sowie Unternehmen ohne Finanznachweise fallen heraus. Um API-Grenzen einzuhalten, werden pro Aktualisierung nur bis zu 35 SEC-Unternehmen geprüft und Werte 28 Tage zwischengespeichert. Die Abdeckung wächst mit Datenaktualisierungen. Ist die SEC nicht erreichbar, werden keine erfundenen Fundamentalwerte ausgegeben.

**Beate Sander persönlich beschrieb** breite Diversifikation, langfristiges Halten, antizyklische Nachkäufe gut aufgestellter Unternehmen und gelegentliche Teilverkäufe. Interviews: [herCAREER](https://www.her-career.com/beate-sander-ich-koenne-ja-auch-auf-kreuzfahrten-unterwegs-sein-aber-ich-arbeite-lieber-so-viel-wie-eine-junge-startup-gruenderin/) und [Trading-Ideen](https://www.trading-ideen.de/wordpress/interview-mit-beate-sander/). Die Prozentgrenzen im Screener stammen **von uns**, nicht aus einer von Sander veröffentlichten festen Formel.

## Kursdiagramme in jeder Aktienkarte

Beim Aufklappen wird der Kursverlauf **erst dann** geladen (kein externer TradingView-Embed). Vorgaben: **3 Monate**, schnell umschaltbar zwischen **1M, 3M, 6M, 1J, 3J, 5J und MAX** (höchstens die letzten rund zehn Jahre, soweit Daten vom Anbieter verfügbar sind). Pro Symbol erzeugt die Kursdaten-Pipeline eine separate JSON-Datei unter `docs/charts/<Ticker>.json`; ein GitHub-Actions-Cache behält Kurshistorien aus vorherigen Aktualisierungen. Bei fehlenden Kursreihen erscheint eine klare Meldung. Das Chartangebot wächst daher mit den rotierenden Börsendaten-Aktualisierungen.

Kauf-Limit- und Stop-Loss-Linien werden im Chart **nur bei aktiviertem Schalter „Kauf-Limit & Stop-Loss anzeigen“** eingeblendet. Da die Achse den Originalkurs der jeweiligen Börse zeigt, werden die vorhandenen EUR-Modellwerte mit dem **aktuellen Referenzwechselkurs** zurück in die Kurswährung umgerechnet; sie sind weder historische EUR-Kurse noch tatsächliche Broker-Orders. Die Chartreihe verwendet von Yahoo bezogene split-/dividendenbereinigte Schlusskurse, auf den letzten Originalschlusskurs skaliert. Die Modellgrenzen wurden in unseren bisherigen Tests nicht als gewinnsteigernd validiert.

## Stand der Daten und Grenzen

Die Aktienverzeichnisse umfassen viele mehr Börsenticker, als in einem sechs Stunden laufenden Aktualisierungsfenster abgefragt werden. Der öffentliche GitHub-Workflow prüft regionale Ticker in rotierenden Teilmengen. `universe_size` bezeichnet daher nur gefundene Symbole; `scanned_tickers` nur solche mit brauchbaren historischen Kursabfragen, `eligible_count` nur solche mit den nötigen EUR-/Liquiditäts-/Momentumwerten.

Datenquellen: [Adanos – globales Aktienverzeichnis](https://github.com/adanos-software/free-ticker-database), Nasdaq Trader, inoffizielle Yahoo-Finance-Tageskurse (US-Fallback Stooq), Frankfurter-Referenzwechselkurse sowie [TR AT – offizielle Wertpapierliste](https://assets.traderepublic.com/assets/files/AT/Instrument_Universe_AT_en.pdf). Fehlende Daten bleiben fehlend. Kurse sind **keine** tatsächlichen Trade-Republic-Geld-/Briefpreise. Kein Zugriff auf das Brokerkonto, keine Käufe oder Verkäufe. Delistings, Splits, Dividenden, Gebühren und österreichische Besteuerung werden nicht als historische Trading-Performance modelliert.

## Betrieb

Der aktive Workflow ist `.github/workflows/market-data-pages.yml`; er läuft alle sechs Stunden und bei relevanten Änderungen. Die Website kommt aus `docs/index.html`, die generierte Daten-Datei heißt `docs/snapshot.json`. Manuell starten: GitHub → Actions → **Bottleneck Lab · Simplified Global Snapshot** → **Run workflow**. Die Website-Schaltfläche „Aktualisieren“ lädt nur den zuletzt veröffentlichten Snapshot erneut, sie startet keine Datenabfrage.

Die Offline-Tests prüfen geografische Symbolübersetzung, EUR-Konvertierung, die Broker-ISIN-Verifizierung, 12–2-Monats-Momentum, die regionale Auswahl und den Verzicht auf alte Scores; ein Frontend-Check schützt vor doppeltem Code hinter der HTML-Datei.

## Alte Versionen

Frühere Reiter, deren alte **nicht validierte** Kauf-/Stop-Signalmodelle, Forschungs-Backtests, die frühere Android-APK und deren Quellcode bleiben durch die Git-Commit-Historie rekonstruierbar. Diese historischen, nicht ausreichend validierten Ansätze gehören bewusst **nicht** mehr zum aktuellen App-Build.
