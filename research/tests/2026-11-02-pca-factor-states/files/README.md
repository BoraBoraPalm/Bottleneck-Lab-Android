# PCA-Faktoren-Gesamtstudie 2026

Zuerst `output/bericht.html` öffnen. Es ist eine selbständige HTML-Datei mit eingebetteten Abbildungen. Alternativ `output/bericht.md`.

Die Studie prüft den Vorschlag, die historischen Werte/Zustände mehrerer früher getesteter Aspekte gemeinsam zu analysieren. Alle sieben früheren Pakete wurden auf Verwendbarkeit geprüft. Das Hauptpanel enthält 44 rekonstruierbare Kurs-/Volumen-/Nachrichten-/Marktmerkmale; die Erweiterung 24 verzögerte akademische Faktorportfolio-Indikatoren. Fehlende historische firmenspezifische Fundamentaldaten wurden nicht erfunden.

## Zentrales Ergebnis

Im Vorwärtstest 2022–September 2025 schlagen PCA, PLS, Elastic Net, Ridge und ein kleiner fester nichtlinearer Vergleich die Nullprognose beim mittleren Vierwochen-Prognosefehler nicht. PCA findet stabile Achsen aus Trendlage/Risiko und Nachrichtenaufmerksamkeit. Das belegt keine hilfreiche Prognose späterer Mehrerträge. Der Bericht zeigt auch Kosten-/Rangdiagnosen, andere Horizonte, Datenlücken und verbleibende Bias-Risiken. Die App blieb unverändert.

## Wiederholen

Python 3.12; Paketversionen in requirements.txt. Bei normal installiertem Python:

```bash
python -m pip install -r requirements.txt
python run_study.py
python verify.py
python portfolio_audit.py
python rank_diagnostic.py
python report.py
```

Der Hauptlauf benötigt auf der ursprünglichen Umgebung ungefähr 3,5 Minuten. Die Daten liegen vollständig im Paket; kein erneuter Netzwerkabruf ist nötig. Originalnachrichten sind kompakte GDELT-Metadaten mit URLs, keine vollständigen Verlagstexte. Historische Kurse/FX sind unveränderte Snapshots aus der vorherigen Studie; ACWI wurde ausschließlich als zusätzlicher Vergleich geladen. Ein anderer Datenanbieter oder spätere Revisionen können andere Ergebnisse liefern.

Ein optionaler lokaler Ordner `deps` wird vor dem normalen Suchpfad berücksichtigt; er wird nicht mitgeliefert. Bei normaler Paketinstallation ist er nicht nötig.

## Dateien

- `protocol.md`, `output/protocol_lock.json`: Festlegung und Quellhashes vor dem neuen Hauptlauf. Frühere Testergebnisse waren bereits bekannt; deshalb explorative historische Folgestudie, keine neue intellektuell unberührte Bestätigung.
- `data/analysis_panel.parquet`: gemeinsame Aktien-Zeitpunkt-Matrix, inklusive expliziter Zielspalten. Nur die in data_build.py aufgezählten Merkmale dienen als Eingaben. Zukunfts-/Zustandsspalten aus älteren Dateien werden nicht als Merkmale benutzt.
- `data/prices`, `data/news_features.parquet`, `data/news_sample.parquet`: verwendete Roh-/Vorverarbeitungs-Snapshots und Nachrichtenmetadaten.
- `output/predictions_primary_4.parquet`: alle Jahres-Vorwärtsprognosen, inklusive der 14 mangels Zielkursen nicht bewertbaren Zeilen; identische Zeilen für alle Modelle.
- `output/selection_*.json`: sämtliche inneren Validierungsergebnisse und ausschließlich dort gewählte Parameter.
- `output/model_*.joblib`: gespeicherte Jahresmodelle mit sklearn-Standardobjekten. Nur aus vertrauenswürdiger Quelle laden.
- `output/results_primary.json`: unveränderte Hauptkennzahlen und die sieben primären, gemeinsam korrigierten Vergleiche.
- `output/results_12weeks.json`, `output/results_extended.json`: vorab festgelegte sekundäre Auswertungen.
- `output/loadings`, `output/pca_*`: gelernte Gewichte, vollständiges Trainings-Spektrum und interpretierende Gruppenladungen.
- `output/group_ablation_*`: deskriptive Weglassdiagnosen, keine Auswahl neuer Gewinner anhand des Testzeitraums.
- `output/integrity_audit.json`: 21 Prüfungen der zeitlichen Abgrenzung, Quellhashes, Trainingsvorverarbeitung und exakten Modellreproduktion.

## Darstellungskorrekturen und finanzielle Diagnosen

`portfolio_evaluation_note.md` dokumentiert zwei nachträgliche reine Bewertungsprüfungen, ohne neue Modellanpassung:

1. Erfolgsvergleich gegen kostenfreie Bruttobenchmarks anstelle eines fiktiv teuren ständigen Neukaufs aller Benchmark-Einzeltitel.
2. Neutrale proportionale Behandlung gleicher Prognosewerte. Elastic Net unterscheidet an 143 von 195 Stichtagen keine Aktien. Solche Gleichstände dürfen nicht durch Reihenfolge der Firmenliste scheinbare Aktienauswahl erzeugen.

Die unveränderten Originaldiagnosen liegen weiterhin in `results_primary.json` und `portfolio_diagnostic*`. Für die Interpretation der Rang-/Handelsdiagnosen sind `rank_diagnostics_tie_neutral.csv` und `portfolio_common_*` maßgeblich. Undefinierte Rangkorrelationen konstanter Vorhersagen werden dort als 0 Informationsbeitrag gemittelt und zusätzlich gezählt. MSE-, AUC-, Modell- und primäre Bootstrap-Ergebnisse ändern sich dadurch nicht.

Die Kostenrechnung schließt Positionen je Vierwochen-Kohorte vollständig und eröffnet sie neu. Sie ist konservativ und keine tatsächlich ausgeführte Portfoliohistorie. Keine österreichischen Steuern, wirklichen Spreads, historische Brokerverfügbarkeit oder vollständige Corporate-Action-Rekonstruktion. Die breite Faktor-Erweiterung ist wegen fehlender Originalvintages kein strenger Point-in-time-Nachweis.
