# Bottleneck Lab – Hosting

Die Website wird aus `docs/index.html` via GitHub Pages veröffentlicht. Der Datenabruf läuft in GitHub Actions und veröffentlicht die tatsächlichen letzten Tageskurse als `docs/snapshot.json` im Website-Artefakt.

## Einmalig aktivieren
GitHub Repository → **Settings → Pages → Build and deployment → Source: GitHub Actions**.

## Danach
Github → Actions → **Refresh data and publish Bottleneck Lab** → **Run workflow**.

Nach erfolgreichem Deployment:
https://boraborapalm.github.io/Bottleneck-Lab-Android/

Der Button **Snapshot laden** in der Website lädt lediglich den letzten veröffentlichten Datensatz; er startet keinen neuen GitHub-Workflow. Der Workflow ist zusätzlich viermal täglich terminiert. Dies ist kein echter Realtime-Feed.

Ohne erfolgreiche Pages-Veröffentlichung existiert keine live erreichbare Website.
