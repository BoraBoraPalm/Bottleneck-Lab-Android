/* Filed annual financials. Colours describe a metric, never a buy/sell signal. */
(function(root){
  "use strict";
  const STATES={
    green:{label:"Sehr gut"},yellow:{label:"Geht so"},
    orange:{label:"Eher schwach"},red:{label:"Vorsicht"},
    unknown:{label:"Daten fehlen"}
  };
  // Deliberately explicit, own orientation thresholds; not sector benchmarks.
  const RULES=[
    {key:"revenue_growth_yoy",label:"Umsatzwachstum",limits:[.10,0,-.10],
     formula:"Umsatz / Vorjahresumsatz − 1",thresholds:"Grün ≥10 % · Gelb ≥0 % · Orange ≥−10 % · Rot <−10 %"},
    {key:"net_income_growth_yoy",label:"Gewinnwachstum",limits:[.15,0,-.20],
     formula:"Jahresgewinn / positiver Vorjahresgewinn − 1",thresholds:"Grün ≥15 % · Gelb ≥0 % · Orange ≥−20 % · Rot <−20 %; laufender Verlust: Rot"},
    {key:"profit_margin",label:"Nettogewinnmarge",limits:[.15,.05,0],
     formula:"Jahresgewinn / Umsatz",thresholds:"Grün ≥15 % · Gelb ≥5 % · Orange ≥0 % · Rot <0 %"},
    {key:"operating_cashflow_margin",label:"Operativer Cashflow",limits:[.15,.05,0],sensitive:true,
     formula:"Operativer Cashflow / Umsatz",thresholds:"Marge: Grün ≥15 % · Gelb ≥5 % · Orange ≥0 % · Rot <0 %"},
    {key:"free_cashflow_margin",label:"Freier Cashflow",limits:[.10,.03,0],sensitive:true,
     formula:"(Operativer Cashflow − Sachinvestitionen) / Umsatz",thresholds:"Marge: Grün ≥10 % · Gelb ≥3 % · Orange ≥0 % · Rot <0 %"},
    {key:"equity_ratio",label:"Eigenkapitalquote",limits:[.40,.20,.10],sensitive:true,
     formula:"Eigenkapital / Bilanzsumme",thresholds:"Grün ≥40 % · Gelb ≥20 % · Orange ≥10 % · Rot <10 %"},
    {key:"current_ratio",label:"Kurzfristige Liquidität",limits:[2,1.2,1],ratio:true,sensitive:true,
     formula:"Umlaufvermögen / kurzfristige Verbindlichkeiten",thresholds:"Grün ≥2,0× · Gelb ≥1,2× · Orange ≥1,0× · Rot <1,0×"},
    {key:"liabilities_to_equity",label:"Verbindlichkeiten / EK",limits:[1,2,4],lower:true,ratio:true,sensitive:true,
     formula:"Gesamte Verbindlichkeiten / Eigenkapital; inkl. nicht verzinster Verpflichtungen",thresholds:"Grün ≤1× · Gelb ≤2× · Orange ≤4× · Rot >4×; Eigenkapital ≤0: Rot"}
  ];
  const finite=x=>typeof x==="number"&&Number.isFinite(x);
  const format=(n,d=1)=>finite(n)?n.toLocaleString("de-AT",{maximumFractionDigits:d,minimumFractionDigits:d}):"–";
  const percent=n=>finite(n)?format(n*100)+" %":"–";
  function money(n,currency){
    if(!finite(n))return "–";
    const a=Math.abs(n);
    const divisor=a>=1e12?1e12:a>=1e9?1e9:a>=1e6?1e6:1;
    const unit=divisor===1e12?" Bio.":divisor===1e9?" Mrd.":divisor===1e6?" Mio.":"";
    return format(n/divisor,a<1e6?0:1)+unit+" "+(currency||"USD");
  }
  function rating(value,rule){
    if(!finite(value))return "unknown";
    for(let i=0;i<rule.limits.length;i++){
      if(rule.lower?value<=rule.limits[i]:value>=rule.limits[i])return ["green","yellow","orange"][i];
    }
    return "red";
  }
  function reportState(f,today){
    if(!f||typeof f!=="object")return "missing";
    const now=new Date(today||Date.now());
    const end=new Date(f.fy_end+"T00:00:00Z");
    const filed=new Date(f.filed+"T00:00:00Z");
    if(!Number.isFinite(+now)||!Number.isFinite(+end)||!Number.isFinite(+filed))return "unverified";
    if(end>now||filed>now)return "unverified";
    return (now-end)/86400000>550?"stale":"current";
  }
  function metrics(stock,options){
    const f=stock.fundamentals||{};
    const freshness=reportState(stock.fundamentals,options?.today);
    const financial=/financ|bank|insurance|versicherung|finanz|reit/i.test(
      (stock.stock_sector||"")+" "+(stock.name||""));
    return RULES.map(rule=>{
      // Older cached records still supply their explicitly reported basic values.
      let value=f[rule.key];
      if(rule.key==="operating_cashflow_margin"&&!finite(value)&&finite(f.operating_cashflow)&&f.revenue>0)
        value=f.operating_cashflow/f.revenue;
      let state=rating(value,rule);
      let text=rule.ratio?(finite(value)?format(value)+"×":"–"):percent(value);
      let detail=rule.formula;
      let label=STATES[state].label;
      if(rule.key==="revenue_growth_yoy")detail="Umsatz: "+money(f.revenue,f.currency);
      if(rule.key==="net_income_growth_yoy"){
        detail="Jahresgewinn: "+money(f.net_income,f.currency);
        if(finite(f.net_income)&&f.net_income<=0){state="red";label="Vorsicht";if(!finite(value))text=f.net_income<0?"Verlust":"Kein Gewinn";}
        else if(f.earnings_comparison==="turnaround"){state="yellow";label="Gewinnwende";text="Verlust → Gewinn";}
      }
      if(rule.key==="operating_cashflow_margin")detail=money(f.operating_cashflow,f.currency)+" · Marge am Umsatz";
      if(rule.key==="free_cashflow_margin")detail=money(f.free_cashflow,f.currency)+" · nach Sachinvestitionen";
      if(rule.key==="liabilities_to_equity"&&finite(f.equity)&&f.equity<=0){
        state="red";label="Vorsicht";text="EK ≤ 0";detail="Keine sinnvolle positive EK-Basis";
      }
      if(state==="unknown")label="Daten fehlen";
      // Never colour an unverified or old statement as good (or bad).
      if(freshness!=="current"){
        state="unknown";
        label=freshness==="stale"?"Bericht veraltet":freshness==="missing"?"Daten fehlen":"Datum ungeprüft";
        if(freshness==="unverified"){text="–";detail="Berichtsdatum nicht verifizierbar";}
      }else if(financial&&rule.sensitive&&state!=="unknown"){
        state="unknown";label="Branchenspezifisch";
      }
      return {...rule,name:rule.label,value,text,detail,state,label,freshness};
    });
  }
  function add(parent,tag,text,cls){
    const node=document.createElement(tag);
    if(cls)node.className=cls;
    if(text!=null)node.textContent=text;
    parent.appendChild(node);
    return node;
  }
  function preview(parent,stock){
    const row=add(parent,"div",null,"fund-preview");
    row.setAttribute("aria-label","Fundamentaldaten im Überblick");
    if(!stock.fundamentals){
      add(row,"span",stock.fundamentals_checked_at?"Fundamentaldaten fehlen":"Fundamentaldaten noch nicht geprüft","fund-pill fund-unknown");
      return;
    }
    for(const m of metrics(stock).filter(m=>["revenue_growth_yoy","profit_margin","operating_cashflow_margin"].includes(m.key))){
      const short=m.key==="revenue_growth_yoy"?"Umsatz":m.key==="profit_margin"?"Marge":"Cashflow-Marge";
      const pill=add(row,"span",short+" "+m.text,"fund-pill fund-"+m.state);
      pill.title=m.label+" · "+m.formula+" · "+m.thresholds;
      pill.setAttribute("aria-label",short+": "+m.text+". "+m.label);
      add(pill,"span"," · "+m.label,"fund-pill-state");
    }
  }
  function render(parent,stock){
    const section=add(parent,"section",null,"fund-panel");
    section.setAttribute("aria-label","Fundamentaldaten "+stock.ticker);
    add(section,"h3","Fundamentaldaten","fund-title");
    const f=stock.fundamentals;
    const legend=add(section,"div",null,"fund-legend");
    for(const key of ["green","yellow","orange","red"])
      add(legend,"span",STATES[key].label,"fund-pill fund-"+key);
    if(!f){
      add(section,"p",stock.fundamentals_checked_at
        ?"Für diese Aktie sind derzeit keine verifizierbaren Jahreszahlen verfügbar. Zuletzt geprüft: "+stock.fundamentals_checked_at+"."
        :"Für diese Aktie liegen noch keine verifizierten Jahreszahlen vor. Die Abdeckung wird bei den Datenaktualisierungen schrittweise erweitert.","fund-empty");
      add(section,"p","Die aktuelle Quelle deckt vor allem US-Unternehmen ab. Fehlende Daten bleiben grau.","fund-note");
      return;
    }
    add(section,"p","Geschäftsjahr bis "+(f.fy_end||"unbekannt")+" · Zuletzt berichtet: "+(f.filed||"unbekannt"),"fund-date");
    const freshness=reportState(f);
    if(freshness!=="current")add(section,"p",freshness==="stale"
      ?"Dieser Abschluss ist älter als 550 Tage. Werte zur Information; Farbbewertung ausgesetzt."
      :"Das Berichtsdatum lässt sich nicht bestätigen. Werte und Farbbewertung ausgesetzt.","fund-empty");
    const grid=add(section,"div",null,"fund-grid");
    for(const m of metrics(stock)){
      const tile=add(grid,"div",null,"fund-tile fund-"+m.state);
      tile.title=m.formula+". "+m.thresholds;
      tile.setAttribute("aria-label",m.name+": "+m.text+". "+m.label);
      add(tile,"span",m.label,"fund-state");
      add(tile,"small",m.key==="operating_cashflow_margin"?"Operative Cashflow-Marge":m.key==="free_cashflow_margin"?"Freie Cashflow-Marge":m.name,"fund-label");
      add(tile,"strong",m.text,"fund-value");
      add(tile,"span",m.detail,"fund-detail");
    }
    const source=add(section,"p","Quelle: "+(f.source||"SEC-XBRL"),"fund-source");
    if((f.source||"").includes("TGMCharts")){
      const link=add(source,"a"," · TGMCharts");
      link.href="https://tgmcharts.com/";link.target="_blank";link.rel="noopener noreferrer";
    }
    if(Number.isInteger(f.cik)&&f.cik>0){
      const link=add(source,"a"," · SEC-Berichte");
      link.href="https://www.sec.gov/edgar/browse/?CIK="+f.cik;link.target="_blank";link.rel="noopener noreferrer";
    }
    add(section,"p","Farben sind eigene, grobe Orientierungswerte je Kennzahl und branchenabhängig. Sie bewerten weder den Aktienpreis noch die Aktie als Ganzes. Bei Banken, Versicherungen und REITs bleiben Cashflow- und Bilanzquoten ohne Standardampel.","fund-note");
    const help=add(section,"details",null,"fund-help");
    add(help,"summary","Berechnung und Farbgrenzen");
    const list=add(help,"ul");
    for(const rule of RULES)add(list,"li",rule.label+": "+rule.formula+". "+rule.thresholds+".");
    add(help,"p","Gewinnwachstum wird nur mit positivem Vorjahresgewinn prozentual verglichen. Eine Gewinnwende wird gelb markiert. Fehlende Kennzahlen werden nicht geschätzt. KGV und Dividendenrendite sind aus dieser Datenquelle derzeit nicht zuverlässig verfügbar.","fund-note");
    const link=add(help,"a","Grundlagen zu Geschäftsberichten (SEC)");
    link.href="https://www.sec.gov/reportspubs/investor-publications/investorpubsbegfinstmtguidehtm.html";
    link.target="_blank";link.rel="noopener noreferrer";
  }
  const api={rules:RULES,rating,reportState,metrics,preview,render};
  if(typeof module!=="undefined"&&module.exports)module.exports=api;
  else root.StockFundamentals=api;
})(typeof window!=="undefined"?window:globalThis);
