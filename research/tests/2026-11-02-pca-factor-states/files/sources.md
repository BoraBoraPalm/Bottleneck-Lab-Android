# Herkunft und Methoden

## Bereits vorhandene Testpakete

Alle wurden in der vorherigen Bestandsprüfung aus ihrem aktuellen gespeicherten Stand gelesen und mit Dateihashes dokumentiert. Paketmitglieder stehen in `sources/prior_packages.json`, Ebenen und ursprüngliche Spalten in `sources/source_inventory.json`, Verwendung in `sources/prior_study_use.csv`.

- Stimmungsmodell_Globaler_Pilot_2026.zip — https://chatgpt.com/library?file_id=libfile_f3dbb35d015c8191856387bb0bb2ff16&account_id=personal
- Behavioral_Strategien_Benchmark_2026.zip — https://chatgpt.com/library?file_id=libfile_eb7efca016688191a682289a9e09e551&account_id=personal
- Bottleneck_Trading_Rules_Independent_2026.zip — https://chatgpt.com/library?file_id=libfile_c3afd081f67881918a9b714611ad5457&account_id=personal
- Bottleneck_Scientific_Factor_Study.zip — https://chatgpt.com/library?file_id=libfile_a7a7e430a70c81918a7eae4dddd4b40c&account_id=personal
- Bottleneck_Momentum_12_2_Research.zip — https://chatgpt.com/library?file_id=libfile_9411fbe17e5081918573115989254416&account_id=personal
- Bottleneck_Lab_ATR_Grenzen_Sensitivitaet.zip — https://chatgpt.com/library?file_id=libfile_e4ca48b909fc819186a4bc128f46a91d&account_id=personal
- Bottleneck_Lab_5Jahre_Backtest_komplett.zip — https://chatgpt.com/library?file_id=libfile_7f26d8bebe048191976b08afcb65337b&account_id=personal

## Originaldaten

- PwC Global Top 100, 31.03.2018: https://preview.thenewsmarket.com/Previews/PWC/DocumentAssets/514404.pdf . Historisch festgelegte Firmenkohorte, nicht repräsentativ für sämtliche Aktien oder Unicorn-Kandidaten.
- GDELT GKG 2.1: https://data.gdeltproject.org/documentation/GDELT-Global_Knowledge_Graph_Codebook-V2.1.pdf . Wortton des ganzen Artikels, keine direkte Anlegeremotion oder garantierte firmenspezifische Aussage. Wöchentliche 15-Minuten-Stichprobe, englischer und übersetzter Stream. Archiv-URLs, Fehlstellen und Hashes im Datenmanifest. Metadaten mit Zuschreibung an GDELT; keine vollständigen Verlagstexte enthalten.
- Yahoo Finance Chart API: verwendete Kurs-/FX-Snapshots aus dem bisherigen Paket, ursprüngliche URLs/Hashes in `data/prices_manifest.json`; zusätzlicher ACWI-Abruf nur als Benchmark in `sources/acwi_manifest.json`. Aktuelle adjustierte Daten, keine lückenlosen Originalvintages, kein handelbarer Geld-/Briefkursfeed. Keine Zusicherung von Weitervertriebsrechten für einen kommerziellen Dienst.
- Roche ROG/ROP 1:1-Umtausch: https://www.roche.com/investors/updates/inv-update-2026-03-16 . Die im vorherigen Paket verwendete wirtschaftlich gleichwertige Kursfortführung bleibt erhalten.
- OpenSourceAP und Kenneth French: ursprüngliche Quellen im kopierten `sources/behavioral_sources.json`; festgehaltene Methodik in `sources/behavioral_protocol.json`. Die zusätzlichen monatlichen Faktorportfoliorenditen wurden rückblickend rekonstruiert. Eine 62-Tage-Verzögerung ersetzt keine dokumentierte Veröffentlichungshistorie. Sie werden nur als gesonderte Sensitivität betrachtet, nicht als bekannte damalige Fundamentaldaten einzelner Firmen.

## Primäre Methodenliteratur

- scikit-learn: Principal Component Regression vs Partial Least Squares Regression. https://scikit-learn.org/stable/auto_examples/cross_decomposition/plot_pcr_vs_pls.html . PCA maximiert Eingabevarianz ohne Zielgröße; PLS berücksichtigt die Zielgröße bei der Richtungswahl. Ein möglicher Vorhersagevorteil muss trotzdem auf zeitlich späteren Daten geprüft werden.
- scikit-learn: Common pitfalls / Data leakage. https://scikit-learn.org/stable/common_pitfalls.html . Vorverarbeitung ausschließlich innerhalb der Trainingsdaten.
- scikit-learn: TimeSeriesSplit. https://scikit-learn.org/stable/modules/generated/sklearn.model_selection.TimeSeriesSplit.html . Verwendet wird hier eine eigene Panel-Zeittrennung mit tatsächlichen Abschlussdaten der Ziele, nicht ein zufälliger Zeilensplit und kein unbedacht auf Einzelzeilen angewandtes Standard-KFold.
- Gu S, Kelly B, Xiu D. Empirical Asset Pricing via Machine Learning. Review of Financial Studies. 2020;33:2223–2273. https://academic.oup.com/rfs/article/33/5/2223/5758276 . Motiviert die Prüfung gemeinsam wirkender Signale und nichtlinearer Wechselwirkungen. Diese viel breitere Studie ist keine Replikation oder Erfolgsgarantie für unser kleines Datenpanel.
