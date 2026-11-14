/* What the archived strategy audit of 2026-11-14 found for each app strategy.
   All figures come from evidence-data.js (generated from the archived result files). */
(function(root){
  "use strict";
  const DATA=root.StockEvidenceData||(typeof require!=="undefined"?require("./evidence-data.js"):null);
  const STUDY_URL="https://github.com/BoraBoraPalm/Bottleneck-Lab-Android/tree/master/research/tests/2026-11-14-strategy-audit";
  const TIERS=Object.freeze({
    hint:{label:"Hinweise, nicht gesichert",chip:"Daten: Hinweise, nicht gesichert"},
    none:{label:"Kein Mehrertrag belegt",chip:"Daten: kein Mehrertrag belegt"},
    against:{label:"Gegenwind in den Daten",chip:"Daten: Gegenwind beim Kursteil"},
    open:{label:"Nicht prüfbar",chip:"Daten: nicht prüfbar"}
  });
  const pp=v=>typeof v!=="number"||!Number.isFinite(v)?"–":(v>0?"+":v<0?"−":"±")+
    Math.abs(v).toLocaleString("de-AT",{minimumFractionDigits:1,maximumFractionDigits:1});
  const abs=v=>Math.abs(v).toLocaleString("de-AT",{minimumFractionDigits:1,maximumFractionDigits:1});
  const fall=v=>"−"+Math.abs(v)+" %";
  const span=r=>r.from+"–"+r.to;
  const open="(nicht gesichert)";
  const STRATEGIES=Object.freeze({
    momentum:{tier:"hint",title:"12–2-Monats-Momentum",
      verdict:"Langfristig der stärkste Kursfaktor. Seit 2000 bei US-Aktien kaum noch Vorsprung; an S&P-500-Aktien half zuletzt nur die jährliche Auswahl.",
      facts:d=>["US-Aktien, oberstes Zehntel, "+span(d.rows.MOM_D10)+": "+pp(d.rows.MOM_D10.net)+"; seit 2000: "+pp(d.rows.MOM_D10.hold)+" "+open+".",
        "Große US-Werte seit 2000: "+pp(d.rows.MOM_BIG.hold)+".",
        "30 US-Branchen, je 6 gehalten, "+span(d.rows.IND_MOM122)+": "+pp(d.rows.IND_MOM122.net)+"; seit 2000: "+pp(d.rows.IND_MOM122.hold)+" "+open+".",
        "S&P-500-Aktien "+span(d.stocks.S_MOM)+": "+pp(d.stocks.S_MOM.net)+" bei monatlicher, "+pp(d.stocks.S_MOM_12M.net)+" bei jährlicher Auswahl (beides nicht gesichert).",
        "Echte Momentum-ETFs seit Auflage: "+d.etf.Momentum.ahead+" von "+d.etf.Momentum.n+" vor ihrem Index, Median "+pp(d.etf.Momentum.median)+"."]},
    trend:{tier:"hint",title:"200-Tage-Trend",
      verdict:"Verhält sich wie Momentum: historisch deutlich, zuletzt schwach.",
      facts:d=>["Branchen mit dem größten Abstand über der 200-Tage-Linie, "+span(d.rows.IND_TREND)+": "+pp(d.rows.IND_TREND.net)+"; seit 2000: "+pp(d.rows.IND_TREND.hold)+" "+open+".",
        "Veröffentlichter Trendfaktor für US-Aktien, "+span(d.rows.OSAP_TrendFactor)+": "+pp(d.rows.OSAP_TrendFactor.net)+"; seit der Veröffentlichung (ab "+d.rows.OSAP_TrendFactor.holdFrom+"): "+pp(d.rows.OSAP_TrendFactor.hold)+".",
        "S&P-500-Aktien "+span(d.stocks.S_TREND)+", oberstes Zehntel: "+pp(d.stocks.S_TREND.net)+" "+open+"."]},
    lowRisk:{tier:"none",title:"Geringe Kursschwankung",chip:"Daten: kein Mehrertrag, weniger Schwankung",
      verdict:"Senkt die Schwankung, bringt aber keinen Mehrertrag.",
      facts:d=>["Ruhigstes Fünftel der US-Aktien, "+span(d.rows.LOWVOL_Q1)+": "+pp(d.rows.LOWVOL_Q1.net)+"; größter Einbruch "+fall(d.rows.LOWVOL_Q1.maxdd)+" statt "+fall(d.rows.LOWVOL_Q1.marketMaxdd)+".",
        "S&P-500-Aktien "+span(d.stocks.S_LOWVOL)+", ruhigstes Zehntel: "+pp(d.stocks.S_LOWVOL.net)+".",
        "Echte Produkte seit Auflage: "+d.etf["Geringe Schwankung"].ahead+" von "+d.etf["Geringe Schwankung"].n+" vor ihrem Index, Median "+pp(d.etf["Geringe Schwankung"].median)+"."]},
    quality:{tier:"hint",title:"Profitabilität / Quality",
      verdict:"Kleiner, recht beständiger Vorsprung in den USA. Außerhalb uneinheitlich; echte Quality-ETFs lagen gleichauf mit ihrem Index.",
      facts:d=>["Bruttogewinn/Bilanzsumme, oberstes Fünftel der US-Aktien, "+span(d.rows.OSAP_GP)+": "+pp(d.rows.OSAP_GP.net)+"; seit der Veröffentlichung (ab "+d.rows.OSAP_GP.holdFrom+"): "+pp(d.rows.OSAP_GP.hold)+" "+open+"; in "+d.rows.OSAP_GP.win10+" % der 10-Jahres-Fenster vorn.",
        "Große Werte außerhalb der USA seit Anfang der 1990er-Jahre: Europa "+pp(d.rows.Europe_QUAL.net)+", Japan "+pp(d.rows.Japan_QUAL.net)+", Schwellenländer "+pp(d.rows.Emerging_QUAL.net)+".",
        "Echte Quality-ETFs seit Auflage: "+d.etf.Quality.ahead+" von "+d.etf.Quality.n+" vor ihrem Index, Median "+pp(d.etf.Quality.median)+"."]},
    value:{tier:"none",title:"Value · günstige Bewertung",
      verdict:"Historisch ein Vorsprung. Seit 2000 nicht mehr gesichert; echte Value-Produkte lagen fast alle hinter ihrem Index.",
      facts:d=>["Günstigstes Fünftel nach Buchwert, US-Aktien, "+span(d.rows.VAL_Q5)+": "+pp(d.rows.VAL_Q5.net)+"; seit 2000: "+pp(d.rows.VAL_Q5.hold)+" "+open+".",
        "Große US-Werte: "+pp(d.rows.VAL_BIG.net)+"; seit 2000: "+pp(d.rows.VAL_BIG.hold)+" "+open+".",
        "Echte Value-Produkte seit Auflage: "+d.etf.Value.ahead+" von "+d.etf.Value.n+" vor ihrem Index, Median "+pp(d.etf.Value.median)+"."]},
    investment:{tier:"none",title:"Konservatives Bilanzwachstum",
      verdict:"Historisch ein kleiner Vorsprung, in den letzten 15 Jahren keiner.",
      facts:d=>["Geringstes Bilanzwachstum, unterstes Fünftel der US-Aktien, "+span(d.rows.INV_Q1)+": "+pp(d.rows.INV_Q1.net)+"; seit 2000: "+pp(d.rows.INV_Q1.hold)+" "+open+"; letzte 15 Jahre: "+pp(d.rows.INV_Q1.recent)+".",
        "Das veröffentlichte Signal seit seiner Veröffentlichung (ab "+d.rows.OSAP_AssetGrowth.holdFrom+"): "+pp(d.rows.OSAP_AssetGrowth.hold)+"."]},
    earnings:{tier:"none",title:"Gewinnmomentum · Quartalsmodell",
      verdict:"Gewinnüberraschungen brachten vor Kosten etwas, nach Kosten nichts. Das Quartalsmodell der App selbst ist nicht geprüft.",
      facts:d=>["Gewinnüberraschungen, oberstes Fünftel der US-Aktien, "+span(d.rows.OSAP_EarningsSurprise)+": "+pp(d.rows.OSAP_EarningsSurprise.gross)+" vor Kosten, "+pp(d.rows.OSAP_EarningsSurprise.net)+" nach Kosten; seit 2000: "+pp(d.rows.OSAP_EarningsSurprise.hold)+"."]},
    growth:{tier:"open",title:"Frühwachstum / Multibagger",
      verdict:"Die Regel der App lässt sich mit historischen Daten nicht nachbilden. Verwandte Signale zeigen keinen Vorteil; hohes Umsatzwachstum allein lag zurück.",
      facts:d=>["Umsatzüberraschung, US-Aktien, "+span(d.rows.OSAP_RevenueSurprise)+": "+pp(d.rows.OSAP_RevenueSurprise.net)+".",
        "Serien steigender Gewinne, "+span(d.rows.OSAP_EarningsStreak)+": "+pp(d.rows.OSAP_EarningsStreak.net)+"; seit der Veröffentlichung (ab "+d.rows.OSAP_EarningsStreak.holdFrom+"): "+pp(d.rows.OSAP_EarningsStreak.hold)+".",
        "Höchstes Umsatzwachstum über fünf Jahre, "+span(d.rows.OSAP_MeanRankRevGrowth_GEGENSEITE)+": "+pp(d.rows.OSAP_MeanRankRevGrowth_GEGENSEITE.net)+"."]},
    sander:{tier:"against",title:"Hoch-Tief-Mut · Sander-inspiriert",
      verdict:"Gefallene Aktien blieben im Mittel weiter zurück. Der Qualitätsfilter der App ließ sich nicht mitprüfen; die Gesamtregel ist deshalb ungeprüft.",
      facts:d=>["S&P-500-Aktien 15–55 % unter ihrem 252-Tage-Hoch, "+span(d.stocks.S_DIP)+": "+pp(d.stocks.S_DIP.net)+" gegenüber allen Mitgliedern; in "+d.stocks.S_DIP.win5+" % der 5-Jahres-Fenster vorn.",
        "US-Branchen 15–55 % unter ihrem Hoch, "+span(d.rows.IND_DIP)+": "+pp(d.rows.IND_DIP.net)+".",
        "Am weitesten gefallenes Fünftel aller US-Aktien, "+span(d.rows.OSAP_High52_GEGENSEITE)+": "+pp(d.rows.OSAP_High52_GEGENSEITE.net)+".",
        "Kurse nicht mehr notierter Aktien fehlen im S&P-500-Test. Das begünstigt diese Regel sogar.",
        "Folge in der App: Der Score belohnt tiefere Rückgänge seit 14.11.2026 nicht mehr."]}
  });
  const ENTRY_EXIT=Object.freeze({title:"Einstieg/Ausstieg prüfen",
    verdict:"Schützt vor tiefen Einbrüchen und kostet Rendite.",
    facts:d=>["Regel der App auf den US-Markt angewendet, "+span(d.rows.T_APP)+": "+pp(d.rows.T_APP.net)+"; letzte 15 Jahre: "+pp(d.rows.T_APP.recent)+"; größter Einbruch "+fall(d.rows.T_APP.maxdd)+" statt "+fall(d.rows.T_APP.marketMaxdd)+".",
      "Nach österreichischer KESt (Modell über 20 Jahre): "+pp(d.rows.T_APP.tax)+".",
      "Einfache 200-Tage-Regel: "+pp(d.rows.T_SMA200.net)+"; größter Einbruch "+fall(d.rows.T_SMA200.maxdd)+"."]});
  function findings(d=DATA){
    const picks=[d.rows.PICK_10J_TOP10.recent,d.rows.PICK_15J_TOP10.recent,d.rows.PICK_20J_TOP10.recent];
    return [d.study.strategies+" Strategien nach einem vorab festgelegten Protokoll geprüft. In den USA erfüllt keine die Kriterien für „verlässlich besser als der Markt“.",
      d.osap.signals+" veröffentlichte Signale: im Mittel "+pp(d.osap.inSample)+" in der Stichprobe der Originalarbeit, "+pp(d.osap.afterPublication)+" nach der Veröffentlichung.",
      "Jedes Jahr die zehn bisher besten Signale auswählen: in den letzten 15 Jahren "+pp(Math.max(...picks))+" bis "+pp(Math.min(...picks))+".",
      "Österreichische KESt: Wer sein Depot einmal pro Jahr mit Gewinn umschichtet, verliert gegenüber Kaufen und Halten rund "+abs(d.tax.turnover100)+" Prozentpunkte pro Jahr (Modell über 20 Jahre); bei 30 % Umschlag rund "+abs(d.tax.turnover30)+".",
      "Einzige Ausnahme auf dem Papier: Quality + Value + Momentum in Schwellenländern mit "+pp(d.emerging.gross)+" vor Kosten, bei 2 % Kosten "+pp(d.emerging.at2)+". Der älteste echte Value-Fonds dort (seit "+d.emerging.valueFund.from+"): "+pp(d.emerging.valueFund.net)+" gegenüber dem Indexfonds. Ein Hinweis, kein Beweis."];
  }
  function notAdded(d=DATA){
    return ["Momentum je Schwankung: Branchen "+pp(d.rows.IND_RAM.net)+", an S&P-500-Aktien aber "+pp(d.stocks.S_RAM.net)+".",
      "Branchen-Momentum: zwölf grobe Branchen "+pp(d.sectors12.IND12_MOM122.net)+" (vierteljährlich "+pp(d.sectors12.IND12_MOM122_3M.net)+"), als Aktienfaktor an S&P-500-Aktien aber "+pp(d.stocks.S_SECTOR3.net)+".",
      "Nähe zum 52-Wochen-Hoch: an S&P-500-Aktien "+pp(d.stocks.S_HIGH52.net)+".",
      "Mix Quality + Value + Momentum (USA), "+span(d.rows.MIX_QVM)+": "+pp(d.rows.MIX_QVM.net)+"; seit 2000: "+pp(d.rows.MIX_QVM.hold)+" "+open+".",
      "Markt-Timing: 10-Monats-Linie "+pp(d.rows.T_SMA10M.net)+", Dual Momentum seit "+d.rows.GEM.from+" "+pp(d.rows.GEM.net)+" (letzte 15 Jahre "+pp(d.rows.GEM.recent)+"), GTAA "+pp(d.rows.GTAA5.net)+". Kleinere Einbrüche, weniger Rendite."];
  }
  function describe(key,d=DATA){
    const s=Object.prototype.hasOwnProperty.call(STRATEGIES,key)?STRATEGIES[key]:null;
    if(!s||!d)return null;
    return {key,tier:s.tier,tierLabel:TIERS[s.tier].label,chip:s.chip||TIERS[s.tier].chip,title:s.title,verdict:s.verdict,facts:s.facts(d)};
  }
  function add(parent,tag,text,cls){
    const el=document.createElement(tag);if(cls)el.className=cls;if(text!=null)el.textContent=String(text);parent.appendChild(el);return el;
  }
  function decorate(container){
    for(const input of container.querySelectorAll("input[data-factor]")){
      const e=describe(input.dataset.factor),host=input.closest("label")?.querySelector("span");
      if(!e||!host)continue;
      let chip=host.querySelector(".evidence-chip");
      if(!chip)chip=add(host,"span",null,"evidence-chip");
      chip.className="evidence-chip evidence-"+e.tier;chip.textContent=e.chip;chip.title=e.verdict;
    }
  }
  function block(parent,title,tier,verdict,facts){
    const box=add(parent,"div",null,"evidence-block"+(tier?" evidence-"+tier:""));
    add(box,"strong",tier?title+" · "+TIERS[tier].label:title);add(box,"span",verdict);
    const list=add(box,"ul");for(const f of facts)add(list,"li",f);
  }
  function render(parent,d=DATA){
    if(!d){add(parent,"p","Die Auswertung konnte nicht geladen werden.");return;}
    add(parent,"p","Alle Zahlen sind der Abstand zum Markt in Prozentpunkten pro Jahr, nach Kosten. „Nicht gesichert“ heißt: Der Vorsprung kann Zufall sein. Vergangene Ergebnisse sagen die Zukunft nicht voraus.");
    const list=add(parent,"ul",null,"evidence-findings");for(const f of findings(d))add(list,"li",f);
    for(const key of Object.keys(STRATEGIES)){const e=describe(key,d);block(parent,e.title,e.tier,e.verdict,e.facts);}
    block(parent,ENTRY_EXIT.title,null,ENTRY_EXIT.verdict,ENTRY_EXIT.facts(d));
    block(parent,"Getestet und nicht eingebaut",null,"Diese Ideen sahen in einem Datensatz gut aus und in einem anderen nicht, oder sie kosteten Rendite.",notAdded(d));
    const p=add(parent,"p",null,"small muted");p.append("Stand der Daten: "+d.study.dataEnd+". Protokoll, alle "+d.study.strategies+" Ergebnisse und Grenzen: ");
    const link=add(p,"a","archivierte Studie vom 14.11.2026");link.href=STUDY_URL;link.target="_blank";link.rel="noopener noreferrer";p.append(".");
  }
  const api={data:DATA,tiers:TIERS,strategies:STRATEGIES,entryExit:ENTRY_EXIT,studyUrl:STUDY_URL,pp,describe,findings,notAdded,decorate,render};
  if(typeof module!=="undefined"&&module.exports)module.exports=api;
  root.StockEvidence=api;
})(typeof window!=="undefined"?window:globalThis);
