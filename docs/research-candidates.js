/* Bottleneck Lab independent research candidate UI.
 * This script ONLY renders v5 snapshot.research_candidates.
 * Does not modify baseline trade signals, model sliders, or order logic.
 * All company/external text is rendered via textContent, never innerHTML.
 */
(() => {
  'use strict';
  const $ = id => document.getElementById(id);
  const num = (v,d=2) => Number.isFinite(v)
    ? v.toLocaleString('de-AT',{minimumFractionDigits:d,maximumFractionDigits:d}) : '–';
  const eur = v => Number.isFinite(v) ? num(v,2)+' €' : '–';
  let snapshot=null;
  const choices = {
    quality_momentum:'Quality + Momentum',
    quality_value_momentum:'Quality + Value + Momentum',
    global_momentum:'Weltweites 12–2-Monats-Momentum',
    bottleneck_hypotheses:'Engpass-Exposition (Hypothesen)',
    overlap:'Überschneidungen'
  };
  const add=(parent,tag,content,cls)=>{
    const el=document.createElement(tag);
    if(cls)el.className=cls;
    if(content!==undefined&&content!==null)el.textContent=String(content);
    parent.append(el);
    return el;
  };
  const linked=(parent,text,url)=>{
    if(!url||typeof url!=='string'||!url.startsWith('https://'))return;
    const link=add(parent,'a',text);
    link.href=url;
    link.target='_blank';
    link.rel='noopener noreferrer';
    return link;
  };
  const announce=()=>{
    if(window.parent!==window)window.parent.postMessage({
      bottleneckResearchHeight:Math.ceil(document.documentElement.scrollHeight)
    },location.origin==='null'?'*':location.origin);
  };
  const quality=(r,kind)=>{
    const list=[];
    if(Number.isFinite(r.momentum_12_2_pct))list.push('12–2-Monats-Momentum '+num(r.momentum_12_2_pct,1)+' %');
    if(r.factors){
      if(Number.isFinite(r.factors.quality))list.push('Quality '+num(r.factors.quality,1)+'/100');
      if(Number.isFinite(r.factors.momentum))list.push('Momentum-Rang '+num(r.factors.momentum,1)+'/100');
      if(Number.isFinite(r.factors.value))list.push('Value '+num(r.factors.value,1)+'/100');
      if(r.factors.quality_components)list.push('Quality-Kennzahlen '+r.factors.quality_components);
    }
    if(kind==='bottleneck_hypotheses')list.push('Thematisch zugeordnet, Engpasswirkung nicht geprüft');
    return list.join(' · ');
  };
  function card(r,i,kind){
    const out=add(document.createDocumentFragment(),'article',null,'research-stock');
    const heading=add(out,'div',null,'research-stock-title');
    const info=add(heading,'div');
    add(info,'strong',(i+1)+'. '+r.ticker+' · '+r.name);
    add(info,'div',(r.region?r.region+' · ':'')+(r.country?r.country+' · ':'')+r.theme,'muted research-small');
    if(kind==='bottleneck_hypotheses'){
      add(heading,'span','Branchenhypothese','research-tag research-caution');
    }else if(kind==='global_momentum'){
      add(heading,'span',num(r.momentum_12_2_pct,1)+' %','research-tag');
    }else if(kind==='overlap'){
      add(heading,'span',Object.keys(r.appears_in||{}).length+' Strategien','research-tag');
    }else{
      add(heading,'span',num(r.score,1)+'/100','research-tag');
    }
    const flags=add(out,'div',null,'research-flags');
    add(flags,'span',r.tr_at_listed?'TR-AT-ISIN bestätigt':'TR-AT nicht bestätigt',
      r.tr_at_listed?'research-tag':'research-tag research-caution');
    if(r.tr_at_listed&&r.tr_isin)add(flags,'span','ISIN: '+r.tr_isin,'muted research-small');
    if(kind==='global_momentum'&&Number.isFinite(r.avg_turnover_20d_eur)){
      add(out,'div','20-Tage-Umsatz (EUR/Tag): '+eur(r.avg_turnover_20d_eur),'muted research-small');
    }
  const prices=add(out,'div',null,'research-metrics');
    add(prices,'div',null,'research-metric').append(
      add(document.createDocumentFragment(),'small','EUR-Referenzkurs'),
      add(document.createDocumentFragment(),'strong',eur(r.close_eur)));
    add(prices,'div',null,'research-metric').append(
      add(document.createDocumentFragment(),'small','Kauf-Limit (nur Modell)'),
      add(document.createDocumentFragment(),'strong',eur(r.illustrative_buy_eur)));
    add(prices,'div',null,'research-metric').append(
      add(document.createDocumentFragment(),'small','Stop (nur Modell)'),
      add(document.createDocumentFragment(),'strong',eur(r.illustrative_stop_eur)));
    if(kind==='overlap'){
      const overlap=Object.entries(r.appears_in||{}).map(([k,n])=>(choices[k]||k)+' #'+n);
      add(out,'p','In mehreren Kandidatenlisten: '+overlap.join(' · '),'research-small');
    }else{
      add(out,'p',quality(r,kind),'research-small');
    }
    const evidence=add(out,'div',null,'research-evidence');
    add(evidence,'div','Kursstand: '+(r.price_date||'unbekannt')+' · FX: '+(r.fx_date||'unbekannt')+
        ' · Kursquelle: '+(r.price_source||'unbekannt'),'muted research-small');
    if(r.sec_filing_date){
      const secrow=add(evidence,'div',null,'research-small');
      add(secrow,'span','SEC-Jahresabschluss eingereicht '+r.sec_filing_date+' · ');
      linked(secrow,'Originaldaten',r.sec_source_url);
    }else if(kind!=='bottleneck_hypotheses'){
      add(evidence,'div','Keine verifizierten SEC-Bilanzdaten für diesen Titel','muted research-small');
    }
    if(kind==='bottleneck_hypotheses'){
      add(evidence,'div','Hypothese: '+(r.thematic_hypothesis||r.theme),'research-small');
      const n=Array.isArray(r.theme_news)?r.theme_news:[];
      if(n.length){
        add(evidence,'div','Sektor-Nachrichten (keine firmenspezifischen Nachweise):','muted research-small');
        for(const item of n){
          const line=add(evidence,'div',null,'research-small');
          linked(line,item.title,item.url);
        }
      }else{
        add(evidence,'div','Keine zugeordnete aktuelle Sektor-Nachricht in diesem Snapshot.','muted research-small');
      }
    }
    add(out,'div','Modellgrenzen: 1 × ATR Kaufabschlag, 2,5 × ATR Stop. Keine geprüften Q/V/M-Orders oder aktuellen Trade-Republic-Geld-/Briefkurse.','muted research-small');
    return out;
  }
  const filterRows=(rows)=>{
    let filtered=Array.isArray(rows)?rows:[];
    if($('candidateTrOnly').checked)filtered=filtered.filter(r=>r.tr_at_listed===true);
    return filtered;
  };
  function render(){
    if(!snapshot)return;
    const panel=snapshot.research_candidates;
    const kind=$('candidateKind').value;
    const rows=panel.lists[kind]||[];
    const filtered=filterRows(rows);
    const ele=$('candidateCards');
    ele.replaceChildren();
    const available=kind==='quality_momentum'?panel.quality_momentum_coverage:
      kind==='quality_value_momentum'?panel.qvm_coverage:
      kind==='bottleneck_hypotheses'?panel.thematic_hypothesis_coverage:
      kind==='global_momentum'?panel.global_momentum_coverage:
      panel.lists.overlap.length;
    const broker=$('candidateTrOnly').checked?' · nur bestätigte TR-AT-ISIN':' · alle Kandidaten';
    $('candidateSummary').textContent=
      num(filtered.length,0)+' angezeigt von '+num(rows.length,0)+' Top-Kandidaten'+broker+
      ' · '+num(available,0)+' Unternehmen mit ausreichender Datenbasis im Teiluniversum.';
    if(kind==='bottleneck_hypotheses'){
      $('candidateEvidence').className='warn';
      $('candidateEvidence').textContent=
        'Engpass-Exposition ist eine ausdrücklich unbestätigte Branchenhypothese. Sortierung nur nach 12–2-Monats-Kursmomentum, nicht nach einer gemessenen Angebotsknappheit. Sektor-News belegen keinen firmenspezifischen Renditevorteil. Keine validierte Engpass-Rangliste.';
    }else if(kind==='global_momentum'){
      $('candidateEvidence').className='warn';
      $('candidateEvidence').textContent=
        'Weltweites 12–2-Monats-Kursmomentum, pro Emittentenregion maximal vier Titel. Preis und lokaler Handelsumsatz in EUR umgerechnet. Keine US-SEC-Bilanzvoraussetzung – aber auch kein international validierter Quality-/Value-Score und keine Garantie auf eine Überrendite.';
    }else if(kind==='overlap'){
      $('candidateEvidence').className='info';
      $('candidateEvidence').textContent=
        'Überschneidungen zeigen nur, dass eine Aktie in mindestens zwei verschiedenen Forschungslisten erscheint. Das ist kein unabhängiger statistischer Beleg, insbesondere weil die Engpassliste ebenfalls Momentum nutzt.';
    }else{
      $('candidateEvidence').className='info';
      $('candidateEvidence').textContent=
        'Rangwerte sind relative Scores innerhalb eines kleinen und unvollständigen Aktienuniversums. Fehlende Bilanzdaten werden nicht auf null gesetzt oder geschätzt. Es gibt noch keinen überlebensbiasfreien Backtest der hier gezeigten Einzeltitel.';
    }
    if(!filtered.length){
      add(ele,'div',$('candidateTrOnly').checked?
        'Keine eindeutig TR-AT-bestätigten Titel in dieser Liste. Filter deaktivieren, um alle Forschungs-Kandidaten anzuzeigen.':
        'Keine ausreichend belegten Kandidaten für diese Strategie im aktuellen Snapshot.',
        'warn');
    }else{
      filtered.forEach((r,i)=>ele.appendChild(card(r,i,kind)));
    }
    announce();
  }
  async function load(){
    const status=$('candidateDataStatus');
    try{
      const r=await fetch('snapshot.json?research='+Date.now(),{cache:'no-store'});
      if(!r.ok)throw Error('HTTP '+r.status);
      const json=await r.json();
      if(!json.research_candidates||!json.research_candidates.lists)
        throw Error('Kandidaten fehlen im Snapshot');
      snapshot=json;
      const timestamp=Date.parse(json.generated_at||'');
      const old=Number.isFinite(timestamp)&&(Date.now()-timestamp)>48*3600000;
      const details=json.research_candidates;
      status.textContent=
        'Datenstand: '+new Date(json.generated_at).toLocaleString('de-AT')+
        ' · '+num(details.eligible_recent_usd_quotes,0)+' geeignete EUR-umgerechnete US-Kurse'+
        ' · '+num(details.quality_momentum_coverage,0)+' mit Quality/Momentum'+
        ' · '+num(details.qvm_coverage,0)+' mit Q/V/M'+
        (old?' · Achtung: mehr als 48 Stunden alt':'');
      if(old)status.classList.add('bad');
      $('candidateKind').disabled=false;
      $('candidateTrOnly').disabled=false;
      render();
    }catch(e){
      status.textContent='Aktuelle Kandidaten derzeit nicht überprüfbar: '+e.message+
        '. Die wissenschaftliche Strategieauswertung oben bleibt verfügbar.';
      $('candidateCards').replaceChildren();
      $('candidateEvidence').textContent=
        'Ohne nachvollziehbare aktuelle Kurs- und SEC-Daten werden keine Aktienkandidaten erfunden.';
      console.warn('Candidate research feed:',e);
      announce();
    }
  }
  if($('candidateKind')&&$('candidateTrOnly')){
    $('candidateKind').addEventListener('change',render);
    $('candidateTrOnly').addEventListener('change',render);
    load();
  }
})();
