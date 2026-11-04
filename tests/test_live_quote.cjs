"use strict";
// On-demand search quotes: validation, reuse until expiry, storage limits,
// EUR conversion and the card wiring. No network.
const assert=require("node:assert/strict");
const fs=require("node:fs");
const live=require("../docs/live-quote.js");
const charts=require("../docs/chart-widget.js");

function series(ticker,{days=300,expires="2026-11-05T17:00:00Z",currency="EUR"}={}){
  const points=[];
  const start=Date.UTC(2025,0,1);
  for(let i=0;i<days;i++)points.push([new Date(start+i*86400000).toISOString().slice(0,10),100+i]);
  return {version:1,ticker,currency,asof:points.at(-1)[0],close:points.at(-1)[1],source:"Yahoo Finance",
    basis:"adjusted close normalized to latest raw close",live:true,fetched:"2026-11-04T10:00:00Z",expires,max_age:3600,points};
}
function memoryStorage(){
  const map=new Map();
  return {map,getItem:k=>map.has(k)?map.get(k):null,setItem:(k,v)=>map.set(k,String(v))};
}
const now=Date.parse("2026-11-04T12:00:00Z");

(async()=>{
  // Valid answer is accepted and matches the chart format.
  const good=series("SAN.PA");
  assert.equal(live.validate(good,"SAN.PA"),good);
  assert.equal(charts.checkedData(good,"SAN.PA").points.length,300,"Chart widget accepts the same series");
  for(const broken of [{...good,ticker:"OTHER"},{...good,version:2},{...good,currency:"EURO"},{...good,close:-1},
      {...good,expires:"never"},{...good,asof:"2026-01-01"},{...good,points:good.points.slice(0,10)},
      {...good,points:[...good.points.slice(0,-1),[good.points.at(-3)[0],5]]}])
    assert.throws(()=>live.validate(broken,"SAN.PA"));

  // One network request; afterwards memory and device storage answer until expiry.
  live.clear();
  const storage=memoryStorage();let calls=0;
  const fetch=async url=>{calls++;assert.equal(url,live.service+"SAN.PA");
    return {ok:true,status:200,json:async()=>series("SAN.PA")};};
  const first=await live.load("SAN.PA",{fetch,storage,now});
  assert.equal(first.close,399);assert.equal(calls,1);
  await live.load("SAN.PA",{fetch,storage,now});assert.equal(calls,1,"memory reuse");
  live.clear();
  await live.load("SAN.PA",{fetch,storage,now});assert.equal(calls,1,"device storage reuse after reload");
  assert.ok(live.peek("SAN.PA",{storage,now}));
  // After expiry a new request is made.
  live.clear();
  await live.load("SAN.PA",{fetch,storage,now:Date.parse("2026-11-05T18:00:00Z")});assert.equal(calls,2);
  // Parallel requests for the same stock share one network call.
  live.clear();calls=0;
  await Promise.all([live.load("SAN.PA",{fetch,storage:null,now}),live.load("SAN.PA",{fetch,storage:null,now})]);
  assert.equal(calls,1);

  // Storage keeps at most twelve lookups and survives blocked storage.
  live.clear();
  const many=memoryStorage();
  for(let i=0;i<15;i++){
    const t="T"+i;
    await live.load(t,{storage:many,now,fetch:async()=>({ok:true,status:200,json:async()=>({...series(t),fetched:"2026-11-04T10:"+String(i).padStart(2,"0")+":00Z"})})});
  }
  const kept=Object.keys(JSON.parse(many.map.get(live.storageKey)).items);
  assert.equal(kept.length,12);assert.ok(!kept.includes("T0")&&kept.includes("T14"),"oldest lookups are dropped");
  const blocked={getItem(){throw Error("blocked")},setItem(){throw Error("blocked")}};
  live.clear();
  assert.equal((await live.load("BLK.DE",{storage:blocked,now,fetch:async()=>({ok:true,status:200,json:async()=>series("BLK.DE")})})).ticker,"BLK.DE");

  // Errors are explained and never stored.
  live.clear();
  const errStorage=memoryStorage();
  await assert.rejects(live.load("SAP.DE",{storage:errStorage,now,fetch:async()=>({ok:false,status:502,json:async()=>({error:"upstream_429"})})}),/Yahoo begrenzt/);
  await assert.rejects(live.load("SAP.DE",{storage:errStorage,now,fetch:async()=>({ok:false,status:502,json:async()=>({error:"no_data"})})}),/keine Tageskurse/);
  assert.equal(errStorage.map.size,0);
  await assert.rejects(live.load("../x",{now,fetch:async()=>{throw Error("must not fetch")}}),/nicht abgefragt/);

  // EUR conversion from the snapshot table, otherwise from quoted stocks; pipeline momentum definition.
  const fx=live.fxTable({fx_eur:{USD:{eur_per_unit:.9,fx_date:"2026-11-03"}},stocks:[{currency:"GBp",eur_per_unit:.0118,fx_date:"2026-11-03"}]});
  assert.equal(fx.USD.eur_per_unit,.9);assert.equal(fx.GBp.eur_per_unit,.0118);
  const q=live.summary(series("AAPL",{currency:"USD"}),fx);
  assert.ok(Math.abs(q.eur-399*.9)<1e-9);assert.equal(q.fx_date,"2026-11-03");
  assert.ok(Math.abs(q.momentum_12_2-(378/147-1))<1e-12,"252 to 21 sessions ago");
  assert.equal(live.summary(series("X.T",{currency:"JPY",days:100}),fx).eur,null,"no invented EUR rate");
  assert.equal(live.summary(series("X.T",{currency:"JPY",days:100}),fx).momentum_12_2,null);

  // Card wiring: only search hits without stored quote, button does not toggle the card,
  // chart uses the fetched series.
  const html=fs.readFileSync("docs/index.html","utf8");
  assert.ok(html.includes('<script src="live-quote.js?v=3"></script>'));
  assert.ok(html.includes('const staleStored=Number.isFinite(s.reference_close_eur)&&s.entry_review==="stale_quote";'));
  assert.ok(html.includes('if(wantsLive&&!liveData&&typeof StockLiveQuote!=="undefined"){'));
  assert.ok(html.includes('(searchNote||momentumEl).after(box);'),"also candidate cards with a stale stored quote");
  assert.ok(html.includes('const button=add(box,"button",staleStored?"Aktuellen Kurs laden":"Kurs jetzt laden"'),"button element, not a text tag");
  assert.ok(html.includes('event.preventDefault();event.stopPropagation();void fetchLive();'));
  assert.ok(html.includes('showTradeLevels:()=>$("showTradeLevels").checked,data:liveData'));
  assert.ok(html.includes('if(liveData)s=StockLiveQuote.enrich(s,liveData,snapshot);'));
  assert.ok(html.includes('const fresh=makeCard(base,mix,{...options,liveData:data});'),"loaded card is rebuilt with all values");

  // Enrichment: EUR values, volatility and the entry/exit review from the fetched context.
  const ctx={sma200_ratio:.08,sma200_native:370,crash_21_level_native:330,crash_peak_level_native:310,return_21d:.02,
    drawdown_252d:-.05,atr14_native:6,crash_warning:false,correction_warning:false,risk_reference_native:384,
    context_basis:"Yahoo adjusted OHLC, signal after close"};
  const data={...series("SAN.PA",{currency:"USD"}),context:ctx,turnover:5e6,asof:"2026-11-03"};
  data.points[data.points.length-1][0]="2026-11-03";
  const snap={fx_eur:{USD:{eur_per_unit:.9,fx_date:"2026-11-03"}},market_context:{risk:"normal"}};
  const e=live.enrich({ticker:"SAN.PA",name:"Sanofi"},data,snap,Date.parse("2026-11-04T12:00:00Z"));
  assert.equal(e.entry_review,"entry_review");assert.equal(e.exit_review,"hold_review");
  assert.ok(Math.abs(e.model_buy_limit_eur-(399-6)*.9)<1e-6);
  assert.ok(Math.abs(e.model_initial_stop_eur-(399-6-15)*.9)<1e-6);
  assert.ok(Math.abs(e.sma200_level_eur-370*.9)<1e-6);
  assert.equal(e.avg_turnover_20d_eur,4.5e6);
  assert.ok(e.volatility_252d>0&&e.long_risk_basis.startsWith("Yahoo adjusted log returns"));
  assert.equal(live.enrich({ticker:"SAN.PA"},data,{...snap,market_context:{risk:"crash"}},Date.parse("2026-11-04T12:00:00Z")).entry_review,"wait_market");
  assert.equal(live.enrich({ticker:"SAN.PA"},data,snap,Date.parse("2026-11-12T12:00:00Z")).entry_review,"stale_quote");
  assert.equal(live.enrich({ticker:"SAN.PA"},{...data,context:null},snap).entry_review,"insufficient_data");
  assert.equal(live.enrich({ticker:"SAN.PA"},data,{}).reference_close_eur,undefined,"no invented EUR rate");
  const stale=live.enrich({ticker:"SAN.PA",price_date:"2026-10-29",entry_review:"stale_quote",model_buy_limit_eur:1,
    fundamentals:{revenue:5}},data,{...snap},Date.parse("2026-11-04T12:00:00Z"));
  assert.equal(stale.entry_review,"entry_review");assert.notEqual(stale.model_buy_limit_eur,1,"old levels replaced");
  assert.equal(stale.fundamentals.revenue,5,"stored fundamentals kept");
  console.log("Live search quotes: validation, reuse until expiry, shared requests, bounded device storage, honest errors, EUR conversion and card wiring verified.");
})().catch(error=>{console.error(error);process.exit(1);});
