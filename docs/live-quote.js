/* On-demand daily close for search hits without a stored quote.
   The optional Cloudflare worker (cloudflare/quote-worker.js) returns one
   Yahoo daily series in the docs/charts format plus "expires": until then no
   new close can exist, so the answer is reused from memory, this device's
   storage or the HTTP cache instead of being requested again. */
(function(root){
  "use strict";
  // v=4: answers of the current worker (trend/crash/ATR context and raw
  // closes). Answers stored from an older worker are neither reused nor looked up.
  const SERVICE="https://bottleneck-lab-android.markus-schuster-dev.workers.dev/quote?v=4&symbol=";
  const STORAGE_KEY="bottleneck.live-quotes.v4",MAX_STORED=20;
  // Stocks/ETFs (SAP.DE), indices (^GDAXI) and exchange rates (USDEUR=X).
  const TICKER=/^\^?[A-Z0-9][A-Z0-9.\-]{0,19}(=X)?$/;
  const memory=new Map(),pending=new Map();
  const finite=v=>typeof v==="number"&&Number.isFinite(v);

  function validate(data,ticker){
    if(!data||data.version!==1||data.ticker!==ticker||!/^[A-Za-z]{3}$/.test(data.currency||"")
       ||!/^20\d{2}-\d\d-\d\d$/.test(data.asof||"")||!finite(data.close)||data.close<=0
       ||!Array.isArray(data.points)||data.points.length<30||!Number.isFinite(Date.parse(data.expires)))
      throw Error("Ungültige Kursantwort");
    let previous="";
    for(const p of data.points){
      if(!Array.isArray(p)||p.length!==2||!/^20\d{2}-\d\d-\d\d$/.test(p[0])||p[0]<=previous||!finite(p[1])||p[1]<=0)
        throw Error("Ungültige Kursreihe");
      previous=p[0];
    }
    if(previous!==data.asof)throw Error("Kursreihe und Stichtag stimmen nicht überein");
    if(data.closes!==undefined&&(!Array.isArray(data.closes)||data.closes.length!==data.points.length||!data.closes.every(v=>finite(v)&&v>0)))
      throw Error("Ungültige Schlusskurse");
    return data;
  }
  function readStore(storage){
    try{
      const raw=JSON.parse(storage.getItem(STORAGE_KEY));
      return raw&&raw.version===1&&raw.items&&typeof raw.items==="object"?raw.items:{};
    }catch{return {};}
  }
  function writeStore(storage,items){
    try{storage.setItem(STORAGE_KEY,JSON.stringify({version:1,items}));return true;}catch{return false;}
  }
  function defaultStorage(){
    try{return root.localStorage||null;}catch{return null;}
  }
  function peek(ticker,options={}){
    const now=options.now??Date.now(),storage=options.storage===undefined?defaultStorage():options.storage;
    // A long series without context comes from an outdated worker: refetch.
    const fresh=entry=>entry&&Date.parse(entry.expires)>now&&Array.isArray(entry.closes)
      &&!(Array.isArray(entry.points)&&entry.points.length>=253&&!entry.context&&/^[A-Z0-9]/.test(entry.ticker)&&!String(entry.ticker).endsWith("=X"));
    const held=memory.get(ticker);
    if(fresh(held))return held;
    if(!storage)return null;
    const stored=readStore(storage)[ticker];
    try{
      if(fresh(stored)){validate(stored,ticker);memory.set(ticker,stored);return stored;}
    }catch{}
    return null;
  }
  function remember(data,storage,now){
    memory.set(data.ticker,data);
    if(!storage)return;
    const items=readStore(storage);
    for(const [key,entry] of Object.entries(items))
      if(!entry||!(Date.parse(entry.expires)>now))delete items[key];
    items[data.ticker]=data;
    const keys=Object.keys(items).sort((a,b)=>String(items[b].fetched||"").localeCompare(String(items[a].fetched||"")));
    for(const key of keys.slice(MAX_STORED))delete items[key];
    if(!writeStore(storage,items)){
      // Storage full or blocked: keep at least this lookup.
      writeStore(storage,{[data.ticker]:data});
    }
  }
  async function load(ticker,options={}){
    if(!TICKER.test(ticker||""))throw Error("Dieses Börsensymbol kann nicht abgefragt werden.");
    const now=options.now??Date.now(),storage=options.storage===undefined?defaultStorage():options.storage;
    const cached=peek(ticker,{now,storage});
    if(cached)return cached;
    if(pending.has(ticker))return pending.get(ticker);
    const request=(options.fetch||root.fetch)(SERVICE+encodeURIComponent(ticker))
      .then(async response=>{
        let body=null;
        try{body=await response.json();}catch{}
        if(!response.ok){
          const code=body&&typeof body.error==="string"?body.error:"HTTP "+response.status;
          throw Error(code==="upstream_429"?"Yahoo begrenzt gerade die Abfragen. Bitte später erneut versuchen."
            :code==="no_data"||code==="upstream_404"?"Yahoo hat für dieses Börsensymbol keine Tageskurse."
            :"Kurs derzeit nicht abrufbar ("+code+").");
        }
        const data=validate(body,ticker);
        remember(data,storage,now);
        return data;
      })
      .finally(()=>pending.delete(ticker));
    pending.set(ticker,request);
    return request;
  }
  // EUR reference rates: the snapshot table, else rates already attached to quoted stocks.
  function fxTable(snapshot){
    const table={};
    for(const s of (snapshot&&snapshot.stocks)||[]){
      if(s&&typeof s.currency==="string"&&finite(s.eur_per_unit)&&s.eur_per_unit>0&&!table[s.currency])
        table[s.currency]={eur_per_unit:s.eur_per_unit,fx_date:s.fx_date||null};
    }
    const listed=snapshot&&snapshot.fx_eur;
    if(listed&&typeof listed==="object"){
      for(const [currency,rate] of Object.entries(listed))
        if(rate&&finite(rate.eur_per_unit)&&rate.eur_per_unit>0)table[currency]={eur_per_unit:rate.eur_per_unit,fx_date:rate.fx_date||null};
    }
    return table;
  }
  function summary(data,fx){
    const rate=fx&&fx[data.currency];
    const p=data.points,n=p.length;
    return {
      close:data.close,currency:data.currency,asof:data.asof,expires:data.expires,fetched:data.fetched||null,
      eur:rate?data.close*rate.eur_per_unit:null,fx_date:rate?rate.fx_date:null,
      // Same definition as the pipeline: adjusted close 252 to 21 sessions ago.
      momentum_12_2:n>=253?p[n-22][1]/p[n-253][1]-1:null
    };
  }
  const round=(v,d)=>Math.round(v*10**d)/10**d;
  // Port of trade_guidance.assign_decision (same thresholds and wording keys).
  function decide(stock,market,now=Date.now()){
    const m=stock.momentum_12_2,trend=stock.sma200_ratio,r21=stock.return_21d,dd=stock.drawdown_252d;
    const price=stock.reference_close_eur,fx=stock.eur_per_unit,ref=stock.risk_reference_native;
    if(![m,trend,r21,dd,price,fx,ref].every(finite)){
      stock.entry_review="insufficient_data";stock.exit_review="insufficient_data";return stock;
    }
    const risk=market&&market.risk;
    let entry="entry_review",exit="hold_review";
    if(stock.crash_warning===true){entry="avoid_crash";exit="review_exit_crash";}
    else if(trend<0){entry="wait_downtrend";exit="review_exit_trend";}
    else if(m<=0)entry="wait_momentum";
    else if(stock.correction_warning===true)entry="wait_correction";
    else if(risk==="crash"||risk==="downtrend")entry="wait_market";
    else if(risk==null)entry="market_unverified";
    const today=Date.parse(new Date(now).toISOString().slice(0,10)+"T00:00:00Z");
    const daysOld=(today-Date.parse(stock.price_date+"T00:00:00Z"))/86400000;
    if(!(daysOld>=0&&daysOld<=4)){entry="stale_quote";exit="insufficient_data";}
    stock.entry_review=entry;stock.exit_review=exit;
    stock.risk_reference_eur=round(ref*fx,4);stock.entry_reference_eur=round(price,4);
    const close=stock.close,atr=stock.atr14_native;
    if(entry!=="stale_quote"&&finite(close)&&finite(atr)&&close>0&&atr>0
       &&String(stock.context_basis||"").startsWith("Yahoo adjusted OHLC")){
      const buy=close-atr,stop=buy-2.5*atr;
      if(stop>0&&buy>0){
        stock.model_buy_limit_eur=round(buy*fx,4);stock.model_initial_stop_eur=round(stop*fx,4);
        stock.model_limit_rule="Last close - 1 ATR(14); initial stop = limit - 2.5 ATR(14)";
      }
    }
    for(const [native,eur] of [["sma200_native","sma200_level_eur"],["crash_21_level_native","crash_21_level_eur"],["crash_peak_level_native","crash_peak_level_eur"]])
      if(finite(stock[native])&&stock[native]>0)stock[eur]=round(stock[native]*fx,4);
    return stock;
  }
  // A search hit enriched with the fetched series: price, EUR value, momentum,
  // 12-month volatility, trend/crash/ATR context and the entry/exit review.
  function enrich(stock,data,snapshot,now=Date.now()){
    const p=data.points,n=p.length,rate=fxTable(snapshot)[data.currency];
    const live={...stock,close:data.close,currency:data.currency,price_date:data.asof,source:"Yahoo Finance",
      // Stored levels belong to the old close; they are recalculated below.
      model_buy_limit_eur:undefined,model_initial_stop_eur:undefined,model_limit_rule:undefined,
      live_quote:{fetched:data.fetched||null,expires:data.expires},
      momentum_12_2:n>=253?p[n-22][1]/p[n-253][1]-1:null,
      momentum_basis:"Yahoo adjusted daily closes",momentum_skip_sessions:21,
      avg_local_turnover_20d:finite(data.turnover)?data.turnover:null,...(data.context||{})};
    if(n>=253){
      const r=[];for(let i=n-252;i<n;i++)r.push(Math.log(p[i][1]/p[i-1][1]));
      const mean=r.reduce((a,b)=>a+b,0)/r.length;
      const sd=Math.sqrt(r.reduce((a,b)=>a+(b-mean)**2,0)/(r.length-1));
      if(finite(sd)){live.volatility_252d=round(sd*Math.sqrt(252),8);live.long_risk_basis="Yahoo adjusted log returns; 252 sessions; annualised sqrt(252)";}
    }
    if(rate){
      live.eur_per_unit=rate.eur_per_unit;live.fx_date=rate.fx_date;
      live.reference_close_eur=round(data.close*rate.eur_per_unit,6);
      if(finite(live.avg_local_turnover_20d))live.avg_turnover_20d_eur=round(live.avg_local_turnover_20d*rate.eur_per_unit,2);
    }
    return decide(live,snapshot&&snapshot.market_context,now);
  }
  function clear(){memory.clear();pending.clear();}
  const api={service:SERVICE,storageKey:STORAGE_KEY,validate,peek,load,fxTable,summary,decide,enrich,clear};
  if(typeof module!=="undefined"&&module.exports)module.exports=api;
  root.StockLiveQuote=api;
})(typeof window!=="undefined"?window:globalThis);
