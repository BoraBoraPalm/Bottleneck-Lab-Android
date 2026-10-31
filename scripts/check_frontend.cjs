const fs=require("node:fs");
const html=fs.readFileSync("docs/index.html","utf8");
function exactly(pattern,count,name){
  const n=(html.match(pattern)||[]).length;
  if(n!==count)throw new Error(name+": expected "+count+", found "+n);
}
exactly(/<html(?:\s[^>]*)?>/gi,1,"HTML opening");
exactly(/<\/html>/gi,1,"HTML closing");
exactly(/<script(?:\s[^>]*)?>/gi,1,"JS opening");
exactly(/<\/script>/gi,1,"JS closing");
if(!/<\/html>\s*$/i.test(html))throw new Error("Code leaked after </html>");
const match=html.match(/<script>([\s\S]*?)<\/script>/i);
if(!match)throw new Error("Missing inline script");
new Function(match[1]);
for(const id of ["universe","quoted","eligible","search","region","scope","trOnly",
  "count","results","empty","status","reload","factorMomentum","factorLowRisk","factorTrend","strategySummary"]){
  if(!html.includes('id="'+id+'"'))throw new Error("UI control missing: "+id);
}
if(html.includes("<iframe")||html.includes('data-tab=')||html.includes("ATR-Stop")||html.includes("strategie-study.json"))
  throw new Error("Retired tab/iframe/trade-model UI accidentally restored");
if(!html.includes("reference_close_eur")||!html.includes("momentum_12_2"))
  throw new Error("Research app missing EUR reference price or momentum");
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
