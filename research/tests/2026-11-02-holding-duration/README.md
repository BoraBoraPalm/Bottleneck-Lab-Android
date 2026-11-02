# Haltedauer, Weiterhalten und Prognosehorizonte – systematische Folgestudie

Abgeschlossen am 02.11.2026, begrenzte historische Aussage. Die App blieb unverändert.

Die vorher fehlende Intervall-/Haltedauerprüfung wurde für die dokumentierten Literaturproxies und Kursregeln tatsächlich gerechnet. Negative Tests bei 20 Sitzungen oder vier Wochen verwerfen nicht jede andere Dauer.

- [Vollständiger Ergebnisbericht](files/output/bericht.md), [HTML mit Abbildungen](files/output/bericht.html).
- [Vorab-Protokoll](files/protocol.md), [Versionen und korrigierte Zwischenwerte](files/VERSION_HISTORY.md).
- [Alle Strategien kompakt](files/output/strategy_summary.csv), [gemeinsame 32 primäre Tests](files/output/primary_tests_joint.json), [zeitlich gewählte B-Intervalle samt allen Trainingskennzahlen](files/output/trading_choices.json).
- [Zeit-/Reproduktionsprüfung und Daten-/Codehashes](files/output/verification.json).
- [Vollpaket](https://chatgpt.com/library?file_id=libfile_e52d2f0f4f008191a52aacdcedda8487&account_id=personal) mit vollständigen verwendeten Eingaben, Tagespfaden, Trades und Vorhersagen. SHA-256: `0a759f4ddc6df7096973f1f4b4c9891ab7bf16edfc62daf3396958465d4f22d4`, 55609895 Byte; vollständiges Member-/SHA-Manifest in [ARTIFACT_MEMBERS.json](ARTIFACT_MEMBERS.json).

A: 20 Familien, Signalaktualisierung alle 1/3/6/12 Monate; jährlich aus 120 abgeschlossenen Monaten gewählt, Bewertung 2014–2025. B: zwölf Handelsregeln, sechs Intervalle von 5/10/20/60/120/252 US-Sitzungen; jährlich aus fünf früheren Jahren gewählt, Bewertung 2019–2025. Endliche Ausstiege und bloßes erneutes Prüfen/Weiterhalten sind getrennt. C: fünf Modelle, sieben Horizonte von 1–52 Wochen neu gelernt, gemeinsame 15.240 Aktien-Zeitpunkte 2022–2024; keine ausgeführte 52-Wochen-Handelsstrategie.

Die Dauer verändert einzelne Handelsresultate stark; die größten historischen Renditen sind teilweise konzentriert. Korrigierte p-Werte betreffen den Zusatznutzen der Intervallwahl gegenüber derselben festen Referenz, nicht den Nachweis künftiger Marktüberlegenheit. PCA/PLS bleiben bei allen geprüften Horizonten hinter Null-Mehrertrag; der positive 52-Wochen-Baumbefund ist mit nur drei Jahren und einem null enthaltenden Blockintervall offen.

Historische Jahre waren bereits bekannt; revidierte Quellen und globale Ausführungsnäherungen bleiben Grenzen. Vollständige Hoch-Tief-Mut-/Frühwachstum-/Fundamental-Appfilter bleiben mangels historischer Vintages offen. Zum Wiederverwenden gespeicherte Ergebnisse lesen und das genaue Vollpaket wiederherstellen, keine neue Bewertung zum bloßen Nachsehen starten. Startbefehle und Paketversionen stehen im Bericht/README des Pakets.
