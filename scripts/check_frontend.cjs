const fs = require("node:fs");
const file = fs.readFileSync("docs/index.html", "utf8");
const opening = (file.match(/<script(?:\s[^>]*)?>/gi) || []).length;
const closing = (file.match(/<\/script\s*>/gi) || []).length;
const htmlOpen = (file.match(/<html(?:\s[^>]*)?>/gi) || []).length;
const htmlClose = (file.match(/<\/html\s*>/gi) || []).length;
if (opening !== 1 || closing !== 1) throw new Error("Expected exactly one script block, found " + opening + " opening and " + closing + " closing tags");
if (htmlOpen !== 1 || htmlClose !== 1) throw new Error("Expected exactly one complete HTML document");
if (!/<\/html\s*>\s*$/i.test(file)) throw new Error("Stray content after </html>: possible duplicated script displayed as webpage text");
const block = file.match(/<script(?:\s[^>]*)?>([\s\S]*?)<\/script\s*>/i);
if (!block) throw new Error("Frontend JavaScript not found");
new Function(block[1]);
for (const id of ["coverage","top","listCount","search","table","news","refresh","status","detail","trOnly"]) {
  if (!file.includes('id="'+id+'"')) throw new Error("Missing UI element: " + id);
}
console.log("Frontend verified: single script, complete HTML, no trailing source, required controls present.");


// Isolated research tab: keep original app's single inline script untouched.
const researchPage=fs.readFileSync("docs/strategies.html","utf8");
const inner=(researchPage.match(/<script>([\s\S]*?)<\/script>/gi)||[]);
if (inner.length!==1 || !/<\/html>\s*$/i.test(researchPage))
  throw new Error("Research tab has duplicate script or trailing code");
const researchJs=researchPage.match(/<script>([\s\S]*?)<\/script>/i);
new Function(researchJs[1]);
if (!file.includes('data-tab="strategies"')||!file.includes('id="tab-strategies"')||!file.includes('id="strategiesFrame"'))
  throw new Error("Research tab not linked in main app");
if (!researchPage.includes('strategy-study.json'))throw new Error("Research JSON not linked");
const study=JSON.parse(fs.readFileSync("docs/strategy-study.json","utf8"));
const modelNames=Object.keys(study.periods.eur_2000.model);
if(modelNames.length!==12)throw new Error("Expected 12 strategies including benchmark");
if(Object.keys(study.periods.usd_full.model).length!==12)throw new Error("Missing USD strategy rows");
if(study.costs.headwindsQvm.length!==18)throw new Error("Missing cost sensitivity windows");
for(const [name,parts] of Object.entries(study.weights)){
  const sum=Object.values(parts).reduce((a,b)=>a+b,0);
  if(Math.abs(sum-100)>0.1)throw new Error("Weights do not total 100 for "+name);
}
for(const name of modelNames)for(const [periodKey,period] of Object.entries(study.periods)){
  const row=period.model[name];
  if(!row||!Number.isFinite(row.cagr)||!Number.isFinite(row.maxDrawdown)
     ||!Number.isFinite(row.correctedP)||!Number.isFinite(row.outperformance5y))
    throw new Error("Incomplete study row: "+periodKey+" "+name);
}
console.log("Research panel validated: 12 strategies, 2 periods, 18 cost scenarios, no trailing HTML.");
