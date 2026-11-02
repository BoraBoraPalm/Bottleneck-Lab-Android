"use strict";
const assert=require("node:assert/strict");
const h=require("../docs/holding-horizon.js");

// The app uses past-selected evidence, never the hindsight-best fixed CAGR.
assert.equal(h.plan("year").proposal,"momentum");
assert.equal(h.plan("quarter").proposal,"trend");
assert.equal(h.plan("half").proposal,"trend");
for(const key of ["all","short","longer","invented","__proto__"])
  assert.equal(h.plan(key).proposal,null,"No invented strategy for an untested horizon");
assert.equal(h.describe("momentum","year").state,"match");
assert.equal(h.describe("momentum","quarter").state,"other");
assert.equal(h.describe("trend","quarter").state,"match");
assert.equal(h.describe("trend","half").state,"match");
assert.equal(h.describe("trend","year").state,"other");
assert.match(h.describe("lowRisk","year").short,/Prüftakt.*12 Monate.*Median.*6 Monate/);
assert.match(h.describe("momentum").detail,/6 von 7 Jahren/);
assert.match(h.describe("trend").detail,/5 von 7 Jahren/);

for(const key of ["quality","value","investment","sander","growth","earnings"]){
  for(const horizon of Object.keys(h.horizons))assert.equal(h.describe(key,horizon).state,"open");
  assert.match(h.describe(key).short,/offen/);
}
assert.equal(h.describe("quality").kind,"refresh");
assert.equal(h.describe("earnings").kind,"unknown","App total-income model cannot inherit the EPS-SUE holding result");
assert.match(h.describe("quality").detail,/Portfoliozuordnung/);
assert.match(h.describe("value").detail,/Keine daraus abgeleitete Verkaufsfrist/);
const mixed=h.summary(["momentum","trend"],"half");
assert.equal(mixed.state,"open");
assert.match(mixed.title,/keine geprüfte Haltedauer/);
assert.doesNotMatch(mixed.text,/9 Monate/,"Never average two strategy durations into a fake optimum");
assert.equal(h.summary(["momentum","momentum"]).title,h.summary(["momentum"]).title);
assert.equal(h.describe("__proto__").state,"open");

const memory=new Map(),storage={getItem:key=>memory.get(key)||null,setItem:(key,value)=>memory.set(key,value)};
assert.equal(h.readSettings(storage),null);
assert.equal(h.writeSettings(storage,{horizon:"half",candidates:["trend"],search:["momentum","quality"]}),true);
assert.deepEqual(h.readSettings(storage),{horizon:"half",candidates:["trend"],search:["momentum","quality"]});
h.writeSettings(storage,{horizon:"invented",candidates:["__proto__","unknown"],search:[]});
assert.deepEqual(h.readSettings(storage),{horizon:"all",candidates:["momentum"],search:[]},"Corrupt/obsolete preferences keep one valid ranking factor and may keep no search assessments");
const blocked={getItem(){throw Error("Storage blocked")},setItem(){throw Error("Storage blocked")}};
assert.equal(h.readSettings(blocked),null);assert.equal(h.writeSettings(blocked,{}),false);

// Render a real fit tile with the shipped fit and time modules. A time choice
// must add information without changing the stock-feature assessment colour.
const fit=require("../docs/strategy-fit.js");
class Element{
  constructor(tag){this.tag=tag;this.children=[];this.className="";this.textContent="";}
  setAttribute(){}
  append(...children){this.children.push(...children);}
  appendChild(child){this.children.push(child);return child;}
}
global.document={createElement:tag=>new Element(tag)};
const stock={ticker:"NO_DATA"},parent=new Element("div");
fit.render(parent,stock,["momentum"],{horizon:"year"});
assert.equal(parent.children.length,1);
const tile=parent.children[0].children[0];
assert.match(tile.className,/fund-unknown/,"Missing stock data remain grey even when the strategy's horizon matches");
assert.equal(tile.children.length,3);
assert.match(tile.children[2].textContent,/12 Monate.*Horizont im Testbereich/);
delete global.document;
console.log("Holding horizons: past-only evidence, unknown durations, no fake mixture, resilient preferences and unchanged stock-fit assessments verified.");
