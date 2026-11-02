# Daten- und Konstruktionsprüfung

Prüfdatum: 1. November 2026.

## Exakte Stände

- Daten: `OpenSourceAP/CrossSection` auf Hugging Face,
  `ad1dfba5a6d80c4ce53ce6b8127f5a949dda1e40`, Ausgabe Oktober 2026.
- Geprüfter öffentlicher Code:
  https://github.com/OpenSourceAP/CrossSection/tree/9f053398c4995651d822e90d81526d0644c6f3e5
- Die Metadaten der Autoren bezeichnen die Datenausgabe als Codeversion 2.1.0.
  Der Code-Audit ersetzt keine vollständige Rekonstruktion aus WRDS-Rohdaten
  oder einen Beleg ursprünglicher Echtzeit-Datenschnappschüsse.

## Befunde

1. `Portfolios/Code/30_PredictorAltPorts.R` erzwingt bei standardisierten
   Quintilen 20%-Quantile und Marktkapitalisierungsgewichtung. Andere Merkmale,
   darunter Zuordnungsturnus und Filter, folgen den Originalimplementierungen.
2. `Portfolios/Code/01_PortfolioFunction.R` verschiebt Signalmonate um einen
   Monat für die Renditezuordnung. Value-Gewichte verwenden die vorherige
   Marktkapitalisierung. Die Signale und Portfolios werden nicht mit zukünftigen
   Monatsrenditen gewichtet. Die Zuordnungstermine folgen Startmonat und
   Halte-/Rebalancingintervall, keine ständig überlappenden Dreimonatskohorten.
3. `Signals/pyCode/Predictors/Mom12m.py` kombiniert elf vorherige Monatsrenditen
   und überspringt den aktuellen Signalmonat. Das Original-Replikationsportfolio
   wird quartalsweise neu zugeordnet. Fehlende Monatsrenditen im ursprünglichen
   Signalcode werden als null behandelt: eine zusätzliche Quellenkonvention,
   deren Auswirkung ohne Rohdaten nicht isoliert getestet wurde.
4. `Signals/pyCode/DataDownloads/CompustatQuarterly.py` setzt Quartalsdaten
   frühestens drei Monate nach Quartalsende an und verschiebt eine später
   veröffentlichte Meldung weiter nach hinten. Das ist ein festgelegter
   konservativer Lag, keine vollständige Rekonstruktion der unmittelbar nach
   jeder Pressemitteilung handelbaren Daten.
5. `Signals/pyCode/Predictors/EarningsSurprise.py` verwendet EPS-Wachstum relativ
   zum historischen Drift und zur Schwankung vorheriger Überraschungen.
   Das ist keine Analystenkonsens-Überraschung. Verfügbare historische Lags
   werden nach den Originalkonventionen verarbeitet; die Quelle verlangt nicht
   zwingend denselben streng lückenlosen 13-Quartalsnachweis wie eine eigene
   neue Implementierung. Es wird die veröffentlichte Replikation getestet.
6. `Signals/pyCode/Predictors/REV6.py` verwendet eine aktuelle und sechs
   vergangene monatliche Änderungen mittlerer Gewinnschätzungen. Trotz des
   historischen Namens REV6 sind das im geprüften Code sieben Summanden.
7. `Signals/pyCode/Predictors/ZZ2_AnnouncementReturn.py` ordnet das Ereignis dem
   Monat des letzten Tages im vollständigen Fenster zu. Der geprüfte Code
   verwendet zwei vorherige Handelstage, Meldungstag und einen Folgetag.
   Die Kurzbeschreibung in SignalDoc nennt ein leicht anderes Fenster; für den
   Replikationstest sind die tatsächlichen veröffentlichten Renditen maßgeblich.
   Die Autoren dokumentieren eine Look-ahead-Korrektur im Oktober 2024.
8. `Portfolios/Code/32_Predictor2x3Ports.R` ordnet ALLE FF93-artigen Signale nur
   im Juni neu zu. Diese Datei wurde daher nicht als primärer monatlicher
   Nachrichten-/Momentumtest verwendet, sondern nur als strukturelle Sensitivität.
9. `Portfolios/Code/11_ProcessCRSP.R` übernimmt CIZ-Monatsrenditen einschließlich
   vorhandener Delisting-Renditen. Die frühere pauschale Imputation fehlender
   Delistingverluste wird nicht angewendet. Nicht erfasste Fälle bleiben ein
   Datenrisiko; es wird keine vollständige Biasfreiheit behauptet.
10. Das Liquiditäts-Szenario schließt Aktien unter der NYSE-20%-Größenschwelle
    vor Renditezuordnung aus, behält aber ursprüngliche Gewichtungen/Quantile.
    Es ist kein reiner Ein-Parameter-Liquiditätsvergleich zum VW-Haupttest.
11. Die aktuelle Baker-Wurgler-Dokumentation meldet Datenrevisionen, fünf statt
    sechs Komponenten sowie eine Änderung des bereinigten Modells 2026.
    Für einen wirklich zeitgenössischen Sentiment-Timingtest fehlen hier
    verifizierte Veröffentlichungsvintages. Er wurde nicht fingiert mitgetestet.
12. Die frühere individuelle Aktienprüfung hatte eine heutige Überlebendenauswahl.
    Die frühere Faktorstudie wies selbst auf revidierte Indizes, bekannte
    Historien und illustrative Kosten hin. Beide ersetzen keinen unvoreingenommenen
    neuen Prospektivtest und wurden nicht als Bestätigung eines Siegers verwendet.

## Eigene Kontrollen

- 312 identische aufeinanderfolgende Monate 2000–2025, keine fehlenden Renditen
  oder künstlichen Ersatzrenditen in den ausgewählten Portfolioreihen.
- Quellenwerte in Prozent werden genau einmal zu Dezimalrenditen umgerechnet.
- Long-only-Fünftel haben keine Shortseite, positive Aktienzahlen und endliche
  Monatsrenditen. Portfolioanteile summieren sich auf eins; kein Hebel.
- Geometrische Verkettung inklusive Anfangskapital, korrekte erste Verlustphase
  im Drawdown; Gegenprüfung durch direkte Multiplikation der Monatsfaktoren.
- HAC-Standardfehler gegen geschlossene IID-Speziallösung geprüft; Holm-Verfahren
  anhand eines bekannten Zahlenbeispiels überprüft.
- Gemeinsame Bootstrap-Zeitindizes für Strategien/Benchmark; keine unabhängige
  Vermischung oder zufällige Trennung von Zukunft und Vergangenheit.
- Entwicklungs-/Walk-forward-Trainingsfenster liegen vollständig vor ihren
  Auswertungsfenstern. Keine nachträglich optimierten Mischungsgewichte.
- Kostenfaktor mathematisch auf den jährlichen Vermögensfaktor geprüft.
- EUR-Umrechnung für alle Pfade gleich; das relative Vermögen zum Markt muss
  sich algebraisch unverändert ergeben und wurde entsprechend geprüft.
- Alle vier im unabhängigen Momentum-Check betrachteten Varianten werden
  offengelegt; keine nachträgliche Auswahl nur einer günstigen Variante.

## Was dadurch nicht bewiesen ist

Kein vollständiger Rohdaten-/Vintage-Audit, keine kausale Isolation von Emotionen,
keine garantierte Handelbarkeit zu Monatsendkursen, keine bekannten historischen
Transaktionskosten, keine österreichische Nachsteuerrendite, kein Schluss von
einem rückblickenden Höchstwert auf die beste zukünftige Strategie. Blockverfahren
erfassen Stichprobenunsicherheit unter ihren Abhängigkeitsannahmen; sie schützen
nicht vor künftigen Strukturbrüchen oder unbekannten Datenfehlern.
