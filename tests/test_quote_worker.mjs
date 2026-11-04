// Offline checks for cloudflare/quote-worker.js (no network).
import assert from "node:assert/strict";
import worker, {convert} from "../cloudflare/quote-worker.js";

const day=86400;
function payload(days,{start,end,gmtoffset=0,partial=null}={}){
  const ts=[],close=[],adj=[];
  const base=Date.UTC(2026,8,1)/1000+14*3600; // bars stamped at 14:00 UTC
  for(let i=0;i<days;i++){ts.push(base+i*day);close.push(100+i);adj.push((100+i)/2);}
  if(partial!==null){ts.push(base+(days-1)*day+3600);close.push(partial);adj.push(partial/2);}
  const meta={currency:"EUR",exchangeName:"PAR",gmtoffset};
  if(start)meta.currentTradingPeriod={regular:{start,end,gmtoffset}};
  const high=close.map(c=>c*1.01),low=close.map(c=>c*.99),volume=close.map(()=>1000);
  return {chart:{result:[{meta,timestamp:ts,indicators:{quote:[{close,high,low,volume}],adjclose:[{adjclose:adj}]}}]}};
}
const lastBar=Date.UTC(2026,8,1)/1000+14*3600+39*day; // day 40 at 14:00 UTC
const sessionStart=lastBar-6*3600, sessionEnd=lastBar+2.5*3600; // 08:00–16:30 UTC

// Open session: today's bar is dropped; valid until 30 min after close.
let c=convert("SAN.PA",payload(40,{start:sessionStart,end:sessionEnd}),lastBar+600);
assert.equal(c.points.length,39,"open session bar is not a close");
assert.equal(c.close,138);
assert.equal(Date.parse(c.expires)/1000,sessionEnd+1800);
assert.ok(c.points.every((p,i,a)=>!i||a[i-1][0]<p[0]));

// After settle: today's bar counts; next expiry is the following day's settle time.
c=convert("SAN.PA",payload(40,{start:sessionStart,end:sessionEnd}),sessionEnd+3600);
assert.equal(c.points.length,40);assert.equal(c.close,139);
assert.equal(Date.parse(c.expires)/1000,sessionEnd+1800+day);

// Within 30 minutes after the close the bar is still treated as not final.
c=convert("SAN.PA",payload(40,{start:sessionStart,end:sessionEnd}),sessionEnd+600);
assert.equal(c.points.length,39);

// Duplicate session bar keeps the latest value; no session data -> 1 hour.
c=convert("SAN.PA",payload(40,{partial:150}),lastBar+7200);
assert.equal(c.points.length,40);assert.equal(c.close,150);assert.equal(c.max_age,3600);

// Weekend: session in the past by days -> expiry rolls forward, capped at 24 h.
c=convert("SAN.PA",payload(40,{start:sessionStart,end:sessionEnd}),sessionEnd+2.2*day);
assert.ok(c.max_age>=300&&c.max_age<=86400);
assert.equal(convert("X",payload(20),lastBar),null,"too short history");
assert.equal(c.context,null,"context needs 253 sessions");
assert.equal(c.turnover,Math.round(c.close*1000*0+(()=>{const v=payload(40).chart.result[0].indicators.quote[0];return v.close.slice(-20).reduce((a,b)=>a+b*1000,0)/20;})()));
// Bars without high/low are skipped like in the pipeline.
const gap=payload(40);gap.chart.result[0].indicators.quote[0].high[10]=null;
assert.equal(convert("SAN.PA",gap,lastBar+7200).points.length,39);
const long=convert("SAN.PA",payload(300),Date.UTC(2027,0,1)/1000);
assert.ok(long.context&&long.context.context_basis.startsWith("Yahoo adjusted OHLC"));
assert.equal(long.context.crash_warning,false);assert.ok(long.context.sma200_ratio>0);

// HTTP behaviour: origin restriction, strict symbols, cache header, upstream errors.
const calls=[];
globalThis.fetch=async u=>{calls.push(u);return new Response(JSON.stringify(payload(40)),{status:200});};
const site="https://boraborapalm.github.io";
const ok=await worker.fetch(new Request("https://w.example/quote?symbol=san.pa",{headers:{Origin:site}}));
assert.equal(ok.status,200);assert.equal(ok.headers.get("access-control-allow-origin"),site);
assert.match(ok.headers.get("cache-control"),/^public, max-age=\d+$/);
assert.match(calls[0],/^https:\/\/query1\.finance\.yahoo\.com\/v8\/finance\/chart\/SAN\.PA\?range=10y&interval=1d$/);
assert.equal((await worker.fetch(new Request("https://w.example/quote?symbol=X",{headers:{Origin:"https://evil.example"}}))).status,403);
for(const bad of ["","../x","a/b","https://x","A B","X".repeat(21)])
  assert.equal((await worker.fetch(new Request("https://w.example/quote?symbol="+encodeURIComponent(bad)))).status,400,bad);
assert.equal((await worker.fetch(new Request("https://w.example/other"))).status,404);
const version=await worker.fetch(new Request("https://w.example/version"));
assert.equal(version.status,200);assert.ok((await version.json()).features.includes("context"));
assert.equal((await worker.fetch(new Request("https://w.example/quote?symbol=SAP.DE",{method:"POST"}))).status,405);
const direct=await worker.fetch(new Request("https://w.example/quote?symbol=SAP.DE"));
assert.equal(direct.status,200);assert.equal(direct.headers.get("access-control-allow-origin"),null);
globalThis.fetch=async()=>new Response("",{status:429});
const limited=await worker.fetch(new Request("https://w.example/quote?symbol=SAP.DE"));
assert.equal(limited.status,502);assert.equal((await limited.json()).error,"upstream_429");
assert.equal(limited.headers.get("cache-control"),"no-store","errors are never cached");
console.log("Quote worker: closes only, market-aware expiry, origin/symbol restrictions and error handling verified.");
