/* Independent directory search. Similarity is a text match, never a stock score. */
(function(root){
  "use strict";
  const ALIASES={GOOG:"Google",GOOGL:"Google",META:"Facebook FB"};
  const normalize=value=>String(value||"").toLocaleLowerCase("de-AT").replace(/ß/g,"ss")
    .normalize("NFKD").replace(/\p{M}/gu,"").replace(/[^\p{L}\p{N}]+/gu," ").trim().replace(/\s+/g," ");
  const compact=value=>normalize(value).replace(/ /g,"");
  // Listing in the issuer's ISIN country (SAN.PA for Sanofi), not a foreign
  // line or a US depositary receipt (SNY = ADR, 1/2 share).
  const homeListing=stock=>{
    const isin=String(stock.reference_isin||"").toUpperCase(),country=String(stock.country_code||"").toUpperCase();
    return isin.length===12&&country.length===2&&isin.slice(0,2)===country;
  };
  // Trailing legal forms/share-class words do not distinguish companies:
  // "Sanofi SA", "SIEMENS AG NA O.N." -> "sanofi", "siemens".
  const LEGAL=new Set("sa ag se nv plc inc corp corporation ltd limited oyj abp ab asa spa sca sas kgaa gmbh bv na on o n inh adr ads".split(" "));
  const core=name=>{
    const words=name.split(" ");
    while(words.length>1&&LEGAL.has(words[words.length-1]))words.pop();
    return words.join(" ");
  };
  const depositaryReceipt=stock=>{
    const isin=String(stock.reference_isin||"").toUpperCase(),country=String(stock.country_code||"").toUpperCase();
    return isin.startsWith("US")&&country.length===2&&country!=="US";
  };
  function prepare(catalog,stocks){
    const byTicker=new Map();
    for(const row of catalog||[]){
      if(row&&typeof row.ticker==="string"&&row.ticker.length<=30)
        byTicker.set(row.ticker,{...row});
    }
    // Price/fundamental observations remain usable regardless of eligibility.
    // Keep a directory name when a quote only carries the ticker as its name.
    for(const row of stocks||[]){
      if(!row||typeof row.ticker!=="string")continue;
      const meta=byTicker.get(row.ticker)||{};
      const merged={...meta,...row};
      if((!row.name||row.name===row.ticker)&&meta.name)merged.name=meta.name;
      byTicker.set(row.ticker,merged);
    }
    return Array.from(byTicker.values(),stock=>{
      const name=normalize(stock.name),ticker=compact(stock.ticker);
      const alias=normalize(ALIASES[stock.ticker]);
      return {stock,name,core:core(name),ticker,base:compact(String(stock.ticker).split(".")[0]),alias,isin:compact(stock.reference_isin||stock.tr_isin),
        tokens:Array.from(new Set((name+" "+alias).trim().split(" "))).filter(Boolean).slice(0,25)};
    });
  }
  function distance(a,b,limit){
    // Optimal-string-alignment distance includes adjacent transpositions.
    if(Math.abs(a.length-b.length)>limit)return limit+1;
    let previousPrevious=null,previous=Array.from({length:b.length+1},(_,i)=>i);
    for(let i=1;i<=a.length;i++){
      const current=[i];
      let best=i;
      for(let j=1;j<=b.length;j++){
        current[j]=Math.min(current[j-1]+1,previous[j]+1,previous[j-1]+(a[i-1]===b[j-1]?0:1));
        if(previousPrevious&&i>1&&j>1&&a[i-1]===b[j-2]&&a[i-2]===b[j-1])
          current[j]=Math.min(current[j],previousPrevious[j-2]+1);
        best=Math.min(best,current[j]);
      }
      if(best>limit)return limit+1;
      previousPrevious=previous;previous=current;
    }
    return previous[b.length];
  }
  function find(index,query,limit=30){
    const q=normalize(String(query||"").slice(0,120)),cq=compact(q),terms=q.split(" ").filter(Boolean).slice(0,6);
    if(!q)return {items:[],total:0};
    // An exact ticker lists only that ticker on all exchanges ("SAP" -> SAP,
    // SAP.DE), home listing first; no fuzzy names.
    const exact=(index||[]).some(row=>cq===row.ticker)
      ?(index||[]).filter(row=>cq===row.ticker||cq===row.base)
        .sort((a,b)=>Number(homeListing(b.stock))-Number(homeListing(a.stock))||Number(b.ticker===cq)-Number(a.ticker===cq))
      :[];
    if(exact.length)return {items:exact.slice(0,Math.max(0,Math.min(75,limit))).map(row=>({stock:row.stock,score:1000,kind:"Börsenticker"})),total:exact.length};
    const hits=[];
    for(const row of index||[]){
      let score=0,kind="Name / Ticker";
      if(cq===row.ticker)score=1000;
      else if(cq&&cq===row.isin)score=990;
      else if(q===row.name||q===row.core||q===row.alias)score=950;
      else if(cq&&cq===row.base)score=900;
      else if(q.length>=2&&row.ticker.startsWith(cq))score=850;
      else if(q.length>=2&&row.name.startsWith(q))score=800;
      else if(q.length>=2&&terms.every(term=>row.tokens.some(token=>token.startsWith(term))))score=750;
      else if(q.length>=2&&(row.name.includes(q)||row.alias.includes(q)))score=700;
      else if(q.length>=4){
        let edits=0,matched=true;
        for(const term of terms){
          if(row.tokens.some(token=>token.startsWith(term)))continue;
          if(term.length<4){matched=false;break;}
          const max=term.length>=8?2:1;
          let best=max+1;
          for(const token of row.tokens){
            if(Math.abs(token.length-term.length)>max)continue;
            best=Math.min(best,distance(term,token,max));
            if(best===1)break;
          }
          if(best>max){matched=false;break;}
          edits+=best;
        }
        if(matched){score=500-edits*20;kind="Ähnlicher Name";}
      }
      if(score)hits.push({stock:row.stock,score,kind});
    }
    hits.sort((a,b)=>b.score-a.score
      ||Number(homeListing(b.stock))-Number(homeListing(a.stock))
      ||Number(Number.isFinite(b.stock.reference_close_eur))-Number(Number.isFinite(a.stock.reference_close_eur))
      ||a.stock.ticker.localeCompare(b.stock.ticker));
    return {items:hits.slice(0,Math.max(0,Math.min(75,limit))),total:hits.length};
  }
  function create(options){
    const {input,form,status,results,suggestions,makeCard,getStocks}=options;
    let directory=[],index=prepare([],getStocks()),loading=null,loaded=false,failed=false;
    let timer=null,request=0,lastQuery="",submitted=false;
    function rebuild(){index=prepare(directory,getStocks());}
    async function ensure(){
      if(loaded)return;
      if(loading)return loading;
      status.textContent="Lade Aktienverzeichnis …";
      loading=(async()=>{
        try{
          const response=await fetch("search-index.json",{cache:"no-cache"});
          if(!response.ok)throw Error("HTTP "+response.status);
          const payload=await response.json();
          if(payload.version!==1||!Array.isArray(payload.stocks)||payload.stocks.length>150000)
            throw Error("Ungültiges Verzeichnis");
          directory=payload.stocks;loaded=true;failed=false;
        }catch(error){failed=true;}
        finally{loading=null;rebuild();}
      })();
      return loading;
    }
    function fillSuggestions(query){
      suggestions.replaceChildren();
      if(normalize(query).length<2)return;
      for(const hit of find(index,query,5).items){
        const option=document.createElement("button");
        option.type="button";option.className="search-suggestion";
        option.textContent=(hit.stock.name||hit.stock.ticker)+" · "+hit.stock.ticker
          +(hit.stock.exchange?" · "+hit.stock.exchange:"");
        option.addEventListener("click",()=>{input.value=hit.stock.ticker;search(input.value);});
        suggestions.appendChild(option);
      }
    }
    function show(query){
      const opened=new Set(Array.from(results.querySelectorAll("details.stock[open]"),node=>node.dataset.ticker));
      results.replaceChildren();
      const found=find(index,query,30);
      if(!normalize(query)){
        status.textContent="Gib einen Firmennamen oder Börsenticker ein. Die Suche ist unabhängig von den Kandidaten-Filtern.";
        return;
      }
      const suffix=failed?" Das Namensverzeichnis ist derzeit nicht erreichbar; gesucht wird in den vorhandenen Kursdatensätzen.":"";
      status.textContent=(found.total
        ?found.total.toLocaleString("de-AT")+" Treffer · "+found.items.length+" angezeigt · unabhängig von Strategie, Region und Trade-Republic-Filter."
        :"Keine passenden Titel gefunden. Probiere einen kürzeren Firmennamen oder den Börsenticker.")+suffix;
      for(const hit of found.items){
        const card=makeCard(hit.stock,hit.kind);
        card.dataset.ticker=hit.stock.ticker;
        if(opened.has(hit.stock.ticker))card.open=true;
        results.appendChild(card);
      }
    }
    async function search(query){
      const run=++request;
      submitted=true;lastQuery=String(query||"").trim();
      await ensure();
      if(run!==request)return;
      suggestions.replaceChildren();show(lastQuery);
    }
    form.addEventListener("submit",event=>{event.preventDefault();clearTimeout(timer);search(input.value);});
    input.addEventListener("input",()=>{
      clearTimeout(timer);++request;submitted=false;
      results.replaceChildren();
      if(!normalize(input.value)){
        suggestions.replaceChildren();show("");return;
      }
      status.textContent="Mit „Suchen“ oder Enter alle passenden Titel anzeigen.";
      timer=setTimeout(async()=>{
        const run=++request,query=input.value;
        await ensure();
        if(run!==request)return;
        fillSuggestions(query);
        status.textContent=failed?"Verzeichnis derzeit nicht erreichbar. Suche in den vorhandenen Kursdatensätzen mit „Suchen“."
          :suggestions.childElementCount?"Vorschlag antippen oder mit „Suchen“ / Enter alle Treffer anzeigen."
          :"Mit „Suchen“ oder Enter nach passenden Titeln suchen.";
      },180);
    });
    return {
      async activate(){await ensure();if(submitted)show(lastQuery);else if(!normalize(input.value))show("");},
      refresh(reindex=true){if(reindex)rebuild();if(submitted)show(lastQuery);},
      search
    };
  }
  const api={normalize,prepare,distance,find,create,homeListing,depositaryReceipt};
  if(typeof module!=="undefined"&&module.exports)module.exports=api;
  root.StockSearch=api;
})(typeof window!=="undefined"?window:globalThis);
