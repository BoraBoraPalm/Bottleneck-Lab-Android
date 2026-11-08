"use strict";
// Depot-Check: returns with dividends/splits, own prices, EUR conversion,
// benchmark alignment and choice, portfolio sum. No network, no DOM.
const assert=require("node:assert/strict");
const fs=require("node:fs");
const tc=require("../docs/trade-check.js");

const close=(a,b,msg)=>assert.ok(Math.abs(a-b)<1e-9,(msg||"")+" "+a+" != "+b);
// Trading days Mon–Fri from 2024-01-01 (a Monday).
function days(n,start="2024-01-01"){
  const out=[];let t=Date.parse(start+"T00:00:00Z");
  while(out.length<n){const d=new Date(t);if(d.getUTCDay()%6!==0)out.push(d.toISOString().slice(0,10));t+=86400000;}
  return out;
}
const D=days(600);
// Raw price rises 10 → 20 linearly; a dividend of 1 on day 300 means adjusted
// history before day 300 is scaled down (adjusted = raw × factor).
function stockSeries(currency="EUR"){
  const raw=D.map((d,i)=>10+10*i/(D.length-1));
  const factor=i=>i<300?(raw[300]-1)/raw[300]:1;
  return {currency,points:D.map((d,i)=>[d,raw[i]*factor(i)]),closes:raw};
}
const flat=(value,currency="EUR")=>({currency,name:"Flat",points:D.map(d=>[d,value])});
const growing=(rate,currency="EUR")=>({currency,name:"Grow",points:D.map((d,i)=>[d,100*(1+rate*i/(D.length-1))])});

// 1) EUR stock vs EUR benchmark, buy on a weekend -> next trading day, still held.
const s=stockSeries();
let r=tc.compute({buy:"2024-01-06",open:true},s,null,growing(.2),null);
assert.equal(r.buyDay,"2024-01-08","Saturday buy executes on Monday");
assert.equal(r.sellDay,D[D.length-1]);assert.equal(r.open,true);
close(r.closeBuy,s.closes[5]);
close(r.stockEur,s.points[D.length-1][1]/s.points[5][1]-1,"total return incl. dividend");
assert.ok(r.stockEur>s.closes[D.length-1]/s.closes[5]-1,"dividend raises the return above the price change");
close(r.benchEur,(100*(1+.2*(D.length-1)/(D.length-1)))/(100*(1+.2*5/(D.length-1)))-1);
close(r.outperformance,r.stockEur-r.benchEur);
assert.ok(r.days>800&&r.stockAnnual!==null&&r.benchAnnual!==null);
assert.equal(r.invested,1000,"no shares: 1,000 EUR per position");
assert.equal(r.chart[0][1],100);assert.equal(r.chart[0][2],100);
assert.equal(r.chart[r.chart.length-1][0],r.sellDay);assert.ok(r.chart.length<=242);

// 2) Own prices replace the closes but keep dividend/split effects.
r=tc.compute({buy:D[10],sell:D[400],buyPrice:s.closes[10]*.98,sellPrice:s.closes[400]*1.01,shares:10},s,null,flat(50),null);
const base=s.points[400][1]/s.points[10][1];
close(r.stockEur,base*1.01/.98-1,"own prices scale the adjusted return");
assert.equal(r.ownBuy,true);assert.equal(r.ownSell,true);
close(r.invested,s.closes[10]*.98*10);close(r.benchEur,0);
close(r.endValue,r.invested*(1+r.stockEur));

// 3) Currency: USD stock converted with USD->EUR, London pence with GBP->EUR/100.
const usd=stockSeries("USD"),fxUsd={points:D.map((d,i)=>[d,.9+.1*i/(D.length-1)]),scale:1};
r=tc.compute({buy:D[0],sell:D[599]},usd,fxUsd,flat(1),null);
close(r.stockEur,(1+r.stockLocal)*(1.0/.9)-1,"EUR return includes the dollar move");
const gbp=stockSeries("GBp"),fxGbp={points:D.map(d=>[d,1.2]),scale:.01};
r=tc.compute({buy:D[0],sell:D[599],shares:100},gbp,fxGbp,flat(1),null);
close(r.stockEur,r.stockLocal,"constant rate: EUR = local return");
close(r.buyEur,gbp.closes[0]*.012,"pence price in EUR");
assert.deepEqual(tc.fxSymbol("GBp"),{symbol:"GBPEUR=X",scale:.01});
assert.deepEqual(tc.fxSymbol("USD"),{symbol:"USDEUR=X",scale:1});
assert.equal(tc.fxSymbol("EUR"),null);

// 4) Benchmark in another currency and with fewer days (holiday): last close on/before.
const benchUsd={currency:"USD",name:"US",points:D.filter((d,i)=>i!==5).map(d=>[d,100])};
r=tc.compute({buy:D[5],sell:D[599]},s,null,benchUsd,fxUsd);
assert.equal(r.benchDays[0],D[4],"benchmark holiday: previous close");
close(r.benchEur,fxUsd.points[599][1]/fxUsd.points[4][1]-1,"flat USD benchmark: only the currency effect");

// 5) Errors are explained, not guessed.
const err=(input,stock=s,bench=flat(1),fx=null,bfx=null)=>tc.compute(input,stock,fx,bench,bfx).error;
assert.match(err({open:true}),/Kaufdatum fehlt/);
assert.match(err({buy:"2023-12-01",open:true}),/beginnt erst am 2024-01-01/);
assert.match(err({buy:D[50],sell:D[10]}),/vor dem Kaufdatum/);
assert.match(err({buy:D[50]}),/Verkaufsdatum fehlt/);
assert.match(err({buy:"2030-01-01",open:true}),/noch keinen Schlusskurs/);
assert.match(err({buy:D[1],open:true},{...s,closes:undefined}),/Unbereinigte Schlusskurse fehlen/);
assert.match(err({buy:D[1],open:true},usd,flat(1),{points:[],scale:1}),/Wechselkurs USD\/EUR/);
assert.match(err({buy:D[1],open:true},s,{currency:"EUR",name:"Late",points:D.slice(100).map(d=>[d,1])}),/beginnt erst am/);
r=tc.compute({buy:D[10],sell:"2030-01-01"},s,null,flat(1),null);
assert.equal(r.sellDay,D[599]);assert.match(r.note,/noch keinen Schlusskurs/);

// 6) Portfolio: what the same money would have become in the benchmarks.
const a=tc.compute({buy:D[0],sell:D[599],shares:10},s,null,flat(1),null);
const b=tc.compute({buy:D[0],sell:D[599]},s,null,growing(1),null);
const total=tc.portfolio([a,b,{error:"x"}]);
assert.equal(total.count,2);close(total.invested,a.invested+1000);
close(total.end,a.endValue+b.endValue);close(total.bench,a.benchValue+b.benchValue);
close(total.difference,total.end-total.bench);assert.equal(total.estimatedAmounts,true);
assert.equal(tc.portfolio([{error:"x"}]),null);

// 7) Automatic benchmark by issuer country (directory country, ISIN, exchange suffix).
const pick=(stock,avail)=>tc.pickBenchmark(stock,avail)?.id;
assert.equal(pick({ticker:"SAP.DE",country_code:"DE"}),"DAX");
assert.equal(pick({ticker:"SAN.PA",country_code:"FR"}),"STOXX600");
assert.equal(pick({ticker:"SNY",country_code:"FR",reference_isin:"US80105N1054"}),"STOXX600","ADR: issuer's home market");
assert.equal(pick({ticker:"AAPL"}),"SPY","no suffix: US");
assert.equal(pick({ticker:"VOE.VI"}),"STOXX600","suffix fallback");
assert.equal(pick({ticker:"7203.T"}),"TOPIX");
assert.equal(pick({ticker:"XYZ.ZZ"}),"ACWI","unknown market: world");
assert.equal(pick({ticker:"SAP.DE",country_code:"DE"},new Set(["ACWI","SPY"])),"ACWI","unavailable benchmark is skipped");
assert.equal(tc.countryOf({reference_isin:"AT0000937503",ticker:"VOE.VI"}),"AT");

// 8) Page wiring.
const html=fs.readFileSync("docs/index.html","utf8");
assert.ok(html.includes('<script src="trade-check.js?v=2"></script>'));
assert.ok(html.includes('id="tabTradeCheck"')&&html.includes('id="tradeCheckPanel"'));
assert.ok(html.includes('document.querySelector(".horizon-panel").hidden=view==="depot";'));
const js=fs.readFileSync("docs/trade-check.js","utf8");
assert.ok(js.includes("try{storage.setItem(STORAGE_KEY"),"device storage wrapped in try/catch");
console.log("Depot-Check: dividends/splits, own prices, EUR conversion incl. pence, benchmark days and choice, portfolio sum and page wiring verified.");
