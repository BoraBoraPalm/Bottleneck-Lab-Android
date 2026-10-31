/* Small responsive SVG chart; no external JS or live third-party network. */
"use strict";
const StockCharts=(()=>{
  const periods={"1M":31,"3M":92,"6M":183,"1J":366,"3J":1096,"5J":1827,"MAX":null};
  const NS="http://www.w3.org/2000/svg",cache=new Map();
  const fmt=(v,d=2)=>Number.isFinite(v)?v.toLocaleString("de-AT",{minimumFractionDigits:d,maximumFractionDigits:d}):"–";
  function selectPoints(points,period){
    if(!Array.isArray(points)||!Object.prototype.hasOwnProperty.call(periods,period))return [];
    if(period==="MAX")return points.slice();
    if(!points.length)return [];
    const last=Date.parse(points[points.length-1][0]+"T00:00:00Z");
    if(!Number.isFinite(last))return [];
    const threshold=new Date(last-periods[period]*86400000).toISOString().slice(0,10);
    return points.filter(p=>p[0]>=threshold);
  }
  function checkedData(data,ticker){
    if(!data||data.version!==1||data.ticker!==ticker||typeof data.currency!=="string"
       ||typeof data.asof!=="string"||!Array.isArray(data.points)||data.points.length<2){
      throw Error("Kursreihe fehlt oder ist ungültig.");
    }
    let previous="";const points=[];
    for(const p of data.points){
      if(!Array.isArray(p)||p.length!==2||!/^20\d{2}-\d\d-\d\d$/.test(p[0])
         ||p[0]<=previous||!Number.isFinite(p[1])||p[1]<=0){
        throw Error("Kursreihe enthält ungültige Werte.");
      }
      previous=p[0];points.push(p);
    }
    if(points[points.length-1][0]!==data.asof)throw Error("Kursreihe und Stichtag stimmen nicht überein.");
    return {...data,points};
  }
  function modelLines(stock,data,enabled){
    if(!enabled||!Number.isFinite(stock.eur_per_unit)||stock.eur_per_unit<=0
       ||stock.price_date!==data.asof||!Number.isFinite(stock.close)||stock.close<=0
       ||Math.abs(data.points[data.points.length-1][1]/stock.close-1)>.02)return [];
    const fields=[["model_buy_limit_eur","Kauf-Limit","#70dbb4"],
                  ["model_initial_stop_eur","Stop-Loss","#ff9e98"]];
    return fields.flatMap(([key,label,color])=>{
      const eur=stock[key],native=eur/stock.eur_per_unit;
      return Number.isFinite(eur)&&eur>0&&Number.isFinite(native)&&native>0
        ? [{value:native,eur,label,color}]:[];
    });
  }
  function el(tag,cls,text){
    const n=document.createElement(tag);
    if(cls)n.className=cls;
    if(text!=null)n.textContent=text;
    return n;
  }
  function svgEl(tag,attrs={},text){
    const n=document.createElementNS(NS,tag);
    for(const [key,value] of Object.entries(attrs))n.setAttribute(key,String(value));
    if(text!=null)n.textContent=text;
    return n;
  }
  function draw(container,details,stock,data,period,showGuides){
    const points=selectPoints(data.points,period);
    if(points.length<2){
      container.replaceChildren(el("p","chart-message","Für diesen Zeitraum sind nicht genügend Handelstage vorhanden."));
      details.replaceChildren();return;
    }
    const lines=modelLines(stock,data,showGuides);
    const prices=points.map(p=>p[1]);
    const extrema=prices.concat(lines.map(l=>l.value));
    let ymin=Math.min(...extrema),ymax=Math.max(...extrema);
    const padding=Math.max((ymax-ymin)*.10,ymax*.008);
    ymin=Math.max(0,ymin-padding);ymax+=padding;
    const W=650,H=265,left=73,right=626,top=20,bottom=222;
    const x=i=>left+(right-left)*i/(points.length-1);
    const y=v=>bottom-(v-ymin)/(ymax-ymin)*(bottom-top);
    const svg=svgEl("svg",{viewBox:"0 0 "+W+" "+H,role:"img",
      "aria-label":"Kursverlauf "+stock.ticker+" "+period+" in "+data.currency+" mit "+lines.length+" Referenzlinien",
      preserveAspectRatio:"xMidYMid meet",class:"price-chart"});
    svg.appendChild(svgEl("title",{},stock.ticker+": bereinigte Schlusskurse "+points[0][0]+" bis "+points[points.length-1][0]));
    for(let i=0;i<=4;i++){
      const value=ymin+(ymax-ymin)*i/4,yy=y(value);
      svg.appendChild(svgEl("line",{x1:left,x2:right,y1:yy,y2:yy,stroke:"#3b5364","stroke-width":.75}));
      svg.appendChild(svgEl("text",{x:left-9,y:yy+4,fill:"#a7bfca","font-size":11,"text-anchor":"end"},fmt(value,Math.abs(value)<10?3:2)));
    }
    const d=points.map((p,i)=>(i?"L":"M")+x(i).toFixed(2)+","+y(p[1]).toFixed(2)).join(" ");
    const fill=d+" L"+x(points.length-1).toFixed(2)+","+bottom+" L"+left+","+bottom+" Z";
    svg.appendChild(svgEl("path",{d:fill,fill:"#2e9986","fill-opacity":.12}));
    svg.appendChild(svgEl("path",{d,fill:"none",stroke:"#5bd7c4",
      "stroke-width":2.3,"stroke-linejoin":"round","stroke-linecap":"round"}));
    for(const line of lines){
      const yy=y(line.value);
      svg.appendChild(svgEl("line",{x1:left,x2:right,y1:yy,y2:yy,
        stroke:line.color,"stroke-width":1.8,"stroke-dasharray":"7 5"}));
    }
    const first=points[0][0],last=points[points.length-1][0];
    const mid=points[Math.floor((points.length-1)/2)][0];
    for(const [xx,day,align] of [[left,first,"start"],[(left+right)/2,mid,"middle"],[right,last,"end"]]){
      svg.appendChild(svgEl("text",{x:xx,y:bottom+19,fill:"#b2c7d1","font-size":11,"text-anchor":align},day));
    }
    svg.appendChild(svgEl("circle",{cx:right,cy:y(prices[prices.length-1]),r:3.5,fill:"#91eed9"}));
    const cursor=svgEl("line",{x1:left,x2:left,y1:top,y2:bottom,
      stroke:"#b8d5d4","stroke-width":1,"stroke-dasharray":"3 4",visibility:"hidden"});
    svg.appendChild(cursor);
    const hit=svgEl("rect",{x:left,y:top,width:right-left,height:bottom-top,
      fill:"transparent","pointer-events":"all"});
    svg.appendChild(hit);
    const tip=el("div","chart-point","Letzter Schlusskurs: "+fmt(prices[prices.length-1],2)+" "+data.currency);
    const tooltip=evt=>{
      const bounds=svg.getBoundingClientRect();
      if(bounds.width===0)return;
      const ratio=(evt.clientX-bounds.left)/bounds.width;
      const idx=Math.max(0,Math.min(points.length-1,
        Math.round((ratio*W-left)/(right-left)*(points.length-1))));
      const cx=x(idx);
      cursor.setAttribute("x1",String(cx));
      cursor.setAttribute("x2",String(cx));
      cursor.setAttribute("visibility","visible");
      tip.textContent=points[idx][0]+": "+fmt(points[idx][1],Math.abs(points[idx][1])<10?3:2)+" "+data.currency;
    };
    hit.addEventListener("pointermove",tooltip);
    hit.addEventListener("pointerdown",tooltip);
    hit.addEventListener("pointerleave",()=>cursor.setAttribute("visibility","hidden"));
    container.replaceChildren(svg,tip);
    details.replaceChildren();
    if(lines.length){
      for(const line of lines){
        const legend=el("span","chart-legend");
        const swatch=el("i","chart-swatch");
        swatch.style.background=line.color;
        legend.append(swatch,document.createTextNode(line.label+": "+fmt(line.value,2)+" "+data.currency+" (≈ "+fmt(line.eur,2)+" €)"));
        details.appendChild(legend);
      }
    }else if(showGuides){
      details.textContent="Keine vergleichbaren Kauf-/Stop-Linien: Kursdatum, Wechselkurs oder Modelldaten stimmen nicht überein.";
    }else{
      details.textContent="Kauf-/Stop-Linien: oben „Kauf-Limit & Stop-Loss anzeigen“ einschalten.";
    }
  }
  function create(container,stock,opts){
    const title=el("div","chart-title","Kursverlauf");
    const toolbar=el("div","chart-periods");
    const output=el("div","chart-output");
    const legend=el("div","chart-legends");
    const note=el("div","chart-note",
      "Bereinigte Schlusskurse, auf den letzten Kurs skaliert · "+stock.currency+
      ". EUR-Linien mit aktuellem Referenzwechselkurs, keine historischen EUR-Kurse oder Broker-Orders.");
    const periodButtons=new Map();
    let chosen="3M",data=null,dead=false;
    const repaint=()=>{
      for(const [k,b] of periodButtons){
        b.classList.toggle("active",k===chosen);
        b.setAttribute("aria-pressed",String(k===chosen));
      }
      if(data&&!dead)draw(output,legend,stock,data,chosen,opts.showTradeLevels());
    };
    for(const period of Object.keys(periods)){
      const button=el("button","chart-period",period);
      button.type="button";
      button.setAttribute("aria-label","Zeitraum "+period);
      button.addEventListener("click",()=>{chosen=period;repaint()});
      toolbar.appendChild(button);
      periodButtons.set(period,button);
    }
    container.replaceChildren(title,toolbar,output,legend,note);
    repaint();
    const load=async()=>{
      if(!stock.chart_available){
        output.textContent="Für diese Aktie ist noch keine historische Kursreihe veröffentlicht. Sie wird bei den nächsten Datenaktualisierungen ergänzt.";
        return;
      }
      output.textContent="Lade historische Kurse …";
      try{
        const symbol=stock.ticker;
        let promised=cache.get(symbol);
        if(!promised){
          promised=fetch("charts/"+encodeURIComponent(symbol)+".json",{cache:"force-cache"})
            .then(resp=>{if(!resp.ok)throw Error("HTTP "+resp.status);return resp.json()})
            .then(raw=>checkedData(raw,symbol));
          cache.set(symbol,promised);
        }
        data=await promised;
        if(dead)return;
        repaint();
      }catch(e){
        cache.delete(stock.ticker);
        if(!dead)output.textContent="Kursreihe derzeit nicht verfügbar ("+String(e.message||e)+").";
      }
    };
    void load();
    return {destroy(){dead=true}};
  }
  return {create,selectPoints,modelLines,checkedData,periods};
})();
if(typeof module!=="undefined"&&module.exports)module.exports=StockCharts;
