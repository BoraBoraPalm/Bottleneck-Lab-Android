"""Generate the German research note and scientific figures from frozen outputs."""
from __future__ import annotations
import pathlib,json,html,platform,importlib.metadata
import numpy as np,pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
R=pathlib.Path(__file__).resolve().parent;O=R/'output';D=R/'data'
res=json.loads((O/'results.json').read_text());cov=json.loads((O/'coverage.json').read_text());strong=json.loads((O/'state_robustness.json').read_text());joint=json.loads((O/'joint_state_diagnostic.json').read_text());audit=json.loads((O/'integrity_audit.json').read_text());cent=pd.read_csv(O/'category_centers.csv');rates=pd.read_csv(O/'conditional_rates.csv');pred=pd.read_parquet(O/'test_predictions.parquet');co=pd.read_csv(D/'cohort.csv');news=pd.read_parquet(D/'news_sample.parquet');feat=pd.read_parquet(D/'news_features.parquet')
NAMES={-1:'Zu wenig Daten',0:'Überwiegend negativ',1:'Stark widersprüchlich',2:'Viel Aufmerksamkeit, eher negativ',3:'Viel Aufmerksamkeit, gemischt',4:'Ruhig, leicht positiv',5:'Deutlich positiv'}
COLORS={-1:'#9299a3',0:'#bd3e46',1:'#dc8a31',2:'#b66d36',3:'#d0b13d',4:'#75a77b',5:'#26836e'}
plt.rcParams.update({'font.family':'DejaVu Sans','font.size':10,'axes.spines.top':False,'axes.spines.right':False,'figure.facecolor':'white','axes.titleweight':'bold'})
# Improvement in proper prediction loss, normalized to each relevant baseline.
rows=[]
for t,label,metric,bkey in [('state_forecast','Nachrichtenkategorie: einfache Übergänge','logloss','transition'),('return','Relative Kursrichtung','brier','price_only'),('volume','Erhöhte Handelsaktivität','brier','price_only')]:
 e=next(x for x in res['primary_tests'] if x['target']==t);base=res[t]['test'][bkey][metric];rows.append((label,100*e['effect']/base,100*e['ci_low']/base,100*e['ci_high']/base))
e=strong['comparison'];b=strong['baseline_metrics']['logloss'];rows.insert(1,('Nachrichtenkategorie: stärkerer Vergleich*',100*e['effect']/b,100*e['ci_low']/b,100*e['ci_high']/b))
fig,ax=plt.subplots(figsize=(10.5,4.2));ys=np.arange(len(rows))[::-1]
for y,(label,v,lo,hi) in zip(ys,rows):
 color='#26836e' if lo>0 else '#bd3e46' if hi<0 else '#b58630';ax.errorbar(v,y,xerr=[[v-lo],[hi-v]],fmt='o',color=color,capsize=5,markersize=7)
ax.set_yticks(ys,[r[0] for r in rows]);ax.axvline(0,color='#687180',lw=1);ax.grid(axis='x',alpha=.2);ax.set_xlabel('Verringerung des Prognosefehlers in %; rechts = besser');ax.set_title('Test 2023–2025: Zusatznutzen von Nachrichtenmerkmalen',loc='left',pad=16)
fig.text(.02,.015,'95%-Intervalle: gemeinsame Kalenderwochen in 8-Wochen-Blöcken. *Nachträglich ergänzter Vergleich.',fontsize=8,color='#525b68');fig.tight_layout(rect=(0,.065,1,1));fig.savefig(O/'prognosevergleich.png',dpi=180);plt.close(fig)
fig,axes=plt.subplots(1,2,figsize=(11.5,5.2),sharey=True)
for ax,task,title in zip(axes,['return','volume'],['Übertrifft regionalen Aktienkorb','Handelsvolumen über jüngster Basis']):
 q=rates[(rates.target==task)&(rates.state>=0)].sort_values('state');ys=np.arange(len(q))[::-1]
 for y,row in zip(ys,q.itertuples()):ax.errorbar(100*row.event_rate,y,xerr=[[100*(row.event_rate-row.ci_low)],[100*(row.ci_high-row.event_rate)]],fmt='o',color=COLORS[row.state],capsize=4)
 ax.set_yticks(ys,[NAMES[int(s)] for s in q.state]);ax.set_title(title,loc='left',fontsize=11,pad=12);ax.axvline(100*res[task]['test']['frequency']['base_rate'],ls='--',color='#9299a3',lw=1);ax.set_xlabel('Historische Häufigkeit in %');ax.grid(axis='x',alpha=.2);ax.set_xlim(30,66)
fig.suptitle('Was folgte auf welche Nachrichtenkategorie?',x=.02,ha='left',fontweight='bold',fontsize=13);fig.text(.02,.01,'Deskriptiv, keine Kausalität. 95%-Intervalle aus Wochenblöcken; Unterschiede zwischen Firmen bleiben enthalten.',fontsize=8);fig.tight_layout(rect=(0,.06,1,.93));fig.savefig(O/'reaktionen_nach_kategorie.png',dpi=180);plt.close(fig)

# A single source for both Markdown and self-contained HTML.
md=[];ht=[]
def title(s):md.append('# '+s);ht.append('<h1>'+html.escape(s)+'</h1>')
def heading(s):md.append('## '+s);ht.append('<h2>'+html.escape(s)+'</h2>')
def para(s):md.append(s);ht.append('<p>'+html.escape(s)+'</p>')
def table(cols,rows):
 md.append('| '+' | '.join(cols)+' |\n| '+' | '.join(['---']*len(cols))+' |\n'+'\n'.join('| '+' | '.join(str(v).replace('|','/') for v in r)+' |' for r in rows));ht.append('<div class="tablewrap"><table><thead><tr>'+''.join('<th>'+html.escape(c)+'</th>' for c in cols)+'</tr></thead><tbody>'+''.join('<tr>'+''.join('<td>'+html.escape(str(c))+'</td>' for c in r)+'</tr>' for r in rows)+'</tbody></table></div>')
def fig(name,alt):
 md.append(f'![{alt}]({name})');import base64
 ht.append('<figure><img alt="'+html.escape(alt)+'" src="data:image/png;base64,'+base64.b64encode((O/name).read_bytes()).decode()+'"></figure>')
def f(x,n=3):return f'{x:.{n}f}'.replace('.',',')
def pct(x):return f(100*x,1)+' %'
title('Stimmung, Erwartungen und Anlegerreaktionen')
para('Internationaler historischer Pilotversuch · 1. November 2026 · Kein Eingriff in die Aktien-App')
heading('Das Ergebnis')
para('Ein statistisches Modell für Nachrichtenstimmung wurde tatsächlich trainiert und außerhalb seiner Lernjahre getestet. Es verbessert die Wahrscheinlichkeitsprognose der nächsten Nachrichtenkategorie. Die zusätzliche Information verbessert in diesem Versuch weder die spätere relative Kursrichtung noch belastbar die Handelsaktivität. Ein rentables Handelssystem oder eine weltweit gültige psychologische Marktregel ist damit nicht nachgewiesen.')
gain=1-strong['candidate_metrics']['logloss']/strong['baseline_metrics']['logloss']
para('Gegenüber einem stärkeren Vergleich, der bereits die aktuelle Kategorie, die Firma und ihre Region kennt, sinkt der Logloss um '+pct(gain)+'. Die häufigste prognostizierte Kategorie wird dabei nicht häufiger richtig getroffen: '+pct(strong['candidate_metrics']['accuracy'])+' gegenüber '+pct(strong['baseline_metrics']['accuracy'])+'. Der Nutzen liegt in der gesamten Wahrscheinlichkeitsverteilung. Dieser stärkere Vergleich wurde nach den drei primären Tests ergänzt; er ist eine zusätzliche Diagnose.')
heading('Daten und tatsächliche Reichweite')
para('Stichprobenrahmen sind sämtliche 100 Unternehmen aus der PwC-Weltrangliste vom 31. März 2018. Damit wurden Unternehmen vor den Lern- und Testjahren gewählt. Diese Auswahl umfasst 19 damalige Unternehmensländer und sechs Regionen. Die Auswahl großer Konzerne ist ausdrücklich kein Modell sämtlicher weltweiter Aktien oder früher Unicorn-Kandidaten.')
para('GDELT GKG 2.1: jeden Mittwoch um 12:00 UTC von Januar 2019 bis Dezember 2025 der englische und der übersetzte Archiv-Stream, 732 angeforderte Dateien. 729 waren verfügbar; eine Übersetzungsdatei vom 13.11.2019 und beide Dateien vom 22.03.2023 fehlten. Die Messung dieser beiden Wochen wird als unvollständig markiert. Es handelt sich um eine feste 15-Minuten-Stichprobe pro Woche. Häufigkeit ist Aufmerksamkeit innerhalb dieser Stichprobe, kein vollständiges weltweites Nachrichtenvolumen.')
para(f'{cov["unique_urls"]:,} unterschiedliche URLs ergeben {cov["news_rows"]:,} Firma-Artikel-Verknüpfungen in {cov["languages"]} Sprachcodes; 90 der 100 Firmen haben überhaupt einen Treffer. Nachrichten mit mehreren Firmen zählen bei jeder erwähnten Firma. Syndizierte Meldungen mit verschiedenen URLs können weiterhin mehrfach auftreten. Das Auswahl- und Timing-Schema ist unabhängig von späteren Renditen.')
para('Der Ton ist der lexikalische Ton des ganzen Artikels. Ein beiläufig erwähnter Firmenname, eine Übersetzung oder ein politisches Ereignis kann die Zuordnung verzerren. Es wurden keine historischen Texte mit einem heutigen, möglicherweise über spätere Kurse informierten Sprachmodell nachbewertet. Ein URL-Hinweis auf das Unternehmen dient als zusätzlicher, unvollkommener Fokus-Indikator; er ersetzt keine manuell validierte firmenspezifische Sentimentanalyse.')
reg=co.groupby('region').agg(companies=('rank','size'),countries=('country','nunique'))
table(['Region','Firmen im Rahmen','Länder','Zustands-Testfälle mit Folgemessung'],[(r,int(x.companies),int(x.countries),int(((pred.target_kind=='state_forecast')&(pred.region==r)).sum())) for r,x in reg.iterrows()])
para('Der bedingte Stimmungs-Test umfasst letztlich 2.631 Firmenwochen von 50 Unternehmen in 13 Ländern; rund 75 % seiner Beobachtungen kommen aus Nordamerika. In Europa verbessert sich der stärkere Vergleich nicht: Logloss 1,539 beim Vergleich, 1,547 beim Nachrichtenmodell. Asien enthält in diesem Test nur vier Firmen. Für Afrika, Lateinamerika und Ozeanien gibt es keine ausreichend dichten Zustandsfolgen. Das Gesamtergebnis ist daher keine regionale Validierung für die ganze Welt.')
heading('Die sechs aus den Lerndaten gebildeten Kategorien')
para('KMeans mit vorab festgelegten sechs Clustern wurde ausschließlich auf Nachrichten aus 2019–2021 angepasst. Merkmale: mittlerer Wortton, positive plus negative Wortanteile, Streuung des Tons, logarithmierte Zahl der Meldungen und Quellen. Die Namen wurden aus den Zentren abgeleitet; spätere Kursverläufe bestimmen weder Zuordnung noch Namen. Eine Kategorie benötigt mindestens zwei verschiedene URLs aus zwei Quellen und vollständige Archiv-Streams.')
catrows=[]
for row in cent.itertuples():
 catrows.append((int(row.state),NAMES[row.state],f(row.tone,2),f(row.dispersion,2),f(row.approx_articles,1)))
table(['ID','Kategorie','Mittlerer Wortton','Streuung','Meldungen am Clusterzentrum*'],catrows)
para('*Rücktransformierter logarithmischer Mittelpunkt, keine durchschnittliche Gesamtzahl aller Nachrichten. „Zu wenig Daten“ erhält ID −1 und keine neutrale/positive Wertung. Nur 9.375 der 36.600 möglichen Firmenwochen haben hinreichende Nachrichten. Im Kurs-Test sind etwa 75 % der aktuellen Zustände unbekannt. „Panik“ und „Euphorie“ bleiben psychologische Hypothesen; diese Wörter werden nicht als gemessene Anlegerzustände ausgegeben.')
train=feat[feat.date<'2022-01-01'];change=train.loc[(train.coverage==1)&train.tone_lag1.notna(),'tone_change'].dropna();q25,q75=change.quantile([.25,.75]);para('Die Richtung kann ergänzend „aufhellend“, „stabil“ oder „eintrübend“ heißen. Als beschreibende Schwellen dienen das 25. und 75. Perzentil der Tonänderung in den Lerndaten: '+f(q25,2)+' und '+f(q75,2)+'. Das Modell verwendet die kontinuierliche Änderung. Ein positiver Ton allein belegt weder Euphorie noch einen günstigen Einstiegspreis.')
heading('Modell und zeitliche Prüfung')
para('Drei getrennte Aufgaben: (1) die Kategorie der folgenden frischen Wochen-Stichprobe, (2) die Aktienrendite der folgenden Handelswoche relativ zu ihrem Vergleichskorb, (3) ein durchschnittliches Handelsvolumen der Folgewoche über dem zuvor beobachteten 20-Tage-Mittel. Aktuelle und folgende Zustandsziele teilen keine Artikel; rollende Vierwochenmerkmale sind ausschließlich Eingaben.')
para('Alle Kandidaten sind regularisierte logistische Regressionen mit festem C=1. Kurskontrollen: vergangene 5/20/60-Handelstage-Renditen, 20/60-Tage-Volatilität, jüngstes relatives Volumen, Firma und Region. Das kombinierte Modell erhält zusätzlich Nachrichtenmerkmale, deren Änderung und die aktuelle Kategorie. Modelle und Cluster werden auf 2019–2021 trainiert. 2022 ist ein reines Diagnosejahr. Der Test 2023–2025 beginnt am 18.01.2023 und endet mit dem Archivstichtag 17.12.2025; die Grenzbereiche wurden mit mindestens zwei Wochen Abstand ausgespart. Es gab keine Modellsuche oder Anpassung anhand der Validierungs- oder Testkennzahlen.')
para('Kursmerkmale enden spätestens am Dienstag vor dem Archivmittwoch. Für Reaktionsziele gilt der erste lokale Handelstag ab dem folgenden Montag, mindestens fünf Kalendertage später. Kursrenditen laufen vom adjustierten Eröffnungskurs bis zum entsprechenden Eröffnungskurs der nächsten Woche. Der Puffer vermeidet unrealistische unmittelbare Ausführung und testet zugleich nur verzögerte Reaktionen. Ein mögliches Signal innerhalb der ersten Stunden wird damit nicht geprüft.')
para('Benchmark für relative Rendite ist ein gleichgewichteter USD-Korb der zeitgleich verfügbaren Firmen derselben Region. Bei weniger als fünf Firmen wird der globale historische Korb verwendet. Devisen beruhen auf dem letzten verfügbaren Schluss vor der lokalen Handelssitzung; das ist eine Näherung. Der Korb ist ein statistischer Vergleich, kein MSCI World und kein vollständig handelbarer Index. ADRe und unterschiedliche Aktiengattungen begrenzen die Vergleichbarkeit des Volumens. Für historische Abspaltungen wurden keine heutigen Nachfolger unbesehen fortgeführt: DowDuPont endet Mai 2019, United Technologies April 2020.')
heading('Testresultate und Unsicherheit')
rr=[]
for t,label,metric,bk,mk in [('state_forecast','Nächste Nachrichtenkategorie','logloss','transition','news_model'),('return','Relative Kursrichtung','brier','price_only','news_price'),('volume','Erhöhte Handelsaktivität','brier','price_only','news_price')]:
 x=res[t]['test'];e=next(z for z in res['primary_tests'] if z['target']==t);rr.append((label,x[mk]['n'],metric,f(x[bk][metric],6),f(x[mk][metric],6),f(e['p_holm'],4)))
table(['Primäre Aufgabe','Testfälle','Fehlermaß (kleiner besser)','Vergleich','Nachrichtenmodell','p, Holm-korrigiert'],rr)
para('Die primäre Stimmungs-Baseline lernt Übergangshäufigkeiten zwischen den sechs Zuständen. Die Kurs- und Aktivitäts-Baselines kennen bereits die genannten Preis-/Volumenmerkmale. Eine konstante, nur im Training geschätzte Ereignishäufigkeit erreicht beim Kursziel sogar einen besseren Brier-Fehler (0,249851) als beide komplexeren Modelle. Die Modelle liefern hier keinen belastbaren Vorteil bei der Aktienauswahl.')
table(['Zusätzlicher Vergleich','Basis','Nachrichtenmodell','95%-Intervall der Fehlerverringerung'],[('Stimmung: aktuelle Kategorie + Firma + Region',f(strong['baseline_metrics']['logloss'],6),f(strong['candidate_metrics']['logloss'],6),f(strong['comparison']['ci_low'],6)+' bis '+f(strong['comparison']['ci_high'],6)),('Nächste Kategorie inkl. fehlender Messung',f(joint['baseline_logloss'],6),f(joint['candidate_logloss'],6),f(joint['comparison']['ci_low'],6)+' bis '+f(joint['comparison']['ci_high'],6))])
para('Diese beiden Zusatzdiagnosen wurden nach Sichtung der primären Ergebnisse ergänzt; das getestete Nachrichtenmodell und seine Kursmodelle wurden dafür nicht nachjustiert. Für den zweiten Vergleich wird ein separater Verfügbarkeitskopf nur auf den Lernjahren trainiert. Er verteilt die Wahrscheinlichkeit zunächst auf „nächste Woche messbar“ und „nicht messbar“, danach auf die sechs Kategorien. So wird die Auswertung nicht auf nachträglich bekannte Folgeberichterstattung beschränkt: 3.713 zum Prognosezeitpunkt messbare Firmenwochen, davon nur 70,9 % auch nächste Woche messbar. Der Logloss verbessert sich hier um '+pct(1-joint['candidate_logloss']/joint['baseline_logloss'])+'; ein Teil des Gewinns betrifft die Vorhersage der Datenverfügbarkeit. Dies ist keine zusätzliche Messung menschlicher Emotionen.')
para('Konfidenzintervalle und einseitige Nutzen-Tests: 5.000 gepaarte zirkuläre Block-Bootstrap-Wiederholungen über ganze Kalenderwochen in Achtwochenblöcken; alle Firmen einer Woche bleiben zusammen. Sensitivitäten mit vier und 13 Wochen ändern das qualitative Ergebnis nicht. Die drei primären Vergleiche wurden mit Holm korrigiert. Bei konservativer gemeinsamer Korrektur über alle fünf Vergleiche bleibt der zusätzliche gemeinsame Nachrichten-/Verfügbarkeitsvergleich unter p=0,0011. Bootstrap und Korrektur beheben weder schlechte Messung noch alle möglichen langfristigen Abhängigkeiten.')
fig('prognosevergleich.png','Zusatznutzen des Nachrichtenmodells gegenüber vorab und zusätzlich gewählten Baselines mit Block-Konfidenzintervallen')
table(['Kurs-/Aktivitätsaufgabe','AUC Vergleich','AUC Nachrichtenmodell'],[(label,f(res[t]['test']['price_only']['auc'],4),f(res[t]['test']['news_price']['auc'],4)) for t,label in [('return','Relative Kursrichtung'),('volume','Handelsaktivität')]])
para('AUC 0,5 entspricht keiner besseren Rangordnung als Zufall. Die Kurs-AUC des kombinierten Modells liegt bei 0,4998. Der Aktivitätswert steigt von 0,6208 auf 0,6230; das 95%-Intervall der Brier-Verbesserung schließt Null ein. Das ist kein gesicherter zusätzlicher Nachrichten-Effekt. Auch die Untergruppe mit ausreichenden aktuellen Nachrichten und die URL-Fokus-Untergruppe liefern keinen besseren Brier-Fehler als das Kursmodell. Lokale statt USD-Renditen ändern das negative Kursfazit nicht.')
heading('Welche Reaktionen waren in den Kategorien häufiger?')
rows=[]
for s in range(6):
 r=rates[(rates.target=='return')&(rates.state==s)].iloc[0];v=rates[(rates.target=='volume')&(rates.state==s)].iloc[0]
 rows.append((NAMES[s],int(r.n),pct(r.event_rate)+' ['+pct(r.ci_low)+'; '+pct(r.ci_high)+']',pct(v.event_rate)+' ['+pct(v.ci_low)+'; '+pct(v.ci_high)+']'))
table(['Aktuelle Kategorie','Kursfälle','Übertrifft Korb, 95%-Intervall','Volumen erhöht, 95%-Intervall'],rows)
para('Diese Häufigkeiten sind deskriptiv und hängen auch von Firmen, Regionen, Marktphasen und Stichprobenabdeckung ab. Sie zeigen keine durch die Kategorie verursachte Handlung. Jeder abgeschlossene Handel hat Käufer und Verkäufer; mit Tageskursen und Gesamtvolumen lassen sich „die Anleger kaufen/verkaufen“ oder deren Motive nicht direkt identifizieren. Aggressor-seitiger Orderfluss, Depotumschichtungen und Fondsflüsse wurden nicht beobachtet. Ein Kursanstieg ist eine Marktreaktion, kein Nachweis einer bestimmten Emotion.')
fig('reaktionen_nach_kategorie.png','Historische relative Kurs- und Volumenreaktionen pro Kategorie; deskriptive Intervalle')
heading('Konzept für eine belastbarere weltweite Fassung')
para('Sinnvoll ist ein mehrstufiges Wahrscheinlichkeitsmodell: firmenspezifische Textaussagen und deren Neuigkeit → latenter Zustand aus Ton, Aufmerksamkeit, Widersprüchlichkeit und Überraschung → Verteilung der nächsten Zustände → beobachtbare Marktreaktionen, bedingt auf Bewertung, Erwartungen, Liquidität und Marktregime. Entscheidend ist die Abweichung von dem, was bereits erwartet und eingepreist war. Die hier implementierten Cluster und regulierten Prognoseköpfe sind eine einfache überprüfbare Ausgangsversion dieses Konzepts.')
para('Für die nächste Datenstufe fehlen ein vollständiger historischer Nachrichtenstrom mit damaliger Erstverfügbarkeit, verlässliche Entitätsverknüpfungen, finanzspezifische und sprachlich validierte Sentimentwerte, zeitgestempelte Konsenserwartungen sowie tatsächliche Order-/Kapitalflussdaten. Auch delistete Firmen, kleinere Aktien, historische Aktiengattungen und regionale Anlegergruppen müssten im Point-in-time-Universum enthalten sein. Danach wären ein vorab festgelegter geografischer Test und ein neuer prospektiver Zeitabschnitt nötig. Solche Daten wurden hier nicht durch synthetische Beobachtungen ersetzt.')
para('Als konkretes Ausgabeformat erhält eine Aktie: aktuelle Kategorie oder „zu wenig Daten“, Datenabdeckung, Wahrscheinlichkeiten der sechs nächsten Kategorien plus fehlender Messbarkeit, Wahrscheinlichkeit relativer Kursstärke und erhöhten Handelsvolumens sowie eine knappe Erklärung der wichtigsten beobachteten Merkmale. Farben dienen der Darstellung des Tons bzw. der Unsicherheit; sie begründen in diesem Versuch keine Kaufempfehlung. Die App wurde nicht verändert.')
heading('Literatur und Grenzen der Schlussfolgerung')
para('Fraiberger, Lee, Puy und Ranciere untersuchen in „Media Sentiment and International Asset Prices“ (IMF WP/18/274; publizierte Fassung 2021) mehrjährige Reuters-Nachrichten und internationale Aktien-/Kapitalflussdaten. Ihre Ergebnisse motivieren insbesondere die Trennung lokaler und globaler Stimmung und verschiedener Zeithorizonte. Eine solche Studie kann die Hypothese stützen; sie validiert weder unsere gemessenen Kategorien noch die Wirtschaftlichkeit dieses Modells. Unser Wochen-Sampling und der mehrtägige Puffer sind wesentlich gröber.')
para('Die Daten wurden 2026 rückblickend geladen. Archivdatum und konservative Zeitgrenzen reduzieren Look-ahead-Risiken, belegen aber keine lückenlose unveränderte Originalversion jeder Quelldatei. Yahoo-Kurse sind aktuell adjustierte Forschungsdaten mit möglichen Revisionen, Abspaltungs- und Delisting-Problemen. Die historische Liste vermeidet die Auswahl nur heutiger Gewinner, bleibt jedoch eine vorselektierte große und liquide Unternehmenskohorte. Eine vollständig biasfreie Validierung ist damit nicht möglich. Es wurde kein Portfolio nach Transaktionskosten, Geld-/Briefkursen, Steuern oder Markteinfluss getestet; aus diesen Prognosemaßen folgt keine Netto-Überrendite.')
para('Zwölf automatisierte Integritätsprüfungen bestanden, darunter zeitliche Reihenfolge, eindeutige Firmenwochen, frische Zustandsziele, Wahrscheinlichkeitsnormierung und unveränderte Protokoll-/Modellquellen seit dem letzten Lock vor dem ersten Zieltest. Zwei Wochenrenditen über 50 % wurden als Ausreißer dokumentiert und nicht nachträglich entfernt. Diese Prüfungen kontrollieren die Implementierung, nicht die Wahrheit einer psychologischen Interpretation.')
heading('Quellen und Reproduktion')
para('Das Paket enthält die verwendeten kompakten Nachrichtenmetadaten, Kurs-/Devisen-Snapshots, archivierte Modellvorhersagen, Modelle, Protokoll, Prüfergebnisse und Python-Skripte. Aufrufe und Paketversionen stehen in README.md. sources.md dokumentiert die Herkunft; archive_manifest.json und prices_manifest.json dokumentieren Abdeckung und Hashes. Die primäre Konfiguration ist zeitlich vor dem ersten Modelltest protokolliert; die zusätzlichen Diagnosen sind ausdrücklich nachträglich gekennzeichnet.')
sources=[('PwC, Global Top 100, März 2018','https://preview.thenewsmarket.com/Previews/PWC/DocumentAssets/514404.pdf'),('GDELT GKG 2.1 Codebook','https://data.gdeltproject.org/documentation/GDELT-Global_Knowledge_Graph_Codebook-V2.1.pdf'),('GDELT 2.0 und mehrsprachige Archive','https://blog.gdeltproject.org/gdelt-2-0-our-global-world-in-realtime/'),('Fraiberger et al., IMF WP/18/274','https://www.imf.org/en/publications/wp/issues/2018/12/10/media-sentiment-and-international-asset-prices-46454'),('Roche, ROG/ROP-Austausch','https://www.roche.com/investors/updates/inv-update-2026-03-16')]
for label,url in sources:md.append(f'- [{label}]({url})');ht.append('<p><a href="'+html.escape(url)+'">'+html.escape(label)+'</a></p>')
(O/'bericht.md').write_text('\n\n'.join(md))
css='''body{font:16px/1.65 Arial,sans-serif;color:#202d3b;background:#f1f4f7;margin:0}main{max-width:1080px;margin:36px auto;background:white;padding:44px 52px;border-radius:14px;box-shadow:0 6px 28px #172b4d12}h1{font-size:36px;line-height:1.16;letter-spacing:-.7px;color:#123e58}h2{font-size:23px;line-height:1.3;margin-top:40px;color:#123e58;border-top:1px solid #dce4ec;padding-top:23px}p{max-width:1000px;margin:16px 0}table{border-collapse:collapse;font-size:14px;line-height:1.45;width:100%}th{text-align:left;background:#e8f0f5;padding:11px}td{border-bottom:1px solid #e1e7ed;padding:10px;vertical-align:top}tr:nth-child(even){background:#f8fafc}.tablewrap{overflow:auto;margin:22px 0}figure{margin:28px 0}img{max-width:100%;height:auto}a{color:#126780} @media(max-width:700px){main{margin:0;padding:24px 18px;border-radius:0}h1{font-size:29px}} @media print{body{background:white}main{padding:0;margin:0;box-shadow:none}h2{break-after:avoid}table,figure{break-inside:avoid}}'''
(O/'bericht.html').write_text('<!doctype html><html lang="de"><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>Stimmungsmodell – Pilotprüfung</title><style>'+css+'</style><main>'+''.join(ht)+'</main></html>')
# Actual historical examples; no live recommendation.
jp=pd.read_parquet(O/'joint_state_predictions.parquet');sample=jp[jp.company_id.isin([1,2,3,14,62])].sort_values('date').groupby('company_id').tail(1);sample['company']=sample.company_id.map(dict(zip(co['rank'],co.company)));sample.to_csv(O/'historische_beispiele.csv',index=False)
versions={p:importlib.metadata.version(p) for p in ['numpy','pandas','scipy','scikit-learn','pyarrow','matplotlib','joblib']};(R/'requirements.txt').write_text('\n'.join(f'{k}=={v}' for k,v in versions.items())+'\n')
(R/'README.md').write_text('''# Internationales Stimmungsmodell – Pilotversuch

Bericht zuerst öffnen: `output/bericht.html` (selbständig, offline), alternativ `output/bericht.md`.

Die App wurde nicht verändert. Dies ist Forschung mit historischen Daten, kein einsatzbereites Handelssystem.

## Reproduktion ohne erneuten Download

Python 3.12, Versionsstände in requirements.txt. Nach Installation der Pakete im Verzeichnis dieses Projekts:

```bash
python model.py
python verify.py
python robustness.py
python joint_forecast.py
python report.py
```

model.py passt die sechs Kategorien und die primären Modelle nur auf 2019–2021 an. 2022 dient der Diagnose; 2023–2025 ist der Test. Die beiden letzten Modellscripte sind zusätzliche Diagnosen, die erst nach Sichtung der primären Resultate hinzugefügt wurden. Das primäre Kandidatenmodell wurde danach nicht optimiert. Das Verfügbarkeitsmodell in joint_forecast.py berücksichtigt auch ausbleibende Messbarkeit in der Folgewoche.

`data/news_sample.parquet` enthält die verwendete Metadaten-Stichprobe. `data/prices/*.json` sind die Kurs-/FX-Snapshots; `data/price_panel.parquet` und `data/news_features.parquet` sind daraus erzeugte Zwischenwerte. `output/test_predictions.parquet` und `output/joint_state_predictions.parquet` erlauben unabhängige Auswertungen der fixierten Vorhersagen. Die gespeichert geladenen Modelle (joblib) nur aus vertrauenswürdiger Quelle öffnen.

## Optionaler frischer Quellenabruf

```bash
python prices.py
python collect.py
```

collect.py lädt ungefähr 7,7 GB öffentliche komprimierte Archivdaten und behält nur die Firmen-Metadaten (keine Volltexte). Roharchive sind wegen Größe nicht enthalten. Für einen vollständigen Neuabruf ein neues Projektverzeichnis mit den Skripten und leerem data-Verzeichnis verwenden; mitgelieferte Originaldaten zuvor behalten. Yahoo-Daten und historische Unternehmens- bzw. Devisenzuordnungen können sich ändern; neu geladene Ergebnisse müssen nicht exakt der Aufnahme vom 01.11.2026 entsprechen.

Der Datensatz ist eine feste 15-Minuten-Stichprobe pro Woche, kein vollständiger Nachrichtenstrom. Unzureichende Nachrichten erhalten Zustand -1, keine neutrale Stimmung. Die bedingte Stimmungsvorhersage erfordert in beiden Wochen genügend Messungen; die gemeinsame Zusatzdiagnose behandelt fehlende Folgemessungen explizit.

Protokoll und zwei zeitliche Lock-Dateien dokumentieren die Konfiguration vor dem ersten Zieltest. Die zweite Lock-Version korrigiert fehlende Spracharchive und südafrikanische Centkurse. Sie erfolgte vor Einsicht in Modelltestkennzahlen. Alle primären Quellhashes werden von verify.py geprüft.

Keine Handelskosten oder Portfoliorenditen wurden getestet. Datenabdeckung, Bias-Risiken, regionale Grenzen und Quellen stehen im Bericht und in sources.md.
''')
(O/'environment.json').write_text(json.dumps({'python':platform.python_version(),'packages':versions},indent=2))
print('Wrote report HTML/MD, 2 figures, examples, requirements and README.')
