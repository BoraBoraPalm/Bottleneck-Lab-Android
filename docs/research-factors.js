(function(root){
  "use strict";
  const NAMES={quality:"Profitabilität / Quality",value:"Value · Bewertung",earnings:"Gewinnmomentum · Quartalsmodell",investment:"Konservatives Bilanzwachstum"};
  const LABELS={green:"Passt gut",yellow:"Passt teilweise",orange:"Passt wenig",red:"Passt schlecht",unknown:"Zu wenig Daten"};
  const finite=v=>typeof v==="number"&&Number.isFinite(v);
  const fmt=(v,d=2)=>finite(v)?v.toLocaleString("de-AT",{minimumFractionDigits:d,maximumFractionDigits:d}):"–";
  const pct=v=>finite(v)?fmt(v*100,1)+" %":"–";
  function assess(stock,key,options={}){
    const r=stock.factor_research?.[key];
    let state="unknown",reason=r?.reason||"Die zusätzlichen Faktordaten sind noch nicht vorhanden.";
    const now=+new Date(options.today||Date.now());
    const price=Date.parse(stock.price_date+"T00:00:00Z"),asof=Date.parse(r?.asof+"T00:00:00Z");
    const end=Date.parse(r?.report_end+"T00:00:00Z"),filed=Date.parse(r?.filed+"T00:00:00Z");
    const eventFiled=Date.parse(r?.event_filed+"T00:00:00Z");
    const fresh=[now,price,asof,end,filed].every(Number.isFinite)&&price<=now&&asof<=now&&filed<=price&&end<=filed
      &&(now-price)/86400000<8&&(now-asof)/86400000<8&&(now-end)/86400000<(key==="earnings"?181:551)
      &&(key!=="earnings"||(Number.isFinite(eventFiled)&&eventFiled<=filed&&(now-eventFiled)/86400000<121));
    if(stock.factor_research?.version===1&&r?.status==="ok"&&finite(r.value)&&Object.hasOwn(LABELS,r.state)&&fresh)state=r.state;
    else if(r?.status==="ok")reason="Die datierten Kurs-/Berichtsnachweise sind nicht mehr aktuell oder unvollständig.";
    return {key,name:NAMES[key],state,label:LABELS[state],reason};
  }
  function add(parent,tag,text,cls){
    const el=document.createElement(tag);if(cls)el.className=cls;if(text!=null)el.textContent=String(text);parent.appendChild(el);return el;
  }
  function render(parent,stock,chosen){
    const keys=(chosen||[]).filter(k=>Object.hasOwn(NAMES,k));
    if(!keys.length)return;
    const panel=add(parent,"section",null,"fund-panel");
    panel.setAttribute("aria-label","Zusätzliche Faktordaten "+stock.ticker);
    add(panel,"h3","Zusätzliche Faktordaten","fund-title");
    for(const key of keys){
      const f=assess(stock,key),r=stock.factor_research?.[key];
      const tile=add(panel,"div",null,"fit-tile fund-"+f.state);
      add(tile,"strong",f.name+" · "+f.label);add(tile,"span",f.reason);
      if(r?.status!=="ok"||f.state==="unknown")continue;
      const m=r.metrics||{};
      if(key==="quality")add(tile,"span","Bruttogewinn / Bilanzsumme: "+pct(m.gross_profit_to_assets)+" · operativer Cashflow / Bilanzsumme: "+pct(m.cashflow_to_assets));
      if(key==="value")add(tile,"span","KBV: "+fmt(m.pb)+"× · KGV (TTM): "+fmt(m.pe)+"× · Gewinnrendite: "+pct(m.earnings_yield)+" · FCF-Rendite: "+pct(m.fcf_yield));
      if(key==="investment")add(tile,"span","Jährliche Änderung der Bilanzsumme: "+pct(m.asset_growth));
      if(key==="earnings"){
        add(tile,"span","Quartalsgewinn: "+fmt(m.net_income_actual/1e6,1)+" Mio. USD · saisonaler Modellwert: "+fmt(m.net_income_expected_model/1e6,1)+" Mio. USD · Vergleich: "+m.quarters+" Quartale (davon "+m.derived_quarters+" aus dokumentierten Jahres-/YTD-Differenzen).");
        add(tile,"span","Eigenes Modell auf Gesamtgewinnbasis; Sondereffekte können den Wert stark verschieben. Aktienverwässerung/Rückkäufe und Analystenerwartungen werden nicht erfasst. Keine exakte EPS-SUE-/PEAD-Strategie.");
      }
      add(tile,"span","Berichtsende "+r.report_end+" · verwendet bis Filing "+r.filed+" · "+r.source);
      if(key==="value")add(tile,"span","Bewertungs-/Kursdatum: "+r.provider_date+" · Anbieterstand: "+r.provider_updated+". TTM-Kontextwerte sind Anbieterberechnungen.");
      if((r.source||"").includes("TGMCharts")){
        const link=add(tile,"a","Daten durch TGMCharts");link.href="https://tgmcharts.com/";link.target="_blank";link.rel="noopener noreferrer";
      }
    }
    add(panel,"p","Literaturmotivierte Merkmale; unsere Rangliste und Ampelgrenzen sind keine replizierten Forschungsportfolios und haben noch keinen nachgewiesenen Renditevorteil.","small muted");
  }
  const api={assess,render,names:NAMES};
  if(typeof module!=="undefined"&&module.exports)module.exports=api;
  root.StockResearch=api;
})(typeof window!=="undefined"?window:globalThis);
