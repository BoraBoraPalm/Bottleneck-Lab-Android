# Kurs auf Knopfdruck (optional)

Kleiner Cloudflare Worker im Gratis-Tarif, der für die Aktiensuche einen einzelnen Yahoo-Tagesschlusskurs nachlädt. Das Antwortformat entspricht `docs/charts/<TICKER>.json`. Die App funktioniert auch ohne ihn und zeigt dann nur die gespeicherten Kurse.

- `quote-worker.js`: der Worker. Feste Zieladresse (Yahoo Chart), strenge Symbolprüfung, Browserzugriff nur von `https://boraborapalm.github.io`.
- `../wrangler.jsonc` (im Hauptordner): Konfiguration für das automatische Deployment über Cloudflare Workers Builds. Projektname `bottleneck-lab-android`, Git branch `master`, Deploy command `npx wrangler deploy`, kein Build command.
- Test: `node tests/test_quote_worker.mjs`

**Zwischenspeichern:** Der Worker liefert nur abgeschlossene Schlusskurse. Den Balken einer noch laufenden Sitzung lässt er weg. `expires` und `Cache-Control` gelten bis 30 Minuten nach dem nächsten regulären Handelsschluss, höchstens 24 Stunden. So lange verwendet der Browser die gespeicherte Antwort. Fehler werden nie zwischengespeichert.

**Kosten:** Gratis-Tarif mit 100.000 Abrufen pro Tag. Ist das Limit erreicht, antwortet Cloudflare mit einem Fehler (1027); es wird nichts berechnet.

**Deployment prüfen:** `https://bottleneck-lab-android.markus-schuster-dev.workers.dev/version` zeigt die ausgelieferte Fassung. `{"error":"path"}` bedeutet: Cloudflare liefert noch eine Version ohne diesen Endpunkt aus, das automatische Bauen aus GitHub ist dann nicht aktiv (Cloudflare → Settings → Build: Git-Verbindung und Branch `master` prüfen).
