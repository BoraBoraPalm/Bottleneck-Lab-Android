/* Fit to the app's research rules, independently of directory-search relevance. */
(function(root){
  "use strict";
  const LABELS={green:"Passt gut",yellow:"Passt teilweise",orange:"Passt wenig",red:"Passt schlecht",unknown:"Zu wenig Daten"};
  const NAMES={momentum:"12–2-Momentum",lowRisk:"Geringe Schwankung · 12M",trend:"200-Tage-Trend",
    sander:"Hoch-Tief-Mut",growth:"Frühwachstum / Multibagger",quality:"Profitabilität / Quality",
    value:"Value · Bewertung",earnings:"Gewinnmomentum · Quartalsmodell",investment:"Konservatives Bilanzwachstum"};
  const finite=x=>typeof x==="number"&&Number.isFinite(x);
  const fmt=(n,d=1)=>finite(n)?n.toLocaleString("de-AT",{minimumFractionDigits:d,maximumFractionDigits:d}):"–";
  const pct=n=>fmt(100*n)+" %";
  function currentPrice(s,now){
    const d=Date.parse(s.price_date+"T00:00:00Z");
    return Number.isFinite(d)&&d<=now&&(now-d)/86400000<8;
  }
  function currentAnnual(f,now){
    const end=Date.parse(f?.fy_end+"T00:00:00Z"),filed=Date.parse(f?.filed+"T00:00:00Z");
    return Number.isFinite(end)&&Number.isFinite(filed)&&end<=filed&&filed<=now&&(now-end)/86400000<=550;
  }
  function gradedChecks(checks,success){
    const failed=checks.filter(x=>!x.ok);
    if(!failed.length)return {state:"green",reason:success};
    const ratio=(checks.length-failed.length)/checks.length;
    return {state:ratio>=.75?"yellow":ratio>=.5?"orange":"red",reason:failed.slice(0,2).map(x=>x.reason).join(" · ")};
  }
  function assess(stock,key,options={}){
    const now=+new Date(options.today||Date.now()),s=stock||{};
    let result={state:"unknown",reason:"Die benötigten Nachweise fehlen."};
    if(!Object.hasOwn(NAMES,key))return null;
    if(["quality","value","earnings","investment"].includes(key)){
      return root.StockResearch?root.StockResearch.assess(s,key,options):{key,name:NAMES[key],state:"unknown",label:LABELS.unknown,reason:"Die zusätzlichen Faktordaten fehlen."};
    }
    const price=currentPrice(s,now);
    const yahoo=s.source==="Yahoo Finance";
    const context=String(s.context_basis||"").startsWith("Yahoo adjusted OHLC");
    if(key==="momentum"){
      if(price&&yahoo&&s.momentum_basis==="Yahoo adjusted daily closes"&&finite(s.momentum_12_2)){
        const v=s.momentum_12_2;
        result={state:v>=.2?"green":v>=0?"yellow":v>=-.15?"orange":"red",
          reason:pct(v)+" Kursentwicklung im 12–2-Monatsfenster."};
      }else result.reason="Aktuelle, bereinigte 12–2-Momentumhistorie fehlt.";
    }else if(key==="lowRisk"){
      if(price&&yahoo&&s.long_risk_basis==="Yahoo adjusted log returns; 252 sessions; annualised sqrt(252)"
          &&finite(s.volatility_252d)&&s.volatility_252d>=0){
        const v=s.volatility_252d;
        result={state:v<=.2?"green":v<=.35?"yellow":v<=.5?"orange":"red",
          reason:"Annualisierte Renditeschwankung über 252 Handelstage: "+pct(v)+"."};
      }else result.reason="252 bereinigte Tagesrenditen für die längerfristige Risikomessung fehlen.";
    }else if(key==="trend"){
      if(price&&yahoo&&context&&finite(s.sma200_ratio)){
        const v=s.sma200_ratio;
        result={state:v>=0?"green":v>=-.05?"yellow":v>=-.15?"orange":"red",
          reason:pct(Math.abs(v))+(v>=0?" über":" unter")+" dem 200-Tage-Durchschnitt."};
      }else result.reason="Aktuelle, bereinigte 200-Tage-Kurshistorie fehlt.";
    }else if(key==="sander"){
      const f=s.fundamentals;
      if(!currentAnnual(f,now))result.reason="Ein aktueller, datierter Jahresbericht fehlt.";
      else if(!price||!yahoo||!finite(s.drawdown_252d))result.reason="Aktueller Abstand zum 252-Tage-Hoch fehlt.";
      else if(![f.net_income,f.operating_cashflow,f.profit_margin,f.revenue_growth_yoy].every(finite))
        result.reason="Gewinn, Cashflow, Marge oder Vorjahresumsatz fehlen.";
      else{
        const dd=-s.drawdown_252d;
        result=gradedChecks([
          {ok:dd>=.15&&dd<=.55,reason:"Rückgang "+pct(dd)+"; gesucht sind 15–55 %."},
          {ok:f.net_income>0,reason:"Kein positiver Jahresgewinn."},
          {ok:f.operating_cashflow>0,reason:"Kein positiver operativer Jahres-Cashflow."},
          {ok:f.profit_margin>=.03,reason:"Nettomarge "+pct(f.profit_margin)+"; mindestens 3 % gesucht."},
          {ok:f.revenue_growth_yoy>=-.1,reason:"Jahresumsatz fällt um mehr als 10 %."}
        ],"Rückgang "+pct(dd)+"; Gewinn, Cashflow, Marge und Umsatz erfüllen die Vorauswahl.");
      }
    }else if(key==="growth"){
      const r=s.growth_radar,qs=r?.quarters;
      if(!r||!Array.isArray(qs)||qs.length!==3)result.reason="Drei vergleichbare Quartale mit Vorjahresdaten fehlen.";
      else if(["missing_quarters","stale_quarters","missing_quality","stale_financials","missing_price","sector_specific"].includes(r.status)){
        result.reason={missing_quarters:"Vergleichbare Quartalsdaten fehlen.",stale_quarters:"Quartalsdaten sind veraltet.",
          missing_quality:"Gewinn- oder Cashflow-Nachweise fehlen.",stale_financials:"Jahresdaten sind veraltet oder ungeprüft.",
          missing_price:"Ein passender Aktien-/Weltmarkt-Kursvergleich fehlt.",sector_specific:"Diese Branche benötigt eine eigene Bewertung."}[r.status];
      }else if(!price||!currentAnnual(s.fundamentals,now)||qs.some(q=>{
        const end=Date.parse(q.end+"T00:00:00Z"),filed=Date.parse(q.filed+"T00:00:00Z");
        return !Number.isFinite(end)||!Number.isFinite(filed)||end>filed||filed>now||filed>Date.parse(s.price_date+"T00:00:00Z");
      })||(now-Date.parse(qs[2].end+"T00:00:00Z"))/86400000>180)
        result.reason="Aktuelle, datierte Quartals- und Kursnachweise fehlen.";
      else{
        const rates=qs.map(q=>q.revenue_growth_yoy),last=qs[2];
        const values=[...rates,r.revenue_acceleration,r.annual_cashflow_margin,last.net_margin,
          r.net_margin_change_yoy,s.return_63d,r.relative_63d,r.breakout_63d_ratio];
        if(values.every(finite)&&["qualified","criteria_not_met"].includes(r.status)){
          result=gradedChecks([
            {ok:rates[2]>=.2,reason:"Quartalswachstum "+pct(rates[2])+"; mindestens 20 % gesucht."},
            {ok:(rates[0]+rates[1])/2>=.1,reason:"Die zwei vorherigen Wachstumsraten liegen im Mittel unter 10 %."},
            {ok:r.revenue_acceleration>=.02-1e-9,reason:"Beschleunigung "+fmt(r.revenue_acceleration*100)+" Prozentpunkte; mindestens 2 gesucht."},
            {ok:r.annual_cashflow_margin>0,reason:"Kein positiver operativer Jahres-Cashflow."},
            {ok:last.net_margin>=0||r.net_margin_change_yoy>=.03,reason:"Verlustmarge verbessert sich noch nicht ausreichend."},
            {ok:s.return_63d>0,reason:"Der Kurs ist über 63 Handelstage nicht gestiegen."},
            {ok:r.relative_63d>0,reason:"Über 63 Handelstage schwächer als der Weltmarktindikator ACWI."},
            {ok:r.breakout_63d_ratio>=-.15,reason:"Mehr als 15 % unter dem vorherigen 63-Tage-Hoch."}
          ],"Umsatz +"+pct(rates[2])+", Beschleunigung "+fmt(r.revenue_acceleration*100)+" Prozentpunkte; Qualitäts- und Kursregeln erfüllt.");
        }else result.reason="Die Wachstums-, Qualitäts- oder Kursprüfung ist unvollständig.";
      }
    }
    return {key,name:NAMES[key],...result,label:LABELS[result.state]};
  }
  function render(parent,stock,chosen){
    if(!chosen?.length)return;
    const panel=document.createElement("div");panel.className="fit-grid";
    panel.setAttribute("aria-label","Passung zu ausgewählten Strategien");
    for(const key of chosen){
      const fit=assess(stock,key);
      if(!fit)continue;
      const tile=document.createElement("div");tile.className="fit-tile fund-"+fit.state;
      const heading=document.createElement("strong");heading.textContent=fit.name+" · "+fit.label;
      const reason=document.createElement("span");reason.textContent=fit.reason;
      tile.append(heading,reason);panel.appendChild(tile);
    }
    parent.appendChild(panel);
  }
  const api={assess,render,names:NAMES,labels:LABELS};
  if(typeof module!=="undefined"&&module.exports)module.exports=api;
  root.StockFit=api;
})(typeof window!=="undefined"?window:globalThis);
