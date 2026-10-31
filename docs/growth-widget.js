/* Transparent early-growth rule values, never a return forecast. */
(function(root){
  "use strict";
  const finite=x=>typeof x==="number"&&Number.isFinite(x);
  const fmt=(n,d=1)=>finite(n)?n.toLocaleString("de-AT",{minimumFractionDigits:d,maximumFractionDigits:d}):"–";
  const percent=n=>finite(n)?fmt(n*100)+" %":"Daten fehlen";
  const STATUSES={
    qualified:"Vorauswahl erfüllt",criteria_not_met:"Vorauswahl nicht erfüllt",
    missing_quarters:"Drei vergleichbare Quartale fehlen",stale_quarters:"Quartalsbericht veraltet",
    missing_quality:"Gewinn- oder Cashflow-Daten fehlen",stale_financials:"Jahresdaten veraltet oder ungeprüft",
    missing_price:"Kurs- oder Weltmarktvergleich fehlt",sector_specific:"Branchenspezifische Prüfung nötig"
  };
  function state(stock,today){
    const radar=stock.growth_radar;
    if(!radar||typeof radar!=="object")return {status:"missing_quarters",usable:false};
    const now=new Date(today||Date.now());
    const quote=new Date(stock.price_date+"T00:00:00Z");
    const qs=radar.quarters;
    if(!Array.isArray(qs)||qs.length!==3)return {status:radar.status,usable:false};
    const dates=qs.map(q=>[Date.parse(q.end+"T00:00:00Z"),Date.parse(q.filed+"T00:00:00Z")]);
    const verified=Number.isFinite(+now)&&Number.isFinite(+quote)&&dates.every(([end,filed])=>
      Number.isFinite(end)&&Number.isFinite(filed)&&end<=filed&&filed<=+now&&filed<=+quote);
    if(!verified)return {status:"missing_quarters",usable:false};
    if((+now-dates[2][0])/86400000>180)return {status:"stale_quarters",usable:false};
    const freshQuote=quote<=now&&(now-quote)/86400000<=8;
    const components=[radar.growth_score,radar.quality_score,radar.confirmation_score];
    return {status:freshQuote?radar.status:"missing_price",usable:true,
      qualified:freshQuote&&radar.status==="qualified"&&components.every(v=>finite(v)&&v>=0&&v<=100)
        &&finite(radar.score)&&radar.score>=0&&radar.score<=100};
  }
  function add(parent,tag,text,cls){
    const el=document.createElement(tag);
    if(cls)el.className=cls;
    if(text!=null)el.textContent=String(text);
    parent.appendChild(el);return el;
  }
  function preview(parent,stock){
    const radar=stock.growth_radar||{},s=state(stock);
    const row=add(parent,"div",null,"fund-preview growth-preview");
    row.setAttribute("aria-label","Frühwachstum im Überblick");
    if(!s.qualified){add(row,"span",STATUSES[s.status]||"Daten fehlen","fund-pill fund-unknown");return;}
    for(const [label,key] of [["Wachstum","growth_score"],["Qualität","quality_score"],["Kursbestätigung","confirmation_score"]])
      add(row,"span",label+" "+fmt(radar[key],0)+"/100","fund-pill growth-pill");
  }
  function render(parent,stock){
    const radar=stock.growth_radar||{},s=state(stock);
    const panel=add(parent,"section",null,"fund-panel growth-panel");
    panel.setAttribute("aria-label","Frühwachstum "+stock.ticker);
    add(panel,"h3","Frühwachstum / Multibagger-Kandidaten","fund-title");
    add(panel,"p",(STATUSES[s.status]||"Daten fehlen")+(s.qualified?" · Regelwert "+fmt(radar.score)+"/100":""),"growth-status");
    if(s.usable){
      const components=add(panel,"div",null,"growth-components");
      for(const [label,key,weight] of [["Wachstum","growth_score","45 %"],["Finanzielle Qualität","quality_score","30 %"],["Kursbestätigung","confirmation_score","25 %"]]){
        const col=add(components,"div",null,"growth-component");
        add(col,"small",label+" · Gewicht "+weight);
        const value=key==="confirmation_score"&&s.status==="missing_price"?null:radar[key];
        add(col,"strong",finite(value)?fmt(value)+"/100":"Daten fehlen");
      }
      const wrap=add(panel,"div",null,"growth-table-wrap");
      const table=add(wrap,"table",null,"growth-table");
      add(table,"caption","Letzte drei Quartale · jeweils gegenüber dem Vorjahresquartal");
      const head=add(table,"thead"),header=add(head,"tr");
      for(const text of ["Quartalsende","Umsatzwachstum","Nettomarge"]){const th=add(header,"th",text);th.scope="col";}
      const body=add(table,"tbody");
      for(const q of radar.quarters){
        const row=add(body,"tr");
        add(row,"td",q.end+(q.derived?" *":""));
        add(row,"td",percent(q.revenue_growth_yoy));
        add(row,"td",percent(q.net_margin));
      }
      const latest=radar.quarters[2];
      const facts=add(panel,"div",null,"details growth-facts");
      const rows=[
        ["Wachstumsbeschleunigung zum vorigen Quartal",finite(radar.revenue_acceleration)?fmt(radar.revenue_acceleration*100)+" Prozentpunkte":"Daten fehlen"],
        ["Nettomargenänderung zum Vorjahresquartal",finite(radar.net_margin_change_yoy)?fmt(radar.net_margin_change_yoy*100)+" Prozentpunkte":"Daten fehlen"],
        ["Operative Cashflow-Marge · Jahresbericht",percent(radar.annual_cashflow_margin)+(radar.annual_end?" · "+radar.annual_end:"")]
      ];
      if(s.status!=="missing_price")rows.push(
        ["Relative Kursstärke 3M / 6M gegenüber ACWI",percent(radar.relative_63d)+" / "+percent(radar.relative_126d)],
        ["Abstand zum vorherigen 63-Tage-Schlusshoch",percent(radar.breakout_63d_ratio)],
        ["Letzter Handelsumsatz / vorheriger 20-Tage-Durchschnitt",finite(radar.turnover_ratio_20d)?fmt(radar.turnover_ratio_20d)+"×":"Daten fehlen"]);
      for(const [label,value] of rows){const col=add(facts,"div",null,"detail");add(col,"small",label);add(col,"strong",value);}
      add(panel,"p","Quartalsquelle: "+(radar.source||"ungeprüft")+" · jüngstes verwendetes Filing "+latest.filed,"small muted");
      if((radar.source||"").includes("TGMCharts")){
        const link=add(panel,"a","Datenbereitstellung durch TGMCharts · SEC-EDGAR-XBRL","small");
        link.href="https://tgmcharts.com/";link.target="_blank";link.rel="noopener noreferrer";
      }
      if(radar.quarters.some(q=>q.derived))add(panel,"p","* Mindestens ein Quartalswert wurde vom Datenanbieter aus passenden kumulierten SEC-Angaben abgeleitet.","small muted");
    }
    add(panel,"p","Zusätzlich selbst prüfen: Bewertung, Gewinnüberraschungen / Prognoseanhebungen, Wettbewerbsvorteil und Aktienverwässerung. Diese Punkte sind hier ungeprüft und erhalten keine Punkte.","small muted");
    add(panel,"p","Eigene experimentelle Vorauswahl. Die Werte sind weder Gewinnwahrscheinlichkeiten noch prognostizierte Kursvervielfachungen. Noch kein historisch validierter Vorteil.","small muted");
  }
  const api={state,preview,render};
  if(typeof module!=="undefined"&&module.exports)module.exports=api;
  root.StockGrowth=api;
})(typeof window!=="undefined"?window:globalThis);
