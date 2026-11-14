// Evidence labels: every figure the app quotes must equal the archived result files of the
// strategy audit (research/tests/2026-11-14-strategy-audit), and no strategy may be left unlabelled.
const assert=require("node:assert/strict");
const fs=require("node:fs");
const path=require("node:path");
const data=require("../docs/evidence-data.js");
const evidence=require("../docs/evidence.js");
const fit=require("../docs/strategy-fit.js");
const OUT=path.join(__dirname,"../research/tests/2026-11-14-strategy-audit/files/output");

function csv(file){
  // Minimal RFC-4180 reader (quoted fields may contain commas).
  const rows=[];let row=[],cell="",quoted=false;
  const text=fs.readFileSync(path.join(OUT,file),"utf8");
  for(let i=0;i<text.length;i++){
    const c=text[i];
    if(quoted){
      if(c==='"'&&text[i+1]==='"'){cell+='"';i++;}
      else if(c==='"')quoted=false;else cell+=c;
    }else if(c==='"')quoted=true;
    else if(c===","){row.push(cell);cell="";}
    else if(c==="\n"){row.push(cell);rows.push(row);row=[];cell="";}
    else if(c!=="\r")cell+=c;
  }
  const [head,...body]=rows;
  return body.filter(r=>r.length===head.length).map(r=>Object.fromEntries(head.map((h,i)=>[h,r[i]])));
}
const pc=v=>Math.round(1000*Number(v))/10;

// 1. Generated figures equal the archive (percentage points, one decimal).
const all=new Map(csv("all_strategies.csv").map(r=>[r.id,r]));
assert.equal(all.size,data.study.strategies);
for(const [id,r] of Object.entries(data.rows)){
  const a=all.get(id);assert.ok(a,"Archived strategy missing: "+id);
  assert.equal(r.net,pc(a.active),id+" net");
  assert.equal(r.gross,pc(a.gross_active),id+" gross");
  assert.equal(r.hold,pc(a.hold_active),id+" control period");
  assert.equal(r.recent,pc(a.recent_active),id+" last 15 years");
  assert.equal(r.verdict,a.verdict,id+" verdict");
  assert.equal(r.maxdd,Math.round(100*Number(a.maxdd)),id+" drawdown");
}
const stocks=new Map(csv("exploratory_stocks.csv").map(r=>[r.id,r]));
for(const [id,r] of Object.entries(data.stocks))assert.equal(r.net,pc(stocks.get(id).active),id+" stock rule");
const summary=JSON.parse(fs.readFileSync(path.join(OUT,"summary.json"),"utf8"));
assert.deepEqual(data.study.verdicts,summary.verdict_counts);
assert.equal(data.osap.afterPublication,pc(summary.osap.mean_gross_active_postpub));
const products=[...all.values()].filter(r=>r.module==="C5");
assert.equal(Object.values(data.etf).reduce((n,g)=>n+g.n,0),products.length);
assert.equal(data.etf.Momentum.ahead,products.filter(r=>r.family.endsWith("Momentum")&&Number(r.active)>0).length);

// 2. Every selectable strategy carries a label, a plain verdict and complete sentences.
assert.deepEqual(Object.keys(evidence.strategies).sort(),Object.keys(fit.names).sort());
for(const key of Object.keys(fit.names)){
  const e=evidence.describe(key);
  assert.ok(Object.hasOwn(evidence.tiers,e.tier),key);
  assert.ok(e.verdict.length>20&&e.facts.length>=1,key);
  for(const text of [e.chip,e.verdict,...e.facts])assert.ok(!/undefined|NaN|null|–;|: –/.test(text),key+": "+text);
}
assert.equal(evidence.describe("unknown"),null);
for(const text of [...evidence.findings(),...evidence.notAdded(),...evidence.entryExit.facts(data)])
  assert.ok(!/undefined|NaN|null|: –/.test(text),text);

// 3. The labels follow the archived verdicts; nothing is called reliable.
assert.equal(evidence.describe("sander").tier,"against");
assert.equal(all.get("IND_DIP").verdict,"Evidenz dagegen");
assert.ok(Number(stocks.get("S_DIP").active)<0&&Number(stocks.get("S_DIP").t)<-1.645);
for(const key of ["momentum","trend","quality"])assert.equal(evidence.describe(key).tier,"hint",key);
for(const id of ["MOM_D10","MOM_BIG","IND_MOM122","IND_TREND","OSAP_GP","QUAL_BIG","LOWVOL_Q1","VAL_Q5","INV_Q1"])
  assert.notEqual(all.get(id).verdict,"verlässlich",id);
assert.equal(evidence.describe("lowRisk").tier,"none");
assert.ok(data.rows.LOWVOL_Q1.net<=0&&data.rows.LOWVOL_Q1.maxdd>data.rows.LOWVOL_Q1.marketMaxdd);
assert.ok(!Object.values(evidence.tiers).some(t=>/verlässlich|sicher|garant|belegt/i.test(
  (t.label+" "+t.chip).replace(/nicht gesichert|kein Mehrertrag belegt/gi,""))),"No tier may promise an advantage");
assert.equal(evidence.pp(1.25),"+1,3");assert.equal(evidence.pp(-0.5),"−0,5");assert.equal(evidence.pp(0),"±0,0");assert.equal(evidence.pp(NaN),"–");

// 4. Rendering in the page: one chip per candidate strategy, the panel lists all strategies and the study link.
function node(tag){
  const n={tag,children:[],className:"",textContent:"",dataset:{},title:"",
    appendChild(c){n.children.push(c);c.parent=n;return c;},
    append(...items){for(const c of items)n.children.push(typeof c==="string"?{tag:"#text",textContent:c,className:"",children:[]}:c);},
    querySelector(sel){return n.find(x=>x.className&&("."+x.className.split(" ")[0])===sel);},
    find(test){for(const c of n.children){if(test(c))return c;const hit=c.find?.(test);if(hit)return hit;}return null;},
    all(test,out=[]){for(const c of n.children){if(test(c))out.push(c);c.all?.(test,out);}return out;}};
  return n;
}
globalThis.document={createElement:node};
const panel=node("div");evidence.render(panel);
const blocks=panel.all(x=>x.className.startsWith("evidence-block"));
assert.equal(blocks.length,Object.keys(fit.names).length+2);
assert.ok(panel.all(x=>x.tag==="a").some(a=>a.href===evidence.studyUrl&&a.rel==="noopener noreferrer"));
const labels=Object.keys(fit.names).map(key=>{
  const host=node("span"),label={querySelector:()=>host},input={dataset:{factor:key},closest:()=>label};
  return {input,host};
});
evidence.decorate({querySelectorAll:()=>labels.map(l=>l.input)});
evidence.decorate({querySelectorAll:()=>labels.map(l=>l.input)});
for(const {input,host} of labels){
  assert.equal(host.children.length,1,"exactly one chip after repeated decoration");
  assert.equal(host.children[0].textContent,evidence.describe(input.dataset.factor).chip);
}
delete globalThis.document;
console.log("Evidence labels: all figures equal the archived audit, every strategy labelled, nothing called reliable, page wiring verified.");
