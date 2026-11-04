/* On-demand daily close for search hits without a stored quote.
   The optional Cloudflare worker (cloudflare/quote-worker.js) returns one
   Yahoo daily series in the docs/charts format plus "expires": until then no
   new close can exist, so the answer is reused from memory, this device's
   storage or the HTTP cache instead of being requested again. */
(function(root){
  "use strict";
  const SERVICE="https://bottleneck-lab-android.markus-schuster-dev.workers.dev/quote?symbol=";
  const STORAGE_KEY="bottleneck.live-quotes.v1",MAX_STORED=12;
  const TICKER=/^[A-Z0-9][A-Z0-9.\-]{0,19}$/;
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
    const fresh=entry=>entry&&Date.parse(entry.expires)>now;
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
  function clear(){memory.clear();pending.clear();}
  const api={service:SERVICE,storageKey:STORAGE_KEY,validate,peek,load,fxTable,summary,clear};
  if(typeof module!=="undefined"&&module.exports)module.exports=api;
  root.StockLiveQuote=api;
})(typeof window!=="undefined"?window:globalThis);
