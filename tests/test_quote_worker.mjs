// Offline checks for cloudflare/quote-worker.js (no network).
import assert from "node:assert/strict";
import worker, {convert, RequestLog} from "../cloudflare/quote-worker.js";

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
// Search log: recorded after a successful quote, listed for the data run.
class FakeSql{
  constructor(){this.rows=new Map();}
  exec(q,...a){
    if(q.startsWith("CREATE"))return {toArray:()=>[]};
    if(q.startsWith("INSERT")){const [sym,now]=a;const r=this.rows.get(sym);this.rows.set(sym,{symbol:sym,last:now,hits:r?r.hits+1:1});return {toArray:()=>[]};}
    if(q.startsWith("DELETE FROM requested WHERE last")){for(const [k,v] of this.rows)if(v.last<a[0])this.rows.delete(k);return {toArray:()=>[]};}
    if(q.startsWith("DELETE")){const keep=[...this.rows.values()].sort((x,y)=>y.last-x.last).slice(0,a[0]).map(r=>r.symbol);for(const k of [...this.rows.keys()])if(!keep.includes(k))this.rows.delete(k);return {toArray:()=>[]};}
    if(q.startsWith("SELECT"))return {toArray:()=>[...this.rows.values()].sort((x,y)=>y.last-x.last).slice(0,a[0])};
    throw Error(q);
  }
}
const object=new RequestLog({storage:{sql:new FakeSql()}});
const env={REQUESTS:{idFromName:n=>n,get:()=>({fetch:u=>object.fetch(new Request(u))})}};
const waits=[];const ctxStub={waitUntil:p=>waits.push(p)};
globalThis.fetch=async()=>new Response(JSON.stringify(payload(40)),{status:200});
await worker.fetch(new Request("https://w.example/quote?symbol=san.pa",{headers:{Origin:site}}),env,ctxStub);
await worker.fetch(new Request("https://w.example/quote?symbol=SAN.PA"),env,ctxStub);
await worker.fetch(new Request("https://w.example/quote?symbol=VOE.VI"),env,ctxStub);
await Promise.all(waits);
const listed=await (await worker.fetch(new Request("https://w.example/requested"),env,ctxStub)).json();
assert.deepEqual(listed.symbols.map(r=>r.symbol).sort(),["SAN.PA","VOE.VI"]);
assert.equal(listed.symbols.find(r=>r.symbol==="SAN.PA").hits,2);
assert.ok((await (await worker.fetch(new Request("https://w.example/version"),env)).json()).features.includes("requested"));
assert.equal((await object.fetch(new Request("https://log/add?symbol=../x"))).status,400);
globalThis.fetch=async()=>new Response("",{status:404});
waits.length=0;
await worker.fetch(new Request("https://w.example/quote?symbol=NOPE.PA"),env,ctxStub);
assert.equal(waits.length,0,"failed lookups are not recorded");
assert.deepEqual((await (await worker.fetch(new Request("https://w.example/requested"))).json()).symbols,[],"no binding: empty list");
console.log("Quote worker: closes only, market-aware expiry, origin/symbol restrictions and error handling verified.");
