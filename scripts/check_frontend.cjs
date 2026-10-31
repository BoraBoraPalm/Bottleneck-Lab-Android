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
  "count","results","empty","status","reload"]){
  if(!html.includes('id="'+id+'"'))throw new Error("UI control missing: "+id);
}
if(html.includes("<iframe")||html.includes('data-tab=')||html.includes("ATR-Stop")||html.includes("strategie-study.json"))
  throw new Error("Retired tab/iframe/trade-model UI accidentally restored");
if(!html.includes("reference_close_eur")||!html.includes("momentum_12_2"))
  throw new Error("Research app missing EUR reference price or momentum");
console.log("Simple global mobile app: valid JavaScript, one HTML document, no deprecated tabs or trailing code.");
