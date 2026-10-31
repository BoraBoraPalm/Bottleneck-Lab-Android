# Bottleneck Lab — schlanker weltweiter Aktien-Screener

**Website:** https://boraborapalm.github.io/Bottleneck-Lab-Android/

Ein mobiles, bewusst einfaches Recherchewerkzeug für weltweite Aktien:
eine Liste, eine Suche, ein Regionsfilter und ein optionaler Trade-Republic-AT-Filter.

## Was die App zeigt

- Aktien von unterstützten internationalen Börsen, ergänzt durch offizielle US-Börsenverzeichnisse
- Echte, datierte Tageskurse als **indikativ nach EUR umgerechnete Referenzwerte**
- Historisches **12–2-Monats-Momentum** (ungefähr 252 bis 42 Handelstage vor dem Signal)
- Nur Titel mit einer EUR-Referenznotierung ab 2 € und durchschnittlich mindestens 2 Mio. € täglichen 20-Tage-Handelsumsatz, sofern die Daten existieren
- „Auswahl“: bis zu 20 Momentum-Kandidaten mit höchstens vier je Region; „Alle geprüften“: bis zu 75 Treffer der Filter
- Trade Republic Österreich: nur eindeutige ISIN-Treffer in der offiziellen Instrumentenliste (keine Echtzeit-Handelsfreigabe)

Es werden **keine konkreten Käufe, Stop-Loss-Orders oder künftige Renditen** vorhergesagt. Die alte 60-Tage-Score- und ATR-Handelslogik ist entfernt, weil sie in den bisherigen Tests keinen belastbaren Vorteil gezeigt hat. Auch das neue Momentum-Screening ist **nicht als profitabel validiert**. Die akademischen Faktoruntersuchungen betrafen hauptsächlich US-Daten und sind kein Beweis für diese weltweite konkrete Aktienliste.

## Stand der Daten und Grenzen

Die Aktienverzeichnisse umfassen viele mehr Börsenticker, als in einem sechs Stunden laufenden Aktualisierungsfenster abgefragt werden. Der öffentliche GitHub-Workflow prüft regionale Ticker in rotierenden Teilmengen. `universe_size` bezeichnet daher nur gefundene Symbole; `scanned_tickers` nur solche mit brauchbaren historischen Kursabfragen, `eligible_count` nur solche mit den nötigen EUR-/Liquiditäts-/Momentumwerten.

Datenquellen: [Adanos – globales Aktienverzeichnis](https://github.com/adanos-software/free-ticker-database), Nasdaq Trader, inoffizielle Yahoo-Finance-Tageskurse (US-Fallback Stooq), Frankfurter-Referenzwechselkurse sowie [TR AT – offizielle Wertpapierliste](https://assets.traderepublic.com/assets/files/AT/Instrument_Universe_AT_en.pdf). Fehlende Daten bleiben fehlend. Kurse sind **keine** tatsächlichen Trade-Republic-Geld-/Briefpreise. Kein Zugriff auf das Brokerkonto, keine Käufe oder Verkäufe. Delistings, Splits, Dividenden, Gebühren und österreichische Besteuerung werden nicht als historische Trading-Performance modelliert.

## Betrieb

Der aktive Workflow ist `.github/workflows/market-data-pages.yml`; er läuft alle sechs Stunden und bei relevanten Änderungen. Die Website kommt aus `docs/index.html`, die generierte Daten-Datei heißt `docs/snapshot.json`. Manuell starten: GitHub → Actions → **Bottleneck Lab · Simplified Global Snapshot** → **Run workflow**. Die Website-Schaltfläche „Aktualisieren“ lädt nur den zuletzt veröffentlichten Snapshot erneut, sie startet keine Datenabfrage.

Die Offline-Tests prüfen geografische Symbolübersetzung, EUR-Konvertierung, die Broker-ISIN-Verifizierung, 12–2-Monats-Momentum, die regionale Auswahl und den Verzicht auf alte Scores; ein Frontend-Check schützt vor doppeltem Code hinter der HTML-Datei.

## Alte Versionen

Frühere Reiter, hypothetische ATR-Orders, Forschungs-Backtests, die frühere Android-APK und deren Quellcode bleiben durch die Git-Commit-Historie rekonstruierbar. Diese historischen, nicht ausreichend validierten Ansätze gehören bewusst **nicht** mehr zum aktuellen App-Build.
