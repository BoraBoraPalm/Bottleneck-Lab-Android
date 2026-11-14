(function(root){
  "use strict";
  const STUDY_URL="https://github.com/BoraBoraPalm/Bottleneck-Lab-Android/blob/9fbd2c0105816f3d86a807cd22d4a55c6c3d23a3/research/tests/2026-11-02-holding-duration/files/output/bericht.md";
  const STORAGE_KEY="bottleneck.time-plan.v1";
  const HORIZONS=Object.freeze({
    all:{label:"Offen / alle Horizonte",proposal:null},
    short:{label:"1–4 Wochen",proposal:null},
    quarter:{label:"Etwa 3 Monate",proposal:"trend"},
    half:{label:"Etwa 6 Monate",proposal:"trend"},
    year:{label:"Etwa 12 Monate",proposal:"momentum"},
    longer:{label:"Länger als 1 Jahr",proposal:null}
  });
  const PROFILES=Object.freeze({
    momentum:{name:"12–2-Monats-Momentum",kind:"holding",preferred:["year"],
      short:"Prüftakt: meist ca. 12 Monate",
      detail:"In der jährlichen Auswahl aus früheren Daten: 252 Handelssitzungen in 6 von 7 Jahren, einmal 120. Median der abgeschlossenen Trades: 252 Sitzungen, ungefähr ein Jahr. Das 12–2-Signal beschreibt den Kursrückblick, nicht die Haltedauer. Der Zusatznutzen dieser Dauerwahl ist statistisch nicht gesichert (p nach Holm 0,30).",
      study:"Kursregel, 2019–2025; Umschichtung zum gewählten Termin, kein individueller optimaler Verkaufstag. 19,8 % pro Jahr gegenüber 17,5 % beim bloßen gleichgewichteten Halten derselben Aktien; der Abstand zum Weltindex kommt großteils von der Aktienauswahl. Die Studie nutzte noch die frühere Momentum-Variante ohne die letzten zwei Monate; die Wahl für 2019 beruht vermutlich teils auf einem auffälligen Kurswert 2014–2018. Nachprüfung vom 14.11.2026 an S&P-500-Aktien 2011–2026: Die jährliche Auswahl lag vor der monatlichen, beides ohne statistische Sicherheit."},
    lowRisk:{name:"Geringe Kursschwankung",kind:"holding",preferred:["year"],belowBenchmark:true,
      short:"Prüftakt: meist ca. 12 Monate · gehalten: Median ca. 6 Monate · bei jeder Dauer unter dem Weltindex",
      detail:"In der jährlichen Auswahl aus früheren Daten: 252 Sitzungen in 5 von 7 Jahren. Median abgeschlossener Trades: 120 Sitzungen, ungefähr sechs Monate. Prüfintervall und tatsächliche Haltung sind verschiedene Angaben. Die 252 Tage im Volatilitätsmerkmal sind dessen Rückblick.",
      study:"Kursregel, 2019–2025; auch mit angepasstem Intervall unter der ACWI-Benchmark. Die Prüfung vom 14.11.2026 bestätigt das über Jahrzehnte: geringere Einbrüche, kein Mehrertrag."},
    trend:{name:"200-Tage-Trend",kind:"holding",preferred:["quarter","half"],
      short:"Prüftakt: ca. 3–6 Monate, meist 6 Monate",
      detail:"In der jährlichen Auswahl aus früheren Daten: 120 Handelssitzungen in 5 von 7 Jahren, zweimal 60. Median der abgeschlossenen Trades: 120 Sitzungen, ungefähr sechs Monate. Die 200 Tage des Trends sind dessen Berechnungsrückblick.",
      study:"Kursregel, 2019–2025; die Dauerwahl verbesserte diese Regel gegenüber dem festen 20-Sitzungen-Takt statistisch gesichert (p nach Holm 0,006), kein Nachweis künftiger Marktüberlegenheit. 21,6 % pro Jahr gegenüber 17,5 % beim bloßen gleichgewichteten Halten derselben Aktien."},
    sander:{name:"Hoch-Tief-Mut",kind:"unknown",preferred:[],short:"Haltedauer offen",
      detail:"Für unsere Sander-inspirierte Fundamental-Vorauswahl ist keine optimale Haltedauer ermittelt. Ein längerfristiger Ansatz allein bestimmt keinen geprüften Verkaufszeitpunkt.",study:"Exakte historische Fundamental- und Bewertungsdaten fehlen für den vollständigen App-Filter."},
    growth:{name:"Frühwachstum / Multibagger",kind:"unknown",preferred:[],short:"Haltedauer offen",
      detail:"Für den konkreten Frühwachstumsfilter wurde keine optimale Haltedauer nachgewiesen. Quartalswachstum und Kursbestätigung liefern keine feste Zeit bis zu einer Kursvervielfachung.",study:"Der vollständige historische App-Filter ist nicht mit damaligen Fundamental-Vintages validiert."},
    quality:{name:"Profitabilität / Quality",kind:"refresh",preferred:[],short:"Haltedauer offen · Quellenportfolio meist jährlich aktualisiert",
      detail:"Beim Gross-Profit-Literaturportfolio wurde die jährliche Aktualisierung in 9 von 12 Jahren gewählt. Das betrifft die Portfoliozuordnung; die Haltedauer einer einzelnen Aktie ist daraus nicht bekannt.",study:"Literaturportfolio, 2014–2025; kein belastbarer zusätzlicher Nutzen der Intervallwahl."},
    value:{name:"Value / Bewertung",kind:"refresh",preferred:[],short:"Haltedauer offen · Quellenportfolio oft halbjährlich aktualisiert",
      detail:"Beim Value-Literaturportfolio wurde eine Aktualisierung alle sechs Monate in 6 von 12 Jahren gewählt. Keine daraus abgeleitete Verkaufsfrist für eine einzelne günstige Aktie.",study:"Literaturportfolio, 2014–2025; keine eindeutig stabile optimale Aktualisierung."},
    earnings:{name:"Gewinnmomentum / Quartalsmodell",kind:"unknown",preferred:[],short:"Haltedauer für dieses Quartalsmodell offen",
      detail:"Das App-Modell verwendet Gesamtgewinne und ein eigenes saisonales Muster. Der Haltedauertest eines Literatur-Signals zu Gewinnüberraschungen ist kein identischer Test dieses Modells.",study:"Keine ungeprüfte Übertragung der Sechsmonats-Aktualisierung eines anderen Gewinnsignals."},
    investment:{name:"Konservatives Bilanzwachstum",kind:"refresh",preferred:[],short:"Haltedauer offen · Quellenportfolio meist monatlich aktualisiert",
      detail:"Beim Literaturfaktor wurde monatliche Aktualisierung in 10 von 12 Jahren gewählt. Das erzwingt keinen Verkauf jeder Aktie nach einem Monat und war kein Renditenachweis.",study:"Literaturportfolio, 2014–2025; individuelle Aktien-Haltedauern nicht beobachtbar."}
  });
  const own=(obj,key)=>typeof key==="string"&&Object.prototype.hasOwnProperty.call(obj,key);
  const normalize=value=>own(HORIZONS,value)?value:"all";
  const keys=chosen=>Array.isArray(chosen)?[...new Set(chosen.filter(key=>own(PROFILES,key)))]:[];
  function describe(key,horizon="all"){
    const p=own(PROFILES,key)?PROFILES[key]:null;
    if(!p)return {key,state:"open",label:"Haltedauer offen",short:"Haltedauer offen",detail:"Kein dokumentierter Test für diese Strategie.",study:""};
    // A rule that stayed below its benchmark at every tested duration only gets
    // an informational hint, never a "matching horizon" signal.
    const h=normalize(horizon),state=p.kind!=="holding"?"open":h==="all"||p.belowBenchmark?"info":p.preferred.includes(h)?"match":"other";
    const label={open:"Dauer offen",info:"Historischer Testhinweis",match:"Horizont im Testbereich",other:"Anderer oder ungeprüfter Horizont"}[state];
    return {...p,key,state,label};
  }
  function plan(horizon){
    const h=normalize(horizon),p=HORIZONS[h].proposal;
    if(h==="all")return {horizon:h,proposal:null,text:"Wähle deinen Anlagehorizont. Danach kannst du einen passenden Strategievorschlag übernehmen oder deine Häkchen selbst setzen."};
    if(p)return {horizon:h,proposal:p,text:h==="year"
      ?"Für etwa zwölf Monate liefert der Momentum-Kurstest einen Zeitansatz; der Vorteil dieser Dauerwahl ist aber statistisch nicht gesichert. Geringe Kursschwankung hatte zwar meist einen jährlichen Prüftakt, blieb aber bei jeder Dauer unter dem Weltindex. Der Vorschlag wählt Momentum allein."
      :"Für etwa drei bis sechs Monate liefert der Trend-Kurstest einen Zeitansatz; hier ist der Vorteil der Dauerwahl statistisch gesichert. Der Vorschlag wählt den 200-Tage-Trend allein."};
    return {horizon:h,proposal:null,text:h==="short"
      ?"Für eine Haltung von 1–4 Wochen gibt es keinen belastbaren Zeitvorschlag für die aktuellen App-Strategien. Getestete Limit-/Stopp-Varianten waren andere Handelsregeln. Du kannst Strategien weiterhin selbst wählen."
      :"Über ein Jahr hinaus wurde keine feste optimale Haltedauer für die App-Strategien bestimmt. Weiterhalten kann sinnvoll zu prüfen sein; die Zeitspanne allein ist kein Nachweis. Du kannst Strategien selbst wählen."};
  }
  function summary(chosen,horizon="all"){
    const selected=keys(chosen);
    if(!selected.length)return {state:"open",title:"Keine Strategie ausgewählt",text:"Wähle eine Strategie für einen Zeithinweis."};
    if(selected.length>1)return {state:"open",title:"Mix: keine geprüfte Haltedauer",text:selected.length+" Strategien ausgewählt. Ihre Zeithinweise werden nicht zu einer festen Haltefrist gemittelt; sie stehen getrennt bei den Strategien."};
    const p=describe(selected[0],horizon);
    return {state:p.state,title:p.name+" · "+p.label,text:p.short+". "+(p.kind==="holding"?"Orientierung aus dem historischen Kurstest, keine feste Verkaufsfrist.":p.detail)};
  }
  function readSettings(storage){
    try{
      const raw=JSON.parse(storage.getItem(STORAGE_KEY));
      if(!raw||raw.version!==1)return null;
      const candidates=keys(raw.candidates);
      return {horizon:normalize(raw.horizon),candidates:candidates.length?candidates:["momentum"],search:Array.isArray(raw.search)?keys(raw.search):Object.keys(PROFILES)};
    }catch{return null;}
  }
  function writeSettings(storage,value){
    try{storage.setItem(STORAGE_KEY,JSON.stringify({version:1,horizon:normalize(value.horizon),candidates:keys(value.candidates),search:keys(value.search)}));return true;}catch{return false;}
  }
  function decorate(container,horizon){
    for(const input of container.querySelectorAll("input[data-factor],input[data-fit]")){
      const key=input.dataset.factor||input.dataset.fit,p=describe(key,horizon),label=input.closest("label");
      let note=label.querySelector(".holding-chip");
      if(!note){note=document.createElement("span");label.querySelector("span").appendChild(note);}
      note.className="holding-chip horizon-"+p.state;note.textContent=p.short;
      note.title=p.detail+" "+p.study;note.setAttribute("aria-label",p.short+". "+p.label);
    }
  }
  function renderCard(parent,chosen,horizon){
    const s=summary(chosen,horizon),panel=document.createElement("div");panel.className="holding-note horizon-"+s.state;
    const title=document.createElement("strong");title.textContent="Strategie-Zeitplan · "+s.title;
    const text=document.createElement("span");text.textContent=s.text;panel.append(title,text);parent.appendChild(panel);
  }
  const api={horizons:HORIZONS,profiles:PROFILES,studyUrl:STUDY_URL,normalize,keys,describe,plan,summary,readSettings,writeSettings,decorate,renderCard};
  if(typeof module!=="undefined"&&module.exports)module.exports=api;
  root.StockHorizon=api;
})(typeof window!=="undefined"?window:globalThis);
