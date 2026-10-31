const fs=require("node:fs");
const html=fs.readFileSync("docs/index.html","utf8");
function exactly(pattern,count,name){
  const n=(html.match(pattern)||[]).length;
  if(n!==count)throw new Error(name+": expected "+count+", found "+n);
}
exactly(/<html(?:\s[^>]*)?>/gi,1,"HTML opening");
exactly(/<\/html>/gi,1,"HTML closing");
exactly(/<script(?:\s[^>]*)?>/gi,2,"JS opening (widget and inline)");
exactly(/<\/script>/gi,2,"JS closing (widget and inline)");
if(!/<\/html>\s*$/i.test(html))throw new Error("Code leaked after </html>");
const match=html.match(/<script>([\s\S]*?)<\/script>/i);
if(!match)throw new Error("Missing inline script");
new Function(match[1]);
for(const id of ["universe","quoted","eligible","search","region","scope","trOnly",
  "count","results","empty","status","reload","factorMomentum","factorLowRisk","factorTrend","strategySummary","showTradeLevels"]){
  if(!html.includes('id="'+id+'"'))throw new Error("UI control missing: "+id);
}
if(html.includes("<iframe")||html.includes('data-tab=')||html.includes("ATR-Stop")||html.includes("strategie-study.json"))
  throw new Error("Retired tab/iframe/trade-model UI accidentally restored");
if(!html.includes("reference_close_eur")||!html.includes("momentum_12_2"))
  throw new Error("Research app missing EUR reference price or momentum");
if(!html.includes('id="showTradeLevels" type="checkbox"') ||
    html.includes('id="showTradeLevels" type="checkbox" checked')){
  throw new Error("The global trading-levels option must be unchecked by default");
}
if(!match[1].includes('if($("showTradeLevels").checked){') ||
    !match[1].includes('"showTradeLevels","search"')){
  throw new Error("Buy/stop prices must be hidden until the global switch is enabled");
}
console.log("Simple global mobile app: valid JavaScript, one HTML document, no deprecated tabs or trailing code.");


// Run the EXACT pure ranking functions embedded in the published UI.
// No mock backtests: test transparency, ties, factor weights and missing data.
const vm=require("node:vm");
const from="// STRATEGY_MIX_START";
const to="// STRATEGY_MIX_END";
const start=match[1].indexOf(from);
const end=match[1].indexOf(to);
if(start<0||end<=start)throw new Error("Cannot inspect the live factor mixer");
const snippet=match[1].slice(start,end+to.length);
const context=vm.createContext({});
vm.runInContext(snippet,context);
const sample=[
 {ticker:"A",momentum_12_2:.50,atr14_native:20,close:100,sma200_ratio:-.2},
 {ticker:"B",momentum_12_2:.30,atr14_native:3,close:100,sma200_ratio:.15},
 {ticker:"C",momentum_12_2:.10,atr14_native:5,close:100,sma200_ratio:.25},
 {ticker:"MISSING",momentum_12_2:.42,close:100,sma200_ratio:.30}
];
context.sample=sample;
const assert=require("node:assert/strict");
const momentum=vm.runInContext('mixedRanks(sample,["momentum"])',context);
assert.equal(momentum.size,4);
assert.equal(momentum.get("A").score,100);
assert.ok(momentum.get("MISSING").score>momentum.get("B").score);
const combined=vm.runInContext('mixedRanks(sample,["momentum","lowRisk"])',context);
assert.equal(combined.has("MISSING"),false,"Missing ATR must NEVER be imputed");
assert.ok(combined.get("B").score>combined.get("A").score,
  "Multi-factor average must genuinely change the ordering");
assert.equal(combined.get("B").parts.length,2);
assert.equal(combined.get("B").score,
  (combined.get("B").parts[0].score+combined.get("B").parts[1].score)/2);
const triplet=vm.runInContext('mixedRanks(sample,["momentum","lowRisk","trend"])',context);
assert.equal(triplet.get("B").parts.length,3);
assert.ok(triplet.get("B").score>triplet.get("A").score);
const tied=vm.runInContext('mixedRanks([{ticker:"A",momentum_12_2:.3},{ticker:"B",momentum_12_2:.3}],["momentum"])',context);
assert.equal(tied.get("A").score,50);
assert.equal(tied.get("B").score,50);
assert.equal(vm.runInContext('mixedRanks(sample,[])',context).size,0);
assert.equal(vm.runInContext('mixedRanks(sample,["invented"])',context).size,0);
console.log("Strategy checkbox mixer: solo momentum, equal-weight combinations, missing-data exclusion and ties verified.");


// Chart must remain lazy: fetched after <details> is opened, never at app start.
if(!html.includes('<script src="chart-widget.js"></script>')||
   !match[1].includes('article.addEventListener("toggle"')||
   !match[1].includes('StockCharts.create(chartHost,s,')||
   !match[1].includes('showTradeLevels:()=>$("showTradeLevels").checked')){
  throw Error("Lazy price chart or optional trade lines are not correctly connected");
}
const charts=require("../docs/chart-widget.js");
assert.deepEqual(Object.keys(charts.periods),["1M","3M","6M","1J","3J","5J","MAX"]);
const pts=[
 ["2025-01-01",100],["2025-05-01",105],["2025-09-01",92],
 ["2025-11-01",103],["2025-12-01",110],["2026-01-01",120]
];
assert.equal(charts.selectPoints(pts,"MAX").length,6);
assert.equal(charts.selectPoints(pts,"3M").length,3);
assert.equal(charts.selectPoints(pts,"1M").length,2);
const raw=charts.checkedData({version:1,ticker:"TEST",asof:"2026-01-01",
  currency:"JPY",points:pts},"TEST");
const fxStock={ticker:"TEST",close:120,eur_per_unit:.006,price_date:"2026-01-01",
  model_buy_limit_eur:.66,model_initial_stop_eur:.54};
assert.equal(charts.modelLines(fxStock,raw,false).length,0);
const lines=charts.modelLines(fxStock,raw,true);
assert.equal(lines.length,2);
assert.ok(Math.abs(lines[0].value-110)<1e-6,"EUR buy must match JPY price axis");
assert.ok(Math.abs(lines[1].value-90)<1e-6,"EUR stop must match JPY price axis");
assert.equal(charts.modelLines({...fxStock,price_date:"2025-12-01"},raw,true).length,0,
  "Never draw buy/stop lines on out-of-date unrelated chart");
assert.throws(()=>charts.checkedData({...raw,points:pts.slice().reverse()},"TEST"));
console.log("Lazy chart: 3M selection, 1M–MAX range, JPY/EUR guides, stale-date rejection tested.");
