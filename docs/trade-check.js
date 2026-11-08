/* Depot-Check: eigene Käufe und Verkäufe gegen einen passenden Benchmark.

   Rechnung: Gesamtrendite aus bereinigten Tagesschlusskursen (inkl. Dividenden
   und Splits), in EUR umgerechnet mit historischen Wechselkursen. Eigene Kauf-
   oder Verkaufskurse ersetzen den Schlusskurs des jeweiligen Tages; Dividenden
   und Splits bleiben dabei berücksichtigt:
     Rendite = bereinigte Rendite × (eigener Verkaufskurs / Schlusskurs Verkaufstag)
                                  ÷ (eigener Kaufkurs / Schlusskurs Kauftag).
   Benchmark: dieselben Tage, ebenfalls inkl. Dividenden und in EUR. */
(function(root){
  "use strict";
  const STORAGE_KEY="bottleneck.trade-check.v1";
  const DAY=86400000;
  const finite=v=>typeof v==="number"&&Number.isFinite(v);
  const ISO=/^\d{4}-\d{2}-\d{2}$/;

  // Same list as scripts/benchmarks.py (checked by tests/test_benchmarks.py).
  const EUROPE=["AT","BE","CH","CZ","DK","ES","FI","FR","GR","HU","IE","IS","IT","LU","NL","NO","PL","PT","RO","SE"];
  const EMERGING=["AE","BR","CL","CO","EG","ID","KW","MX","MY","PE","PH","QA","SA","TH","TR","ZA"];
  const BENCHMARKS=[
    {id:"SPY",symbol:"SPY",name:"S&P 500",markets:["US"]},
    {id:"DAX",symbol:"^GDAXI",name:"DAX",markets:["DE"]},
    {id:"STOXX600",symbol:"EXSA.DE",name:"STOXX Europe 600",markets:EUROPE},
    {id:"FTSE100",symbol:"ISF.L",name:"FTSE 100",markets:["GB"]},
    {id:"TSX60",symbol:"XIU.TO",name:"S&P/TSX 60",markets:["CA"]},
    {id:"TOPIX",symbol:"1306.T",name:"TOPIX",markets:["JP"]},
    {id:"HSI",symbol:"2800.HK",name:"Hang Seng",markets:["HK"]},
    {id:"ASX200",symbol:"STW.AX",name:"S&P/ASX 200",markets:["AU","NZ"]},
    {id:"KOSPI200",symbol:"069500.KS",name:"KOSPI 200",markets:["KR"]},
    {id:"TW50",symbol:"0050.TW",name:"Taiwan 50",markets:["TW"]},
    {id:"NIFTY50",symbol:"NIFTYBEES.NS",name:"Nifty 50",markets:["IN"]},
    {id:"CSI300",symbol:"510300.SS",name:"CSI 300",markets:["CN"]},
    {id:"EM",symbol:"EEM",name:"MSCI Emerging Markets",markets:EMERGING},
    {id:"WORLD",symbol:"IWDA.AS",name:"MSCI World",markets:[]},
    {id:"ACWI",symbol:"ACWI",name:"MSCI ACWI (Welt)",markets:["*"]}
  ];
  const SUFFIX_COUNTRY={DE:"DE",F:"DE",SG:"DE",MU:"DE",BE:"DE",DU:"DE",HM:"DE",HA:"DE",PA:"FR",AS:"NL",BR:"BE",
    LS:"PT",VI:"AT",MI:"IT",MC:"ES",L:"GB",IL:"GB",SW:"CH",ST:"SE",CO:"DK",HE:"FI",OL:"NO",IR:"IE",WA:"PL",
    PR:"CZ",BD:"HU",RO:"RO",AT:"GR",IC:"IS",T:"JP",HK:"HK",AX:"AU",NZ:"NZ",TO:"CA",V:"CA",NE:"CA",KS:"KR",KQ:"KR",
    TW:"TW",TWO:"TW",NS:"IN",BO:"IN",SS:"CN",SZ:"CN",SA:"BR",MX:"MX",JO:"ZA",IS:"TR",SR:"SA",QA:"QA",
    JK:"ID",BK:"TH",KL:"MY",PS:"PH",SI:"SG",TA:"IL",CA:"EG",SN:"CL",BA:"AR",LM:"PE",CL:"CO",KW:"KW",AE:"AE"};

  // ---------- reine Rechenfunktionen ----------
  function onOrAfter(points,day){
    let lo=0,hi=points.length;
    while(lo<hi){const mid=(lo+hi)>>1;if(points[mid][0]<day)lo=mid+1;else hi=mid;}
    return lo<points.length?lo:-1;
  }
  function onOrBefore(points,day){
    let lo=0,hi=points.length;
    while(lo<hi){const mid=(lo+hi)>>1;if(points[mid][0]<=day)lo=mid+1;else hi=mid;}
    return lo-1;
  }
  // Yahoo quotes London in pence (GBp), Tel Aviv in agorot (ILA), Johannesburg in cents (ZAc).
  function fxSymbol(currency){
    const c=String(currency||"");
    if(c==="EUR")return null;
    const sub={GBp:["GBP",.01],GBX:["GBP",.01],ILA:["ILS",.01],ZAc:["ZAR",.01]}[c];
    if(sub)return {symbol:sub[0]+"EUR=X",scale:sub[1]};
    return /^[A-Z]{3}$/.test(c)?{symbol:c+"EUR=X",scale:1}:null;
  }
  // Issuer country: directory country, else ISIN country, else exchange suffix.
  function countryOf(stock){
    const cc=String(stock&&stock.country_code||"").toUpperCase();
    if(/^[A-Z]{2}$/.test(cc))return cc;
    const isin=String(stock&&(stock.reference_isin||stock.tr_isin)||"").toUpperCase();
    if(/^[A-Z]{2}[A-Z0-9]{9}\d$/.test(isin))return isin.slice(0,2);
    const ticker=String(stock&&stock.ticker||"").toUpperCase();
    const dot=ticker.lastIndexOf(".");
    return dot>0?SUFFIX_COUNTRY[ticker.slice(dot+1)]||null:"US";
  }
  function pickBenchmark(stock,available){
    const usable=BENCHMARKS.filter(b=>!available||available.has(b.id));
    const country=countryOf(stock);
    return usable.find(b=>country&&b.markets.includes(country))||usable.find(b=>b.markets.includes("*"))||usable[0]||null;
  }
  const valueAt=(series,day)=>{
    if(!series)return null;
    let i=onOrBefore(series.points,day);
    if(i<0)i=onOrAfter(series.points,day);
    return i<0?null:series.points[i][1]*(series.scale||1);
  };
  const daysBetween=(a,b)=>Math.round((Date.parse(b+"T00:00:00Z")-Date.parse(a+"T00:00:00Z"))/DAY);
  const annual=(ret,days)=>days>=365?Math.pow(1+ret,365/days)-1:null;

  /* input: {buy, sell, open, buyPrice, sellPrice, shares}
     stock: {points, closes, currency}; fx/benchFx: {points, scale} or null (EUR)
     bench: {points, currency, name} */
  function compute(input,stock,fx,bench,benchFx){
    const P=stock&&stock.points,C=stock&&stock.closes;
    if(!Array.isArray(P)||!P.length)return {error:"Keine Kursreihe für diese Aktie."};
    if(!ISO.test(input.buy||""))return {error:"Kaufdatum fehlt."};
    if(input.buy<P[0][0])return {error:"Die Kursreihe beginnt erst am "+P[0][0]+" (höchstens rund zehn Jahre zurück)."};
    const ib=onOrAfter(P,input.buy);
    if(ib<0)return {error:"Für das Kaufdatum gibt es noch keinen Schlusskurs."};
    let is=P.length-1,note=null;
    if(!input.open){
      if(!ISO.test(input.sell||""))return {error:"Verkaufsdatum fehlt – oder „noch im Depot“ anhaken."};
      if(input.sell<input.buy)return {error:"Das Verkaufsdatum liegt vor dem Kaufdatum."};
      const found=onOrAfter(P,input.sell);
      if(found<0)note="Für das Verkaufsdatum gibt es noch keinen Schlusskurs; verwendet wird der letzte vom "+P[is][0]+".";
      else is=found;
    }
    if(is<ib)is=ib;
    const buyDay=P[ib][0],sellDay=P[is][0];
    const rawB=Array.isArray(C)?C[ib]:null,rawS=Array.isArray(C)?C[is]:null;
    if(!(rawB>0&&rawS>0))return {error:"Unbereinigte Schlusskurse fehlen in der Kursantwort."};
    const ownBuy=finite(input.buyPrice)&&input.buyPrice>0,ownSell=finite(input.sellPrice)&&input.sellPrice>0;
    const buyPrice=ownBuy?input.buyPrice:rawB,sellPrice=ownSell?input.sellPrice:rawS;
    const local=P[is][1]/P[ib][1]*(sellPrice/rawS)/(buyPrice/rawB)-1;
    const fxB=fx?valueAt(fx,buyDay):1,fxS=fx?valueAt(fx,sellDay):1;
    if(!(fxB>0&&fxS>0))return {error:"Wechselkurs "+stock.currency+"/EUR für diesen Zeitraum nicht verfügbar."};
    const stockEur=(1+local)*(fxS/fxB)-1;
    if(!bench||!Array.isArray(bench.points)||!bench.points.length)return {error:"Keine Benchmark-Kursreihe."};
    const B=bench.points,jb=onOrBefore(B,buyDay),js=onOrBefore(B,sellDay);
    if(jb<0)return {error:"Die Benchmark-Reihe ("+(bench.name||"Benchmark")+") beginnt erst am "+B[0][0]+"."};
    const bfB=benchFx?valueAt(benchFx,B[jb][0]):1,bfS=benchFx?valueAt(benchFx,B[js][0]):1;
    if(!(bfB>0&&bfS>0))return {error:"Wechselkurs "+bench.currency+"/EUR für den Benchmark nicht verfügbar."};
    const benchEur=B[js][1]/B[jb][1]*(bfS/bfB)-1;
    const days=daysBetween(buyDay,sellDay);
    const shares=finite(input.shares)&&input.shares>0?input.shares:null;
    const invested=shares?buyPrice*shares*fxB:1000;
    // Time course (100 = buy day), at most ~240 points.
    const step=Math.max(1,Math.ceil((is-ib+1)/240)),chart=[];
    for(let t=ib;t<=is;t+=step){
      const d=P[t][0],k=onOrBefore(B,d);
      const bf=benchFx?valueAt(benchFx,d):1,sf=fx?valueAt(fx,d):1;
      chart.push([d,100*P[t][1]/P[ib][1]*sf/fxB,k>=0?100*B[k][1]/B[jb][1]*bf/bfB:null]);
    }
    if(chart[chart.length-1][0]!==sellDay){
      const bf=benchFx?valueAt(benchFx,sellDay):1;
      chart.push([sellDay,100*P[is][1]/P[ib][1]*fxS/fxB,100*B[js][1]/B[jb][1]*bf/bfB]);
    }
    return {
      buyDay,sellDay,open:!!input.open,days,currency:stock.currency,note,
      closeBuy:rawB,closeSell:rawS,buyPrice,sellPrice,ownBuy,ownSell,
      buyEur:buyPrice*fxB,sellEur:sellPrice*fxS,shares,invested,
      stockLocal:local,stockEur,benchEur,outperformance:stockEur-benchEur,
      stockAnnual:annual(stockEur,days),benchAnnual:annual(benchEur,days),
      endValue:invested*(1+stockEur),benchValue:invested*(1+benchEur),
      benchDays:[B[jb][0],B[js][0]],chart
    };
  }
  function portfolio(results){
    const ok=results.filter(r=>r&&!r.error);
    if(!ok.length)return null;
    const invested=ok.reduce((a,r)=>a+r.invested,0),end=ok.reduce((a,r)=>a+r.endValue,0),bench=ok.reduce((a,r)=>a+r.benchValue,0);
    return {count:ok.length,invested,end,bench,stockReturn:end/invested-1,benchReturn:bench/invested-1,
      difference:end-bench,outperformance:end/invested-bench/invested,estimatedAmounts:ok.some(r=>!r.shares)};
  }

  // ---------- Speicher (nur dieses Gerät) ----------
  function readState(storage){
    try{
      const raw=JSON.parse(storage.getItem(STORAGE_KEY));
      if(raw&&raw.version===1&&Array.isArray(raw.rows))return raw;
    }catch{}
    return null;
  }
  function writeState(storage,state){
    try{storage.setItem(STORAGE_KEY,JSON.stringify({version:1,rows:state.rows,benchmark:state.benchmark}));}catch{}
  }

  // ---------- Oberfläche ----------
  const nf=(v,d=1)=>new Intl.NumberFormat("de-AT",{minimumFractionDigits:d,maximumFractionDigits:d}).format(v);
  const pct=(v,d=1)=>finite(v)?(v>0?"+":"")+nf(v*100,d)+" %":"–";
  const pp=v=>finite(v)?(v>0?"+":"")+nf(v*100,1)+" Prozentpunkte":"–";
  const eur=v=>finite(v)?new Intl.NumberFormat("de-AT",{style:"currency",currency:"EUR"}).format(v):"–";
  const price=(v,c)=>finite(v)?nf(v,v<10?4:2)+" "+(c||""):"–";
  const date=d=>d?d.split("-").reverse().join("."):"–";
  function el(parent,tag,text,cls){
    const node=document.createElement(tag);
    if(text!==null&&text!==undefined)node.textContent=text;
    if(cls)node.className=cls;
    if(parent)parent.appendChild(node);
    return node;
  }
  let uid=0;
  const newRow=()=>({id:"r"+(++uid)+"-"+Date.now().toString(36),ticker:"",name:"",exchange:"",country_code:"",reference_isin:"",
    buy:"",sell:"",open:false,buyPrice:null,sellPrice:null,buyOwn:false,sellOwn:false,shares:null});

  function lineChart(parent,chart,labels){
    const W=320,H=150,pad={l:34,r:8,t:10,b:22};
    const vals=chart.flatMap(p=>[p[1],p[2]]).filter(finite);
    let lo=Math.min(100,...vals),hi=Math.max(100,...vals);
    if(hi-lo<1){hi+=1;lo-=1;}
    const x=i=>pad.l+(W-pad.l-pad.r)*(chart.length<2?0:i/(chart.length-1));
    const y=v=>pad.t+(H-pad.t-pad.b)*(1-(v-lo)/(hi-lo));
    const ns="http://www.w3.org/2000/svg";
    const svg=document.createElementNS(ns,"svg");
    svg.setAttribute("viewBox","0 0 "+W+" "+H);svg.setAttribute("class","tc-chart");
    svg.setAttribute("role","img");
    svg.setAttribute("aria-label","Wertentwicklung ab Kauftag (100): "+labels[0]+" und "+labels[1]);
    const add=(tag,attrs)=>{const n=document.createElementNS(ns,tag);for(const [k,v] of Object.entries(attrs))n.setAttribute(k,v);svg.appendChild(n);return n;};
    add("line",{x1:pad.l,x2:W-pad.r,y1:y(100),y2:y(100),class:"tc-base"});
    for(const [v,anchor] of [[hi,"hi"],[lo,"lo"],[100,"base"]]){
      const t=add("text",{x:pad.l-4,y:y(v)+3,"text-anchor":"end",class:"tc-axis"});t.textContent=nf(v,0);
      if(anchor==="base"&&(Math.abs(y(100)-y(hi))<10||Math.abs(y(100)-y(lo))<10))t.remove();
    }
    const t1=add("text",{x:pad.l,y:H-6,class:"tc-axis"});t1.textContent=date(chart[0][0]);
    const t2=add("text",{x:W-pad.r,y:H-6,"text-anchor":"end",class:"tc-axis"});t2.textContent=date(chart[chart.length-1][0]);
    for(const [k,cls] of [[2,"tc-line-bench"],[1,"tc-line-stock"]]){
      const pts=chart.map((p,i)=>finite(p[k])?x(i).toFixed(1)+","+y(p[k]).toFixed(1):null).filter(Boolean);
      if(pts.length>1)add("polyline",{points:pts.join(" "),class:cls,fill:"none"});
    }
    parent.appendChild(svg);
    const legend=el(parent,"div",null,"tc-legend");
    el(legend,"span",labels[0],"tc-key tc-key-stock");el(legend,"span",labels[1],"tc-key tc-key-bench");
  }

  function create(container,deps){
    const storage=(()=>{try{return root.localStorage||null;}catch{return null;}})();
    const saved=storage?readState(storage):null;
    const state={rows:saved&&saved.rows.length?saved.rows.map(r=>({...newRow(),...r})):[newRow()],
      benchmark:saved&&saved.benchmark?saved.benchmark:{mode:"auto",preset:"ACWI",symbol:""}};
    let searchIndex=null,indexLoading=null,available=null,availableLoading=null;
    const save=()=>{if(storage)writeState(storage,state);};

    container.replaceChildren();
    el(container,"h2","Depot-Check");
    el(container,"p","Trage Käufe ein – auch mehrere oder noch offene Positionen – und vergleiche sie mit einem passenden Markt. Kauf- und Verkaufskurse werden aus den Tagesschlusskursen vorgeschlagen und lassen sich mit deinen echten Kursen überschreiben. Alles bleibt nur auf diesem Gerät gespeichert.","muted small");
    const list=el(container,"div",null,"tc-rows");
    const addBtn=el(container,"button","+ Position hinzufügen","btn secondary tc-add");addBtn.type="button";

    const bench=el(container,"fieldset",null,"tc-bench");
    el(bench,"legend","Benchmark");
    const autoLabel=el(bench,"label",null,"tc-radio");
    const autoRadio=el(autoLabel,"input");autoRadio.type="radio";autoRadio.name="tcBench";autoRadio.value="auto";
    el(autoLabel,"span","Automatisch: je Aktie der passende Markt (z. B. DAX für deutsche, S&P 500 für US-Aktien, MSCI ACWI sonst)");
    const manualLabel=el(bench,"label",null,"tc-radio");
    const manualRadio=el(manualLabel,"input");manualRadio.type="radio";manualRadio.name="tcBench";manualRadio.value="manual";
    el(manualLabel,"span","Manuell für alle Positionen:");
    const manualBox=el(bench,"div",null,"tc-grid");
    const presetWrap=el(manualBox,"label",null,"field");el(presetWrap,"span","Liste");
    const preset=el(presetWrap,"select");
    for(const b of BENCHMARKS){const o=el(preset,"option",b.name+" · "+b.symbol);o.value=b.id;}
    const otherOpt=el(preset,"option","Eigenes Symbol …");otherOpt.value="custom";
    const symbolWrap=el(manualBox,"label",null,"field");el(symbolWrap,"span","Eigenes Yahoo-Symbol");
    const symbolInput=el(symbolWrap,"input");symbolInput.type="text";symbolInput.placeholder="z. B. IWDA.AS, ^GDAXI, VWCE.DE";
    symbolInput.autocapitalize="characters";symbolInput.spellcheck=false;symbolInput.maxLength=22;

    const run=el(container,"button","Mit Benchmark vergleichen","btn tc-run");run.type="button";
    const status=el(container,"p",null,"small muted tc-status");status.setAttribute("role","status");status.setAttribute("aria-live","polite");
    const out=el(container,"div",null,"tc-results");
    const info=el(container,"details",null,"tc-info");
    el(info,"summary","So wird gerechnet");
    for(const text of [
      "Rendite: Tagesschlusskurse von Yahoo Finance, bereinigt um Dividenden und Splits (Dividenden gelten als wieder angelegt), umgerechnet in EUR mit historischen Wechselkursen. Kauf am ersten Handelstag ab dem Kaufdatum, Verkauf am ersten Handelstag ab dem Verkaufsdatum; bei „noch im Depot“ der letzte Schlusskurs.",
      "Eigene Kurse ersetzen den Schlusskurs des jeweiligen Tages; Dividenden und Splits werden weiter berücksichtigt. Ordergebühren und Steuern sind nicht enthalten.",
      "Benchmarks sind breite ETFs bzw. Performanceindizes inklusive Dividenden. Verglichen werden dieselben Tage. Bei mehreren Positionen zeigt die Summe, was aus demselben Geld zu denselben Zeitpunkten im jeweiligen Benchmark geworden wäre. Ohne Stückzahl rechnet jede Position mit 1.000 €.",
      "Vergangene Wertentwicklung ist keine Prognose."])el(info,"p",text,"small muted");

    function syncBenchUi(){
      autoRadio.checked=state.benchmark.mode!=="manual";manualRadio.checked=state.benchmark.mode==="manual";
      preset.value=state.benchmark.preset||"ACWI";symbolInput.value=state.benchmark.symbol||"";
      manualBox.hidden=state.benchmark.mode!=="manual";symbolWrap.hidden=preset.value!=="custom";
    }
    autoRadio.addEventListener("change",()=>{state.benchmark.mode="auto";syncBenchUi();save();});
    manualRadio.addEventListener("change",()=>{state.benchmark.mode="manual";syncBenchUi();save();});
    preset.addEventListener("change",()=>{state.benchmark.preset=preset.value;syncBenchUi();save();});
    symbolInput.addEventListener("input",()=>{state.benchmark.symbol=symbolInput.value.trim().toUpperCase();save();});

    async function ensureIndex(){
      if(searchIndex)return searchIndex;
      if(!indexLoading)indexLoading=deps.loadDirectory().then(rows=>{searchIndex=deps.prepare(rows);return searchIndex;})
        .catch(()=>{searchIndex=deps.prepare([]);return searchIndex;});
      return indexLoading;
    }
    async function ensureAvailable(){
      if(available)return available;
      if(!availableLoading)availableLoading=deps.loadBenchmarkIndex().then(index=>{
        available=new Set((index.benchmarks||[]).filter(b=>b.available).map(b=>b.id));return available;
      }).catch(()=>{available=null;return null;});
      return availableLoading;
    }

    function renderRow(row,n){
      const card=el(list,"div",null,"tc-row");
      const head=el(card,"div",null,"tc-row-head");
      el(head,"strong","Position "+n);
      const remove=el(head,"button","Entfernen","btn secondary tc-remove");remove.type="button";
      remove.addEventListener("click",()=>{state.rows=state.rows.filter(r=>r!==row);if(!state.rows.length)state.rows.push(newRow());save();renderRows();});

      const stockWrap=el(card,"label",null,"field");el(stockWrap,"span","Aktie (Name, Ticker oder ISIN)");
      const stockInput=el(stockWrap,"input");stockInput.type="search";stockInput.autocomplete="off";
      stockInput.placeholder="z. B. Sanofi, SAP.DE";stockInput.value=row.ticker?row.ticker+(row.name?" · "+row.name:""):"";
      const suggest=el(card,"div",null,"search-suggestions tc-suggest");
      let timer=null;
      stockInput.addEventListener("input",()=>{
        clearTimeout(timer);
        timer=setTimeout(async()=>{
          const q=stockInput.value.trim();suggest.replaceChildren();
          if(q.length<2)return;
          const index=await ensureIndex();
          for(const hit of deps.find(index,q,6).items){
            const s=hit.stock,b=el(suggest,"button",(s.name||s.ticker)+" · "+s.ticker+(s.exchange?" · "+s.exchange:""),"search-suggestion");
            b.type="button";
            b.addEventListener("click",()=>{
              Object.assign(row,{ticker:s.ticker,name:s.name||"",exchange:s.exchange||"",country_code:s.country_code||"",
                reference_isin:s.reference_isin||s.tr_isin||"",buyOwn:false,sellOwn:false,buyPrice:null,sellPrice:null});
              stockInput.value=s.ticker+(s.name?" · "+s.name:"");suggest.replaceChildren();save();refreshPrices();
            });
          }
        },180);
      });

      const dates=el(card,"div",null,"tc-grid");
      const buyWrap=el(dates,"label",null,"field");el(buyWrap,"span","Kaufdatum");
      const buyInput=el(buyWrap,"input");buyInput.type="date";buyInput.value=row.buy||"";
      const sellWrap=el(dates,"label",null,"field");el(sellWrap,"span","Verkaufsdatum");
      const sellInput=el(sellWrap,"input");sellInput.type="date";sellInput.value=row.sell||"";
      const openLabel=el(card,"label",null,"tc-open");
      const openBox=el(openLabel,"input");openBox.type="checkbox";openBox.checked=!!row.open;
      el(openLabel,"span","Noch im Depot (offen, bis heute)");
      const today=new Date().toISOString().slice(0,10);
      buyInput.max=today;sellInput.max=today;

      const prices=el(card,"div",null,"tc-grid");
      const bpWrap=el(prices,"label",null,"field");const bpLabel=el(bpWrap,"span","Kaufkurs");
      const bpInput=el(bpWrap,"input");bpInput.type="number";bpInput.step="any";bpInput.min="0";bpInput.inputMode="decimal";
      const spWrap=el(prices,"label",null,"field");const spLabel=el(spWrap,"span","Verkaufskurs");
      const spInput=el(spWrap,"input");spInput.type="number";spInput.step="any";spInput.min="0";spInput.inputMode="decimal";
      const sharesWrap=el(card,"label",null,"field");el(sharesWrap,"span","Stück (optional, für Beträge in €)");
      const sharesInput=el(sharesWrap,"input");sharesInput.type="number";sharesInput.step="any";sharesInput.min="0";sharesInput.inputMode="decimal";
      sharesInput.value=finite(row.shares)?String(row.shares):"";
      const hint=el(card,"p",null,"small muted tc-hint");hint.setAttribute("aria-live","polite");

      function syncOpen(){sellInput.disabled=openBox.checked;sellWrap.classList.toggle("tc-disabled",openBox.checked);}
      syncOpen();
      if(finite(row.buyPrice))bpInput.value=String(row.buyPrice);
      if(finite(row.sellPrice))spInput.value=String(row.sellPrice);

      async function refreshPrices(){
        if(!row.ticker||!row.buy){hint.textContent=row.ticker?"Kaufdatum eintragen – der Kaufkurs wird dann vorgeschlagen.":"";return;}
        hint.textContent="Lade Kurse für "+row.ticker+" …";
        try{
          const data=await deps.loadQuote(row.ticker);
          const r=compute({...row,buyPrice:row.buyOwn?row.buyPrice:null,sellPrice:row.sellOwn?row.sellPrice:null},data,null,
            {points:data.points,currency:data.currency,name:"x"},null);
          bpLabel.textContent="Kaufkurs ("+data.currency+")";spLabel.textContent="Verkaufskurs ("+data.currency+")";
          if(r.error){hint.textContent=r.error;return;}
          // Shown rounded; the exact close is used as long as the field is not edited.
          const shown=v=>String(+v.toFixed(v<10?4:2));
          if(!row.buyOwn){row.buyPrice=r.closeBuy;bpInput.value=shown(r.closeBuy);}
          if(!row.sellOwn){row.sellPrice=r.closeSell;spInput.value=shown(r.closeSell);}
          save();
          hint.textContent=(row.buyOwn?"Kaufkurs: eigener Wert (Schlusskurs am "+date(r.buyDay)+": "+price(r.closeBuy,data.currency)+")"
              :"Kaufkurs = Schlusskurs am "+date(r.buyDay)+(r.buyDay!==row.buy?" (erster Handelstag ab "+date(row.buy)+")":""))
            +" · "+(row.sellOwn?"Verkaufskurs: eigener Wert (Schlusskurs am "+date(r.sellDay)+": "+price(r.closeSell,data.currency)+")"
              :(row.open?"Wert = letzter Schlusskurs vom ":"Verkaufskurs = Schlusskurs am ")+date(r.sellDay))
            +(r.note?" · "+r.note:"")+". Kurse überschreibbar.";
        }catch(error){hint.textContent="Kurse für "+row.ticker+" nicht abrufbar: "+String(error.message||error);}
      }
      buyInput.addEventListener("change",()=>{row.buy=buyInput.value;save();refreshPrices();});
      sellInput.addEventListener("change",()=>{row.sell=sellInput.value;save();refreshPrices();});
      openBox.addEventListener("change",()=>{row.open=openBox.checked;syncOpen();save();refreshPrices();});
      bpInput.addEventListener("input",()=>{const v=parseFloat(bpInput.value);row.buyOwn=finite(v)&&v>0;row.buyPrice=row.buyOwn?v:null;save();});
      spInput.addEventListener("input",()=>{const v=parseFloat(spInput.value);row.sellOwn=finite(v)&&v>0;row.sellPrice=row.sellOwn?v:null;save();});
      bpInput.addEventListener("change",refreshPrices);spInput.addEventListener("change",refreshPrices);
      sharesInput.addEventListener("input",()=>{const v=parseFloat(sharesInput.value);row.shares=finite(v)&&v>0?v:null;save();});
      if(row.ticker&&row.buy)refreshPrices();
    }
    function renderRows(){list.replaceChildren();state.rows.forEach((row,i)=>renderRow(row,i+1));}
    addBtn.addEventListener("click",()=>{state.rows.push(newRow());save();renderRows();
      const inputs=list.querySelectorAll(".tc-row input[type=search]");if(inputs.length)inputs[inputs.length-1].focus();});

    async function fxFor(currency){
      const pair=fxSymbol(currency);
      if(currency==="EUR")return null;
      if(!pair)throw Error("Keine EUR-Umrechnung für "+currency+".");
      const data=await deps.loadQuote(pair.symbol);
      return {points:data.points,scale:pair.scale};
    }
    async function benchmarkFor(row){
      if(state.benchmark.mode==="manual"){
        if(state.benchmark.preset==="custom"){
          const sym=(state.benchmark.symbol||"").toUpperCase();
          if(!sym)throw Error("Bitte ein Benchmark-Symbol eintragen.");
          const data=await deps.loadQuote(sym);
          return {id:sym,name:sym,symbol:sym,points:data.points,currency:data.currency};
        }
        const b=BENCHMARKS.find(x=>x.id===state.benchmark.preset)||BENCHMARKS[BENCHMARKS.length-1];
        return {...b,...await deps.loadBenchmark(b)};
      }
      const avail=await ensureAvailable();
      const b=pickBenchmark(row,avail);
      if(!b)throw Error("Kein Benchmark verfügbar.");
      return {...b,...await deps.loadBenchmark(b)};
    }

    run.addEventListener("click",async()=>{
      const rows=state.rows.filter(r=>r.ticker);
      out.replaceChildren();
      if(!rows.length){status.textContent="Bitte mindestens eine Aktie auswählen.";return;}
      run.disabled=true;status.textContent="Vergleiche "+rows.length+" Position"+(rows.length>1?"en":"")+" …";
      const results=[];
      for(const row of rows){
        let result;
        try{
          const data=await deps.loadQuote(row.ticker);
          const [fx,bench]=await Promise.all([fxFor(data.currency),benchmarkFor(row)]);
          const benchFx=await fxFor(bench.currency);
          result=compute({...row,buyPrice:row.buyOwn?row.buyPrice:null,sellPrice:row.sellOwn?row.sellPrice:null},data,fx,bench,benchFx);
          result.bench=bench;
        }catch(error){result={error:String(error.message||error)};}
        result.row=row;results.push(result);
      }
      run.disabled=false;
      const total=portfolio(results);
      status.textContent=results.filter(r=>!r.error).length+" von "+results.length+" Positionen verglichen.";
      if(total&&total.count>1){
        const box=el(out,"div",null,"tc-total "+(total.difference>=0?"tc-good":"tc-bad"));
        el(box,"h3","Alle Positionen zusammen");
        el(box,"p",(total.difference>=0?"Besser als die Benchmarks: ":"Schlechter als die Benchmarks: ")+eur(total.difference)
          +" ("+pp(total.outperformance)+" bezogen auf den Einsatz)","tc-verdict");
        el(box,"p","Einsatz "+eur(total.invested)+" → heute bzw. bei Verkauf "+eur(total.end)+" ("+pct(total.stockReturn)+") · gleiche Beträge im jeweiligen Benchmark: "
          +eur(total.bench)+" ("+pct(total.benchReturn)+")"+(total.estimatedAmounts?" · Positionen ohne Stückzahl mit je 1.000 € gerechnet.":""),"small");
      }
      for(const r of results){
        const row=r.row,card=el(out,"div",null,"tc-result "+(r.error?"":r.outperformance>=0?"tc-good":"tc-bad"));
        el(card,"h3",row.ticker+(row.name?" · "+row.name:""));
        if(r.error){el(card,"p",r.error,"small");continue;}
        el(card,"p",date(r.buyDay)+" → "+(r.open?"heute ("+date(r.sellDay)+", noch im Depot)":date(r.sellDay))+" · "+nf(r.days,0)+" Tage","small muted");
        el(card,"p",(r.outperformance>=0?"Outperformance: ":"Underperformance: ")+pp(r.outperformance),"tc-verdict");
        const grid=el(card,"div",null,"tc-figures");
        const fig=(label,value,sub)=>{const b=el(grid,"div",null,"tc-figure");el(b,"span",label,"small muted");el(b,"strong",value);if(sub)el(b,"span",sub,"small muted");};
        fig("Aktie (in EUR)",pct(r.stockEur),r.stockAnnual!==null?pct(r.stockAnnual)+" pro Jahr":"unter 1 Jahr: nicht annualisiert");
        fig(r.bench.name+" (in EUR)",pct(r.benchEur),r.benchAnnual!==null?pct(r.benchAnnual)+" pro Jahr":r.bench.symbol);
        el(card,"p","Kauf "+price(r.buyPrice,r.currency)+(r.ownBuy?" (eigener Kurs)":" (Schlusskurs)")+" · "+(r.open?"Wert ":"Verkauf ")+price(r.sellPrice,r.currency)
          +(r.ownSell?" (eigener Kurs)":" (Schlusskurs)")+(r.currency!=="EUR"?" · in Handelswährung "+pct(r.stockLocal):"")
          +(r.shares?" · Einsatz "+eur(r.invested)+" → "+eur(r.endValue)+" (Benchmark: "+eur(r.benchValue)+")":"")
          +(r.note?" · "+r.note:""),"small");
        lineChart(card,r.chart,[row.ticker,r.bench.name]);
      }
    });

    syncBenchUi();renderRows();
    return {state,refresh:renderRows};
  }

  const api={BENCHMARKS,onOrAfter,onOrBefore,fxSymbol,countryOf,pickBenchmark,compute,portfolio,create,STORAGE_KEY};
  if(typeof module!=="undefined"&&module.exports)module.exports=api;
  root.StockTradeCheck=api;
})(typeof window!=="undefined"?window:globalThis);
