const fs=require("node:fs");
const html=fs.readFileSync("docs/index.html","utf8");
function exactly(pattern,count,name){
  const n=(html.match(pattern)||[]).length;
  if(n!==count)throw new Error(name+": expected "+count+", found "+n);
}
exactly(/<html(?:\s[^>]*)?>/gi,1,"HTML opening");
exactly(/<\/html>/gi,1,"HTML closing");
exactly(/<script(?:\s[^>]*)?>/gi,6,"JS opening (five widgets and inline)");
exactly(/<\/script>/gi,6,"JS closing (five widgets and inline)");
if(!/<\/html>\s*$/i.test(html))throw new Error("Code leaked after </html>");
const match=html.match(/<script>([\s\S]*?)<\/script>/i);
if(!match)throw new Error("Missing inline script");
new Function(match[1]);
for(const id of ["universe","quoted","eligible","search","region","scope","trOnly",
  "tabCandidates","tabStockSearch","candidatesPanel","stockSearchPanel","stockSearchForm",
  "stockSearchInput","stockSearchButton","stockSearchStatus","stockSearchResults","stockSearchSuggestions",
  "searchFitChoices",
  "count","results","empty","status","reload","factorMomentum","factorLowRisk","factorTrend","factorSander","factorGrowth","strategySummary","showTradeLevels"]){
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

const sanderSample=[
  {ticker:"QUALIFIED",momentum_12_2:-.2,atr14_native:3,close:100,sma200_ratio:-.15,
   sander_score:80,drawdown_252d:-.30,fundamentals:{quality_ok:true}},
  {ticker:"MISSING",momentum_12_2:.3,atr14_native:1,close:100,sma200_ratio:.15,
   sander_score:null},
  {ticker:"SECOND",momentum_12_2:.15,atr14_native:5,close:100,sma200_ratio:-.20,
   sander_score:40,drawdown_252d:-.18,fundamentals:{quality_ok:true}}
];
context.sanderSample=sanderSample;
const sanderOnly=vm.runInContext('mixedRanks(sanderSample,["sander"])',context);
assert.equal(sanderOnly.size,2,"Only financially verified buy-the-dip stocks rank");
assert.ok(sanderOnly.get("QUALIFIED").score>sanderOnly.get("SECOND").score);
const sanderCombination=vm.runInContext('mixedRanks(sanderSample,["momentum","sander"])',context);
assert.equal(sanderCombination.size,2,"Sander combined with momentum still excludes unchecked firms");
assert.equal(sanderCombination.get("QUALIFIED").parts.length,2);
assert.equal(sanderCombination.get("MISSING"),undefined);

console.log("Strategy checkbox mixer: solo momentum, equal-weight combinations, missing-data exclusion and ties verified.");

const growthSample=[
  {ticker:"EARLY",momentum_12_2:null,growth_score:80,growth_radar:{status:"qualified",score:80},atr14_native:8,close:100},
  {ticker:"MATURE",momentum_12_2:.3,growth_score:60,growth_radar:{status:"qualified",score:60},atr14_native:2,close:100},
  {ticker:"UNCHECKED",momentum_12_2:.5,growth_score:99,growth_radar:{status:"missing_quarters",score:null}},
  {ticker:"MISSING",momentum_12_2:.4}
];
context.growthSample=growthSample;
const growthOnly=vm.runInContext('mixedRanks(growthSample,["growth"])',context);
assert.equal(growthOnly.size,2);
assert.ok(growthOnly.has("EARLY"),"Growth alone can include a six-month stock without 12-2 momentum");
assert.ok(growthOnly.get("EARLY").score>growthOnly.get("MATURE").score);
const growthMix=vm.runInContext('mixedRanks(growthSample,["growth","momentum"])',context);
assert.equal(growthMix.size,1,"Selecting momentum must enforce its own required history");
assert.ok(growthMix.has("MATURE"));
const growthRisk=vm.runInContext('mixedRanks(growthSample,["growth","lowRisk"])',context);
assert.equal(growthRisk.get("EARLY").score,50);
assert.equal(growthRisk.get("MATURE").score,50,"Low risk is a ranking preference, not an undisclosed hard volatility filter");
assert.equal(vm.runInContext('mixedRanks(growthSample,["growth","sander"])',context).size,0);
assert.ok(html.includes('StockGrowth.preview(head,s)')&&html.includes('StockGrowth.render(article,s)'));
assert.ok(!html.includes('id="factorGrowth" data-factor="growth" checked'),"Growth is opt-in");
console.log("Growth option: standalone, momentum/low-risk/Sander combinations and missing-data exclusion verified.");

const growth=require("../docs/growth-widget.js");
const growthStock={ticker:"GROW",price_date:"2026-10-30",growth_radar:{status:"qualified",score:72,
  growth_score:70,quality_score:80,confirmation_score:66,
  quarters:[{end:"2026-03-31",filed:"2026-04-25"},{end:"2026-06-30",filed:"2026-07-25"},
    {end:"2026-09-30",filed:"2026-10-25"}]}};
assert.equal(growth.state(growthStock,"2026-10-31T12:00:00Z").qualified,true);
assert.equal(growth.state(growthStock,"2027-05-01T12:00:00Z").usable,false,"Old quarters cannot display a fresh growth score");
assert.equal(growth.state(growthStock,"2026-11-15T12:00:00Z").qualified,false,"Stale quotes cannot display a confirmed signal");
assert.equal(growth.state({...growthStock,growth_radar:{...growthStock.growth_radar,quality_score:null}},"2026-10-31T12:00:00Z").qualified,false);
assert.equal(growth.state({ticker:"MISSING"}).usable,false);
console.log("Growth display: three independent components, incomplete evidence and stale-date handling verified.");


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

// Exercise the exact financial classifications shipped to the browser.
const financials=require("../docs/fundamentals-widget.js");
const today="2026-10-31T12:00:00Z";
const financialStock={ticker:"EXAMPLE",name:"Example Manufacturing",fundamentals:{
  fy_end:"2025-12-31",filed:"2026-02-15",currency:"USD",source:"SEC EDGAR",
  revenue:100,net_income:20,operating_cashflow:25,free_cashflow:15,
  revenue_growth_yoy:.12,net_income_growth_yoy:.18,profit_margin:.20,
  operating_cashflow_margin:.25,free_cashflow_margin:.15,
  equity:50,equity_ratio:.50,current_ratio:2,liabilities_to_equity:1
}};
const financialMetrics=stock=>financials.metrics(stock,{today});
const byKey=(stock,key)=>financialMetrics(stock).find(m=>m.key===key);
assert.equal(financialMetrics(financialStock).length,8);
assert.ok(financialMetrics(financialStock).every(m=>m.state==="green"));
assert.ok(financialMetrics({ticker:"MISSING"}).every(m=>m.state==="unknown"));
assert.ok(financialMetrics({fundamentals:{...financialStock.fundamentals,
  fy_end:"2024-01-01"}}).every(m=>m.state==="unknown"),"Old statements cannot have green financial badges");
assert.ok(financialMetrics({fundamentals:{...financialStock.fundamentals,
  filed:"2027-01-01"}}).every(m=>m.state==="unknown"&&m.text==="–"),"Future filings must not leak into cards");
const financialRule=financials.rules.find(r=>r.key==="revenue_growth_yoy");
for(const [value,expected] of [[.10,"green"],[0,"yellow"],[-.10,"orange"],[-.10001,"red"],
  [null,"unknown"],[undefined,"unknown"],[NaN,"unknown"],[false,"unknown"]]){
  assert.equal(financials.rating(value,financialRule),expected,"Growth boundary or missing-value classification");
}
const debtRule=financials.rules.find(r=>r.key==="liabilities_to_equity");
for(const [value,expected] of [[0,"green"],[1,"green"],[2,"yellow"],[4,"orange"],[4.1,"red"]])
  assert.equal(financials.rating(value,debtRule),expected);
const withFund=changes=>({...financialStock,fundamentals:{...financialStock.fundamentals,...changes}});
assert.equal(byKey(withFund({net_income:-20,net_income_growth_yoy:1}),"net_income_growth_yoy").state,"red",
  "A company still losing money must not get green earnings growth");
assert.equal(byKey(withFund({net_income:20,net_income_growth_yoy:null,earnings_comparison:"turnaround"}),"net_income_growth_yoy").state,"yellow");
assert.equal(byKey(withFund({equity:-10,liabilities_to_equity:null}),"liabilities_to_equity").state,"red");
assert.equal(byKey(withFund({free_cashflow:null,free_cashflow_margin:null}),"free_cashflow_margin").state,"unknown");
assert.ok(financialMetrics({...financialStock,stock_sector:"Financial Services"})
  .filter(m=>m.sensitive).every(m=>m.state==="unknown"&&m.label==="Branchenspezifisch"));
assert.ok(html.includes('StockFundamentals.preview(head,s)')&&html.includes('StockFundamentals.render(article,s)'),
  "Fundamental metrics must be connected to every stock, independent of the Sander filter");
for(const colour of ["green","yellow","orange","red","unknown"])
  assert.ok(html.includes(".fund-"+colour+"{"),"Missing financial colour style: "+colour);
console.log("Fundamentals: 8 metrics, 4 colour bands, missing/stale data, losses, turnarounds and sector exceptions verified.");

// Independent identity search: all known stocks, never the strategy-filtered list.
const search=require("../docs/stock-search.js");
const searchIndex=search.prepare([
  {ticker:"NVDA",name:"NVIDIA Corporation",reference_isin:"US67066G1040"},
  {ticker:"NVDA.DE",name:"NVIDIA Corporation",exchange:"XETRA"},
  {ticker:"MSFT",name:"Microsoft Corporation"},
  {ticker:"GOOGL",name:"Alphabet Inc."},
  {ticker:"META",name:"Meta Platforms Inc."},
  {ticker:"MUELL.DE",name:"Müller & Söhne AG"},
  {ticker:"NEW",name:"Unscanned Company"},
  {ticker:"BRK-B",name:"Berkshire Hathaway Inc."},
  {ticker:"F",name:"Ford Motor Company"}
],[{ticker:"NVDA",name:"NVDA",reference_close_eur:100,eligible_global_ranking:false},
   {ticker:"LOW",name:"Illiquid Low Price Company",eligible_global_ranking:false,tr_at_listed:false}]);
const first=query=>search.find(searchIndex,query).items[0]?.stock;
assert.equal(first("nViDiA").ticker,"NVDA");
assert.equal(first("nvda").name,"NVIDIA Corporation","Ticker-only quote names must not erase directory names");
assert.equal(search.find(searchIndex,"NVDA").total,1,"An exact ticker must not add unrelated fuzzy names");
assert.equal(first("US67066G1040").ticker,"NVDA");
assert.equal(first("Micrsoft").ticker,"MSFT","Missing character tolerated");
assert.equal(first("Mircosoft").ticker,"MSFT","Adjacent transposition tolerated");
assert.equal(first("Nvidai").ticker,"NVDA");
assert.equal(first("Google").ticker,"GOOGL");
assert.equal(first("Facebook").ticker,"META");
assert.equal(first("muller sohne").ticker,"MUELL.DE");
assert.equal(first("mueller").ticker,"MUELL.DE");
assert.equal(first("brk.b").ticker,"BRK-B");
assert.equal(first("F").ticker,"F","One-letter exact tickers work");
assert.equal(first("illiquid").ticker,"LOW","Illiquid/filtered stocks remain searchable");
assert.equal(first("unscanned").ticker,"NEW","Directory-only company remains searchable");
assert.equal(first("nonsenseUnrelatedName"),undefined);
assert.equal(search.find(searchIndex,"").items.length,0);
assert.equal(search.find(searchIndex,"Nvidia",1).items.length,1);
assert.equal(search.find(searchIndex,"Nvidia",1).total,2,"Separate exchange listings retain their identity");
assert.equal(search.distance("microsoft","mircosoft",2),1);
assert.ok(match[1].includes('getStocks:()=>snapshot?.stocks||[]'),"Search must use all snapshot stocks, not dataRows or mixedRanks");
assert.ok(match[1].includes('makeCard(stock,null,{independent:true,matchLabel})'),"Search cards must not display investment ranks");
assert.ok(html.includes('role="tablist"')&&html.includes('role="search"')&&html.includes('type="submit">Suchen'));
assert.ok(match[1].includes('"ArrowLeft","ArrowRight","Home","End"'),"Tabs need keyboard navigation");
console.log("Independent search: strategy exclusion bypass, directory-only stocks, ticker/ISIN, aliases, accents, typos, transpositions and bounded results verified.");

const fit=require("../docs/strategy-fit.js");
const fitToday={today:"2026-10-31T12:00:00Z"};
const fitStock={ticker:"FIT",price_date:"2026-10-30",source:"Yahoo Finance",close:100,atr14_native:1.5,
  context_basis:"Yahoo adjusted OHLC, signal after close",momentum_basis:"Yahoo adjusted daily closes",
  momentum_12_2:.3,sma200_ratio:.1,drawdown_252d:-.3,
  fundamentals:{fy_end:"2025-12-31",filed:"2026-02-15",net_income:10,operating_cashflow:15,
    profit_margin:.1,revenue_growth_yoy:.2}};
const fitFor=(stock,key)=>fit.assess(stock,key,fitToday);
for(const key of ["momentum","lowRisk","trend","sander"]){
  const value=fitFor(fitStock,key);
  assert.equal(value.state,"green");
  assert.ok(value.reason.length>10);
  assert.equal(fitFor({ticker:"NO_DATA"},key).state,"unknown","Missing evidence must not be graded red");
  assert.equal(fitFor({...fitStock,price_date:"2026-01-01"},key).state,"unknown","Stale prices must not be graded green");
}
for(const [value,state] of [[.2,"green"],[0,"yellow"],[-.15,"orange"],[-.16,"red"]])
  assert.equal(fitFor({...fitStock,momentum_12_2:value},"momentum").state,state);
for(const [value,state] of [[2,"green"],[4,"yellow"],[6,"orange"],[6.1,"red"]])
  assert.equal(fitFor({...fitStock,atr14_native:value},"lowRisk").state,state);
assert.equal(fitFor({...fitStock,momentum_12_2:null},"momentum").state,"unknown");
assert.equal(fitFor({...fitStock,drawdown_252d:-.02},"sander").state,"yellow","One failed requirement is partial fit, not missing data");
assert.equal(fitFor({...fitStock,fundamentals:{...fitStock.fundamentals,
  net_income:-10,operating_cashflow:-10,profit_margin:-.1,revenue_growth_yoy:-.2}},"sander").state,"red");
const growthFit={...fitStock,return_63d:.3,growth_radar:{status:"qualified",
  quarters:[{end:"2026-03-31",filed:"2026-04-25",revenue_growth_yoy:.2},
    {end:"2026-06-30",filed:"2026-07-25",revenue_growth_yoy:.25},
    {end:"2026-09-30",filed:"2026-10-25",revenue_growth_yoy:.4,net_margin:.15}],
  revenue_acceleration:.15,annual_cashflow_margin:.2,net_margin_change_yoy:.05,relative_63d:.1,breakout_63d_ratio:-.02}};
assert.equal(fitFor(growthFit,"growth").state,"green");
assert.equal(fitFor({...growthFit,growth_radar:{...growthFit.growth_radar,status:"missing_price"}},"growth").state,"unknown");
const weakGrowth={...growthFit,growth_radar:{...growthFit.growth_radar,status:"criteria_not_met",revenue_acceleration:-.1}};
assert.equal(fitFor(weakGrowth,"growth").state,"yellow");
assert.ok(fitFor(weakGrowth,"growth").reason.includes("Beschleunigung"));
assert.ok(match[1].includes('StockFit.render(head,s,selectedSearchFits())'),"Search cards must show selected per-strategy fit");
assert.ok(match[1].includes('input.addEventListener("change",()=>searchController.refresh(false))'),"Fit selections must update cards without filtering search results or rebuilding the directory");
console.log("Strategy fit: five strategies, four labelled colours, grey missing/stale evidence, partial-rule explanations and live checkbox updates verified.");
