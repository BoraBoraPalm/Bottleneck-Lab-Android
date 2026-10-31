# Veröffentlichung

Die aktuelle App ist eine statische GitHub-Pages-Website mit einer einzigen Hauptansicht.

- Startseite: https://boraborapalm.github.io/Bottleneck-Lab-Android/
- Quelle: `docs/index.html`
- Daten: `docs/snapshot.json` (wird in GitHub Actions erzeugt, nicht manuell eingecheckt)
- Ablauf: **GitHub → Actions → Bottleneck Lab · Simplified Global Snapshot → Run workflow**
- Automatisch alle sechs Stunden; die Schaltfläche „Aktualisieren“ lädt nur den zuletzt veröffentlichten Datenstand.
- Kein Echtzeitfeed, keine Handelsorders. Historische Versionen sind über Git-History abrufbar.
