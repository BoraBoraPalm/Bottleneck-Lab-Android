/* Depot-Check: eigene Käufe und Verkäufe gegen einen passenden Benchmark.

   Rechnung: Gesamtrendite aus bereinigten Tagesschlusskursen (inkl. Dividenden
   und Splits), in EUR umgerechnet mit historischen Wechselkursen. Eigene Kauf-
   oder Verkaufskurse ersetzen den Schlusskurs des jeweiligen Tages; Dividenden
   und Splits bleiben dabei berücksichtigt:
     Rendite = bereinigte Rendite × (eigener Verkaufskurs / Schlusskurs Verkaufstag)
                                  ÷ (eigener Kaufkurs / Schlusskurs Kauftag).
   Schlusskurse sind splitbereinigt; eigene Kurse dürfen auch "wie damals
   gehandelt" (vor einem späteren Split) sein – die nähere Form wird erkannt.
   Dividendensteuer (Option): jede Ausschüttung ist im Verhältnis bereinigter
   zu unbereinigtem Kurs sichtbar (Rendite y am Ex-Tag); mit Steuersatz s wird
   nur y·(1−s) wieder angelegt: Faktor (1−y)/(1−y·(1−s)) je Ausschüttung.
   Benchmark: dieselben Tage, ebenfalls inkl. Ausschüttungen und in EUR; als
   Index (Standard) = ETF plus dessen laufende Kosten, sonst der ETF selbst.
   Ordergebühren (Option): Einsatz = Kaufbetrag + Kaufgebühr; Endwert minus
   Verkaufsgebühr (nur bei verkauften Positionen); beim ETF ebenso. */
(function(root){
  "use strict";
  const STORAGE_KEY="bottleneck.trade-check.v1";
  const DAY=86400000;
  const finite=v=>typeof v==="number"&&Number.isFinite(v);
  const ISO=/^\d{4}-\d{2}-\d{2}$/;

  // Same list as scripts/benchmarks.py (checked by tests/test_benchmarks.py).
  const EUROPE=["AT","BE","CH","CZ","DK","ES","FI","FR","GR","HU","IE","IS","IT","LU","NL","NO","PL","PT","RO","SE"];
  const EMERGING=["AE","BR","CL","CO","EG","ID","KW","MX","MY","PE","PH","QA","SA","TH","TR","ZA"];
  // symbol/ter: first ETF of the Python list; the data run may choose the next
  // candidate (benchmarks/index.json), which then takes precedence. ter in % p. a.
  const BENCHMARKS=[
    {id:"SPY",symbol:"SPY",ter:0.0945,name:"S&P 500",markets:["US"]},
    {id:"DAX",symbol:"EL4F.DE",ter:0.15,name:"DAX",markets:["DE"]},
    {id:"STOXX600",symbol:"EXSA.DE",ter:0.2,name:"STOXX Europe 600",markets:EUROPE},
    {id:"FTSE100",symbol:"ISF.L",ter:0.07,name:"FTSE 100",markets:["GB"]},
    {id:"TSX60",symbol:"XIU.TO",ter:0.17,name:"S&P/TSX 60",markets:["CA"]},
    {id:"TOPIX",symbol:"1306.T",ter:0.0822,name:"TOPIX",markets:["JP"]},
    {id:"HSI",symbol:"2800.HK",ter:0.06,name:"Hang Seng",markets:["HK"]},
    {id:"ASX200",symbol:"STW.AX",ter:0.05,name:"S&P/ASX 200",markets:["AU","NZ"]},
    {id:"KOSPI200",symbol:"069500.KS",ter:0.15,name:"KOSPI 200",markets:["KR"]},
    {id:"TW50",symbol:"0050.TW",ter:0.13,name:"Taiwan 50",markets:["TW"]},
    {id:"NIFTY50",symbol:"NIFTYBEES.NS",ter:0.04,name:"Nifty 50",markets:["IN"]},
    {id:"CSI300",symbol:"510300.SS",ter:0.2,name:"CSI 300",markets:["CN"]},
    {id:"EM",symbol:"EEM",ter:0.72,name:"MSCI Emerging Markets",markets:EMERGING},
    {id:"WORLD",symbol:"IWDA.AS",ter:0.2,name:"MSCI World",markets:[]},
    {id:"ACWI",symbol:"ACWI",ter:0.32,name:"MSCI ACWI (Welt)",markets:["*"]}
  ];
  const KEST=.275; // österreichische Kapitalertragsteuer auf Dividenden
  // Yahoo symbols of indices that include dividends; other ^ symbols are mostly price indices.
  const PERFORMANCE_INDICES=["^GDAXI","^MDAXI","^SDAXI","^TECDAX","^SP500TR"];
  function indexWarning(symbol){
    const sym=String(symbol||"").toUpperCase();
    if(!sym.startsWith("^"))return null;
    if(PERFORMANCE_INDICES.includes(sym))return "Performanceindex: Dividenden sind enthalten, Fondskosten nicht.";
    return "Achtung: Die meisten ^-Symbole sind Kursindizes ohne Dividenden (z. B. ^GSPC, ^STOXX50E, ^ATX). Der Benchmark wird dann um die Dividendenrendite zu schwach gerechnet – besser einen ETF nehmen (z. B. VWCE.DE) oder ein Symbol mit Dividenden wie ^SP500TR.";
  }
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

  // Payouts are visible as a jump of adjusted/raw close on the ex-day (yield y).
  // With dividend tax only y·(1−rate) is reinvested. cum[t]: factor up to day t.
  const MIN_YIELD=1e-4,MAX_YIELD=.9;
  function taxPath(points,closes,rate){
    const n=points.length,cum=new Float64Array(n),events=[];
    const usable=rate>0&&Array.isArray(closes)&&closes.length===n;
    if(n)cum[0]=1;
    for(let t=1;t<n;t++){
      cum[t]=cum[t-1];
      if(!usable)continue;
      const before=points[t-1][1]/closes[t-1],now=points[t][1]/closes[t];
      if(!(now>0&&before>0))continue;
      const y=1-before/now;
      if(y>=MIN_YIELD&&y<MAX_YIELD){cum[t]*=(1-y)/(1-y*(1-rate));events.push(t);}
    }
    return {cum,events,usable};
  }
  const validSplits=stock=>Array.isArray(stock&&stock.splits)
    ?stock.splits.filter(x=>Array.isArray(x)&&ISO.test(x[0])&&finite(x[1])&&x[1]>0&&x[1]!==1):[];
  // Splits after a day: Yahoo's closes are split-adjusted, × factor = price as traded then.
  const splitFactorAfter=(splits,day)=>splits.reduce((f,x)=>x[0]>day?f*x[1]:f,1);
  // An own price may be given as traded then or split-adjusted: the nearer form wins.
  function ownToAdjusted(own,close,factor){
    if(factor===1)return {value:own,traded:false};
    const traded=Math.abs(Math.log(own/(close*factor)))<Math.abs(Math.log(own/close));
    return {value:traded?own/factor:own,traded};
  }

  /* input: {buy, sell, open, buyPrice, sellPrice, shares, buyFee, sellFee (EUR)}
     stock: {points, closes, splits, currency}; fx/benchFx: {points, scale} or null (EUR)
     bench: {points, closes, currency, name, ter (% p. a.)}
     options: {taxRate (0–1), index (ETF + TER), benchFees (fees also for the benchmark)} */
  function compute(input,stock,fx,bench,benchFx,options={}){
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
    const splits=validSplits(stock),fB=splitFactorAfter(splits,buyDay),fS=splitFactorAfter(splits,sellDay);
    const tradedB=rawB*fB,tradedS=rawS*fS;
    const ownBuy=finite(input.buyPrice)&&input.buyPrice>0,ownSell=finite(input.sellPrice)&&input.sellPrice>0;
    const b=ownBuy?ownToAdjusted(input.buyPrice,rawB,fB):{value:rawB,traded:fB!==1};
    const sv=ownSell?ownToAdjusted(input.sellPrice,rawS,fS):{value:rawS,traded:fS!==1};
    const buyPrice=ownBuy?input.buyPrice:tradedB,sellPrice=ownSell?input.sellPrice:tradedS;
    const rate=finite(options.taxRate)&&options.taxRate>0&&options.taxRate<1?options.taxRate:0;
    const tax=taxPath(P,C,rate),taxStock=tax.cum[is]/tax.cum[ib];
    const priceLocal=P[is][1]/P[ib][1]*(sv.value/rawS)/(b.value/rawB);
    const local=priceLocal*taxStock-1;
    const fxB=fx?valueAt(fx,buyDay):1,fxS=fx?valueAt(fx,sellDay):1;
    if(!(fxB>0&&fxS>0))return {error:"Wechselkurs "+stock.currency+"/EUR für diesen Zeitraum nicht verfügbar."};
    const stockBeforeTax=priceLocal*(fxS/fxB)-1,stockTaxed=(1+local)*(fxS/fxB)-1;
    if(!bench||!Array.isArray(bench.points)||!bench.points.length)return {error:"Keine Benchmark-Kursreihe."};
    const B=bench.points,jb=onOrBefore(B,buyDay),js=onOrBefore(B,sellDay);
    if(jb<0)return {error:"Die Benchmark-Reihe ("+(bench.name||"Benchmark")+") beginnt erst am "+B[0][0]+"."};
    const bfB=benchFx?valueAt(benchFx,B[jb][0]):1,bfS=benchFx?valueAt(benchFx,B[js][0]):1;
    if(!(bfB>0&&bfS>0))return {error:"Wechselkurs "+bench.currency+"/EUR für den Benchmark nicht verfügbar."};
    const bTax=taxPath(B,bench.closes,rate),taxBench=bTax.cum[js]/bTax.cum[jb];
    const ter=options.index&&finite(bench.ter)&&bench.ter>0?bench.ter/100:0;
    const terFactor=d=>ter?Math.pow(1+ter,daysBetween(B[jb][0],d)/365.25):1;
    const benchBeforeTax=B[js][1]/B[jb][1]*terFactor(B[js][0])*(bfS/bfB)-1;
    const benchTaxed=(1+benchBeforeTax)*taxBench-1;
    const days=daysBetween(buyDay,sellDay);
    const shares=finite(input.shares)&&input.shares>0?input.shares:null;
    const fee=v=>finite(v)&&v>0?v:0;
    const buyFee=fee(input.buyFee),sellFee=input.open?0:fee(input.sellFee);
    // Without shares every position counts as 1,000 EUR including the buy fee.
    const invested=shares?buyPrice*shares*fxB+buyFee:1000,base=invested-buyFee;
    if(!(base>0))return {error:"Die Ordergebühren sind höher als der Einsatz."};
    const benchFees=!!options.benchFees;
    const endValue=base*(1+stockTaxed)-sellFee;
    const benchValue=(benchFees?base:invested)*(1+benchTaxed)-(benchFees?sellFee:0);
    const stockEur=endValue/invested-1,benchEur=benchValue/invested-1;
    // Time course (100 = buy day; with tax and index costs, without order fees), at most ~240 points.
    const step=Math.max(1,Math.ceil((is-ib+1)/240)),chart=[];
    const stockAt=(t,sf)=>100*P[t][1]/P[ib][1]*tax.cum[t]/tax.cum[ib]*sf/fxB;
    const benchAt=(k,bf)=>k>=0?100*B[k][1]/B[jb][1]*bTax.cum[k]/bTax.cum[jb]*terFactor(B[k][0])*bf/bfB:null;
    for(let t=ib;t<=is;t+=step){
      const d=P[t][0];
      chart.push([d,stockAt(t,fx?valueAt(fx,d):1),benchAt(onOrBefore(B,d),benchFx?valueAt(benchFx,d):1)]);
    }
    if(chart[chart.length-1][0]!==sellDay)chart.push([sellDay,stockAt(is,fxS),benchAt(js,benchFx?valueAt(benchFx,sellDay):1)]);
    const within=(events,a,z)=>events.filter(t=>t>a&&t<=z).length;
    return {
      buyDay,sellDay,open:!!input.open,days,currency:stock.currency,note,
      closeBuy:tradedB,closeSell:tradedS,buyPrice,sellPrice,ownBuy,ownSell,
      buyTraded:ownBuy&&b.traded,sellTraded:ownSell&&sv.traded,
      splits:splits.filter(x=>x[0]>buyDay&&x[0]<=sellDay),splitsAfterBuy:splits.filter(x=>x[0]>buyDay),
      buyEur:buyPrice*fxB,sellEur:sellPrice*fxS,shares,invested,
      stockLocal:local,stockEur,benchEur,outperformance:stockEur-benchEur,
      stockAnnual:annual(stockEur,days),benchAnnual:annual(benchEur,days),
      endValue,benchValue,
      fees:{buy:buyFee,sell:sellFee,bench:benchFees},
      tax:rate?{rate,stockEvents:within(tax.events,ib,is),stockDrag:stockBeforeTax-stockTaxed,
        benchApplied:bTax.usable,benchEvents:within(bTax.events,jb,js),benchDrag:benchBeforeTax-benchTaxed}:null,
      index:ter?{ter}:null,
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
    try{storage.setItem(STORAGE_KEY,JSON.stringify({version:1,rows:state.rows,benchmark:state.benchmark,options:state.options}));}catch{}
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
    buy:"",sell:"",open:false,buyPrice:null,sellPrice:null,buyOwn:false,sellOwn:false,shares:null,buyFee:null,sellFee:null});
  const splitText=f=>f>=1?nf(f,f%1?2:0)+":1":"1:"+nf(1/f,(1/f)%1?2:0);

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
      benchmark:saved&&saved.benchmark?saved.benchmark:{mode:"auto",preset:"ACWI",symbol:""},
      options:{etf:false,fees:false,fee:1,tax:false,...(saved&&saved.options||{})}};
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
    const symbolWarn=el(bench,"p",null,"small tc-warn");
    const etfLabel=el(bench,"label",null,"tc-open");
    const etfBox=el(etfLabel,"input");etfBox.type="checkbox";
    el(etfLabel,"span","Als ETF mit Kosten rechnen (statt Index)");
    el(bench,"p","Ohne Haken: der Index ohne Fondskosten. Mit Haken: der passende ETF, wie du ihn kaufen könntest – laufende Kosten (TER) stecken im Kurs, Ordergebühren wie bei deinen Aktien.","small muted");

    const costs=el(container,"fieldset",null,"tc-bench");
    el(costs,"legend","Kosten & Steuern");
    const feeLabel=el(costs,"label",null,"tc-open");
    const feeBox=el(feeLabel,"input");feeBox.type="checkbox";
    el(feeLabel,"span","Ordergebühren einrechnen");
    const feeWrap=el(costs,"label",null,"field");el(feeWrap,"span","Gebühr je Order (€), bei jeder Position änderbar");
    const feeInput=el(feeWrap,"input");feeInput.type="number";feeInput.step="any";feeInput.min="0";feeInput.inputMode="decimal";
    const feeNote=el(costs,"p","Kauf immer, Verkauf nur, wenn die Position nicht mehr im Depot ist.","small muted");
    const taxLabel=el(costs,"label",null,"tc-open");
    const taxBox=el(taxLabel,"input");taxBox.type="checkbox";
    el(taxLabel,"span","Dividenden nach österreichischer KESt (27,5 %)");
    const taxNote=el(costs,"p","Von jeder Dividende und jeder ETF-Ausschüttung gehen 27,5 % ab, bevor der Rest wieder angelegt wird. Annahme: ausländische Quellensteuer wird angerechnet bzw. zurückgeholt.","small muted");

    const run=el(container,"button","Mit Benchmark vergleichen","btn tc-run");run.type="button";
    const status=el(container,"p",null,"small muted tc-status");status.setAttribute("role","status");status.setAttribute("aria-live","polite");
    const out=el(container,"div",null,"tc-results");
    const info=el(container,"details",null,"tc-info");
    el(info,"summary","So wird gerechnet");
    for(const text of [
      "Rendite: Tagesschlusskurse von Yahoo Finance, bereinigt um Dividenden und Splits (Dividenden gelten als am Ex-Tag wieder angelegt), umgerechnet in EUR mit historischen Wechselkursen. Kauf am ersten Handelstag ab dem Kaufdatum, Verkauf am ersten Handelstag ab dem Verkaufsdatum; bei „noch im Depot“ der letzte Schlusskurs.",
      "Eigene Kurse ersetzen den Schlusskurs des jeweiligen Tages; Dividenden und Splits werden weiter berücksichtigt. Nach einem Aktiensplit werden Kurse so vorgeschlagen, wie sie damals gehandelt wurden; ein eigener Kurs wird in beiden Formen (vor oder nach dem Split) erkannt. Stückzahl bitte in derselben Form.",
      "Benchmark: je Markt ein breiter ETF inklusive Ausschüttungen. Standard ist der Index ohne Fondskosten, geschätzt als Wertentwicklung dieses ETF plus seine laufenden Kosten (TER); kleine Abweichungen zum echten Index (Tracking-Differenz) sind möglich. „Als ETF mit Kosten“ nimmt den ETF selbst: die laufenden Kosten stecken im Kurs, Ordergebühren gelten wie bei der Aktie. Verglichen werden dieselben Tage.",
      "Ordergebühren (optional): Der Einsatz enthält die Kaufgebühr, vom Endwert geht die Verkaufsgebühr ab (nur bei verkauften Positionen). Ohne Stückzahl rechnet jede Position mit 1.000 € inklusive Kaufgebühr.",
      "Dividendensteuer (optional): Von jeder Dividende bzw. Ausschüttung gehen 27,5 % KESt ab, der Rest wird wieder angelegt – bei der Aktie und beim Benchmark. Ausländische Quellensteuer gilt als angerechnet bzw. erstattet; ohne Erstattung wäre die Belastung höher (z. B. Schweiz, Deutschland). Thesaurierende ETFs zeigen keine Ausschüttungen; die Steuer auf ausschüttungsgleiche Erträge ist dort nicht abgezogen. Steuern auf Kursgewinne sind nicht enthalten – sie treffen Aktie und Benchmark gleich.",
      "Bei mehreren Positionen zeigt die Summe, was aus demselben Geld zu denselben Zeitpunkten im jeweiligen Benchmark geworden wäre. Vergangene Wertentwicklung ist keine Prognose."])el(info,"p",text,"small muted");

    function syncBenchUi(){
      autoRadio.checked=state.benchmark.mode!=="manual";manualRadio.checked=state.benchmark.mode==="manual";
      preset.value=state.benchmark.preset||"ACWI";symbolInput.value=state.benchmark.symbol||"";
      manualBox.hidden=state.benchmark.mode!=="manual";symbolWrap.hidden=preset.value!=="custom";
      const warning=state.benchmark.mode==="manual"&&preset.value==="custom"?indexWarning(symbolInput.value.trim()):null;
      symbolWarn.textContent=warning||"";symbolWarn.hidden=!warning;
      etfBox.checked=!!state.options.etf;feeBox.checked=!!state.options.fees;taxBox.checked=!!state.options.tax;
      feeInput.value=finite(state.options.fee)?String(state.options.fee):"";
      feeWrap.hidden=feeNote.hidden=!state.options.fees;taxNote.hidden=!state.options.tax;
    }
    autoRadio.addEventListener("change",()=>{state.benchmark.mode="auto";syncBenchUi();save();});
    manualRadio.addEventListener("change",()=>{state.benchmark.mode="manual";syncBenchUi();save();});
    preset.addEventListener("change",()=>{state.benchmark.preset=preset.value;syncBenchUi();save();});
    symbolInput.addEventListener("input",()=>{state.benchmark.symbol=symbolInput.value.trim().toUpperCase();syncBenchUi();save();});
    etfBox.addEventListener("change",()=>{state.options.etf=etfBox.checked;save();});
    taxBox.addEventListener("change",()=>{state.options.tax=taxBox.checked;syncBenchUi();save();});
    feeBox.addEventListener("change",()=>{state.options.fees=feeBox.checked;syncBenchUi();save();renderRows();});
    feeInput.addEventListener("input",()=>{
      const v=parseFloat(feeInput.value);state.options.fee=finite(v)&&v>=0?v:0;save();
      for(const input of list.querySelectorAll(".tc-fee"))input.placeholder=nf(state.options.fee,2);
    });

    async function ensureIndex(){
      if(searchIndex)return searchIndex;
      if(!indexLoading)indexLoading=deps.loadDirectory().then(rows=>{searchIndex=deps.prepare(rows);return searchIndex;})
        .catch(()=>{searchIndex=deps.prepare([]);return searchIndex;});
      return indexLoading;
    }
    async function ensureAvailable(){
      if(available)return available;
      if(!availableLoading)availableLoading=deps.loadBenchmarkIndex().then(index=>{
        available=new Map((index.benchmarks||[]).filter(b=>b.available).map(b=>[b.id,b]));return available;
      }).catch(()=>{available=null;return null;});
      return availableLoading;
    }
    // ETF chosen by the data run (symbol, TER) overrides the default of the list.
    function withIndex(b){
      const e=available&&available.get(b.id);
      return e?{...b,symbol:e.symbol||b.symbol,ter:finite(e.ter_percent)?e.ter_percent:b.ter,detail:e.detail||""}:b;
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
      let sellFeeInput=null;
      if(state.options.fees){
        const fees=el(card,"div",null,"tc-grid");
        const feeField=(label,key)=>{
          const wrap=el(fees,"label",null,"field");el(wrap,"span",label);
          const input=el(wrap,"input","","tc-fee");input.type="number";input.step="any";input.min="0";input.inputMode="decimal";
          input.placeholder=nf(state.options.fee,2);input.value=finite(row[key])?String(row[key]):"";
          input.addEventListener("input",()=>{const v=parseFloat(input.value);row[key]=finite(v)&&v>=0?v:null;save();});
          return input;
        };
        feeField("Kaufgebühr (€)","buyFee");sellFeeInput=feeField("Verkaufsgebühr (€)","sellFee");
      }
      const hint=el(card,"p",null,"small muted tc-hint");hint.setAttribute("aria-live","polite");

      function syncOpen(){
        sellInput.disabled=openBox.checked;sellWrap.classList.toggle("tc-disabled",openBox.checked);
        if(sellFeeInput)sellFeeInput.disabled=openBox.checked;
      }
      syncOpen();
      // Suggested closes are shown rounded (the exact close is used while the field is unedited).
      const shown=(v,own)=>own?String(v):String(+v.toFixed(v<10?4:2));
      if(finite(row.buyPrice))bpInput.value=shown(row.buyPrice,row.buyOwn);
      if(finite(row.sellPrice))spInput.value=shown(row.sellPrice,row.sellOwn);

      async function refreshPrices(){
        if(!row.ticker||!row.buy){hint.textContent=row.ticker?"Kaufdatum eintragen – der Kaufkurs wird dann vorgeschlagen.":"";return;}
        hint.textContent="Lade Kurse für "+row.ticker+" …";
        try{
          const data=await deps.loadQuote(row.ticker);
          const r=compute({...row,buyPrice:row.buyOwn?row.buyPrice:null,sellPrice:row.sellOwn?row.sellPrice:null},data,null,
            {points:data.points,currency:data.currency,name:"x"},null);
          bpLabel.textContent="Kaufkurs ("+data.currency+")";spLabel.textContent="Verkaufskurs ("+data.currency+")";
          if(r.error){hint.textContent=r.error;return;}
          if(!row.buyOwn){row.buyPrice=r.closeBuy;bpInput.value=shown(r.closeBuy);}
          if(!row.sellOwn){row.sellPrice=r.closeSell;spInput.value=shown(r.closeSell);}
          save();
          hint.textContent=(row.buyOwn?"Kaufkurs: eigener Wert (Schlusskurs am "+date(r.buyDay)+": "+price(r.closeBuy,data.currency)+")"
              :"Kaufkurs = Schlusskurs am "+date(r.buyDay)+(r.buyDay!==row.buy?" (erster Handelstag ab "+date(row.buy)+")":""))
            +" · "+(row.sellOwn?"Verkaufskurs: eigener Wert (Schlusskurs am "+date(r.sellDay)+": "+price(r.closeSell,data.currency)+")"
              :(row.open?"Wert = letzter Schlusskurs vom ":"Verkaufskurs = Schlusskurs am ")+date(r.sellDay))
            +(r.note?" · "+r.note:"")+". Kurse überschreibbar."
            +(r.splitsAfterBuy.length?" Split "+r.splitsAfterBuy.map(x=>splitText(x[1])+" am "+date(x[0])).join(", ")
              +": Kurse davor wie damals gehandelt – Kurs und Stückzahl bitte beide wie beim Kauf (oder beide wie heute im Depot).":"");
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
          return {id:sym,name:sym,symbol:sym,custom:true,points:data.points,closes:data.closes,currency:data.currency};
        }
        await ensureAvailable();
        const b=withIndex(BENCHMARKS.find(x=>x.id===state.benchmark.preset)||BENCHMARKS[BENCHMARKS.length-1]);
        return {...b,...await deps.loadBenchmark(b)};
      }
      const avail=await ensureAvailable();
      const b=pickBenchmark(row,avail?new Set(avail.keys()):null);
      if(!b)throw Error("Kein Benchmark verfügbar.");
      const chosen=withIndex(b);
      return {...chosen,...await deps.loadBenchmark(chosen)};
    }

    run.addEventListener("click",async()=>{
      const rows=state.rows.filter(r=>r.ticker);
      out.replaceChildren();
      if(!rows.length){status.textContent="Bitte mindestens eine Aktie auswählen.";return;}
      run.disabled=true;status.textContent="Vergleiche "+rows.length+" Position"+(rows.length>1?"en":"")+" …";
      const results=[],opt=state.options;
      const feesFor=row=>opt.fees?{buyFee:finite(row.buyFee)?row.buyFee:opt.fee,sellFee:finite(row.sellFee)?row.sellFee:opt.fee}:{buyFee:0,sellFee:0};
      for(const row of rows){
        let result;
        try{
          const data=await deps.loadQuote(row.ticker);
          const [fx,bench]=await Promise.all([fxFor(data.currency),benchmarkFor(row)]);
          const benchFx=await fxFor(bench.currency);
          const isIndexSymbol=bench.custom&&String(bench.symbol).startsWith("^");
          result=compute({...row,...feesFor(row),buyPrice:row.buyOwn?row.buyPrice:null,sellPrice:row.sellOwn?row.sellPrice:null},
            data,fx,bench,benchFx,{taxRate:opt.tax?KEST:0,index:!opt.etf,benchFees:!!opt.etf&&!!opt.fees&&!isIndexSymbol});
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
        const bench=r.bench,benchLabel=bench.custom?bench.symbol:r.index?bench.name+" (Index)":bench.name+" (ETF "+bench.symbol+")";
        fig("Aktie (in EUR)",pct(r.stockEur),r.stockAnnual!==null?pct(r.stockAnnual)+" pro Jahr":"unter 1 Jahr: nicht annualisiert");
        fig(benchLabel+" in EUR",pct(r.benchEur),r.benchAnnual!==null?pct(r.benchAnnual)+" pro Jahr":"unter 1 Jahr: nicht annualisiert");
        el(card,"p","Kauf "+price(r.buyPrice,r.currency)+(r.ownBuy?" (eigener Kurs)":" (Schlusskurs)")+" · "+(r.open?"Wert ":"Verkauf ")+price(r.sellPrice,r.currency)
          +(r.ownSell?" (eigener Kurs)":" (Schlusskurs)")+(r.currency!=="EUR"?" · in Handelswährung "+pct(r.stockLocal):"")
          +(r.shares?" · Einsatz "+eur(r.invested)+" → "+eur(r.endValue)+" (Benchmark: "+eur(r.benchValue)+")":"")
          +(r.note?" · "+r.note:""),"small");
        const details=[];
        const drag=v=>(v>=0?"−":"+")+nf(Math.abs(v)*100,2)+" Prozentpunkte";
        const count=(n,one,many)=>nf(n,0)+" "+(n===1?one:many);
        if(r.fees.buy||r.fees.sell)details.push("Ordergebühren: Kauf "+eur(r.fees.buy)+(r.open?"":" · Verkauf "+eur(r.fees.sell))
          +(r.fees.bench?" – beim Benchmark-ETF ebenso.":" – beim Index keine."));
        if(r.tax)details.push("KESt auf Dividenden: Aktie "+(r.tax.stockEvents?drag(r.tax.stockDrag)+" ("+count(r.tax.stockEvents,"Dividende","Dividenden")+")":"keine Dividenden im Zeitraum")
          +" · Benchmark "+(!r.tax.benchApplied?"Ausschüttungen nicht erkennbar – nicht abgezogen"
            :r.tax.benchEvents?drag(r.tax.benchDrag)+" ("+count(r.tax.benchEvents,"Ausschüttung","Ausschüttungen")+")"
            :"keine Ausschüttungen im Zeitraum (thesaurierend: ausschüttungsgleiche Erträge nicht berücksichtigt)"));
        if(r.index)details.push("Index geschätzt: ETF "+bench.symbol+" plus "+nf(r.index.ter*100,2)+" % laufende Kosten pro Jahr.");
        else if(!bench.custom&&finite(bench.ter))details.push((bench.detail||"ETF "+bench.symbol)+" · laufende Kosten "+nf(bench.ter,2)+" % pro Jahr (im Kurs enthalten).");
        else if(bench.custom)details.push(indexWarning(bench.symbol)||"Eigenes Symbol: Kursreihe wie geliefert (inkl. Ausschüttungen, ohne Kostenzuschlag).");
        if(r.splits.length)details.push("Split "+r.splits.map(x=>splitText(x[1])+" am "+date(x[0])).join(", ")+" berücksichtigt"
          +(r.buyTraded?"; dein Kaufkurs wurde als Kurs vor dem Split erkannt":"")+".");
        for(const text of details)el(card,"p",text,"small muted");
        lineChart(card,r.chart,[row.ticker,bench.custom?bench.symbol:bench.name]);
      }
    });

    syncBenchUi();renderRows();
    return {state,refresh:renderRows};
  }

  const api={BENCHMARKS,KEST,onOrAfter,onOrBefore,fxSymbol,countryOf,pickBenchmark,taxPath,indexWarning,compute,portfolio,create,STORAGE_KEY};
  if(typeof module!=="undefined"&&module.exports)module.exports=api;
  root.StockTradeCheck=api;
})(typeof window!=="undefined"?window:globalThis);
