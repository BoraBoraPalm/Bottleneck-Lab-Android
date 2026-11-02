from __future__ import annotations
import pathlib,sys,json,itertools,hashlib,datetime
R=pathlib.Path(__file__).resolve().parents[1];sys.path.insert(0,str(R.parent/'pca_forecast_study/deps'))
import numpy as np,pandas as pd
D=R/'data';O=R/'output';SEED=20261102
SIGNALS=['Mom12m','BM','GP','AssetGrowth','OperProf','RealizedVol','EarningsSurprise','REV6','AnnouncementReturn'];KS=[1,3,6,12];COST=.01
NAMES={'Mom12m':'Momentum','BM':'Value','GP':'Gross-Profit-Quality','AssetGrowth':'Konservatives Bilanzwachstum','OperProf':'Operative Profitabilität','RealizedVol':'Geringe realisierte Volatilität','EarningsSurprise':'Gewinnüberraschung','REV6':'Analystenrevisionen','AnnouncementReturn':'Ankündigungsrendite'}

def stats(r,b):
 r=np.asarray(r,float);b=np.asarray(b,float);x=r-b;n=len(r);s=np.std(x,ddof=1)
 w=np.cumprod(1+r);w0=np.r_[1,w];dd=w0/np.maximum.accumulate(w0)-1
 return dict(months=n,cagr=float(np.prod(1+r)**(12/n)-1),benchmark_cagr=float(np.prod(1+b)**(12/n)-1),cagr_excess=float(np.prod(1+r)**(12/n)-np.prod(1+b)**(12/n)),annualized_mean_excess=float(np.mean(x)*12),information_ratio=float(np.mean(x)/s*np.sqrt(12)) if s>1e-12 else 0.,annualized_vol=float(np.std(r,ddof=1)*np.sqrt(12)),max_drawdown=float(dd.min()),end_per_10000=float(10000*w[-1]))
def boot(d,block=12,n=5000):
 d=np.asarray(d);N=len(d);rng=np.random.default_rng(SEED+block);st=rng.integers(0,N,size=(n,int(np.ceil(N/block))));ix=((st[:,:,None]+np.arange(block))%N).reshape(n,-1)[:,:N];v=d[ix].mean(axis=1)*12;effect=float(d.mean()*12)
 return dict(effect_annualized_mean=effect,low=float(np.quantile(v,.025)),high=float(np.quantile(v,.975)),p_one_sided=float((1+np.sum(v-effect>=effect))/(n+1)),block_months=block,iterations=n)
def build():
 docs=pd.read_csv(D/'SignalDoc.csv').set_index('Acronym');original={s:int(docs.loc[s,'Portfolio Period']) for s in SIGNALS};weights={s:docs.loc[s,'Stock Weight'] for s in SIGNALS}
 frames=[];ports={}
 if (D/'academic_selected_long_returns.csv').exists():
  d=pd.read_csv(D/'academic_selected_long_returns.csv');ports=json.loads((D/'academic_source_metadata.json').read_text())['long_portfolios']
 else:
  for k in KS:
   d=pd.read_parquet(D/f'PredictorAltPorts_HoldPer_{k}.parquet',filters=[('signalname','in',SIGNALS)])
   d=d[d.port!='LS'].copy();largest=d.groupby('signalname').port.max();d=d[d.apply(lambda r:r.port==largest[r.signalname],axis=1)];d['month']=pd.to_datetime(d.date).dt.to_period('M');d['k']=k;d['return']=d.ret/100;assert (d['return']>-1).all();assert d.Nshort.eq(0).all();assert not d.duplicated(['month','signalname']).any();frames.append(d[['month','signalname','k','return','Nlong']]);ports[k]=largest.to_dict()
  d=pd.concat(frames,ignore_index=True);d['month']=d.month.astype(str);d.to_csv(D/'academic_selected_long_returns.csv',index=False)
 d['month']=pd.PeriodIndex(d.month,freq='M');x=d.pivot(index='month',columns=['signalname','k'],values='return').sort_index();base=pd.read_csv(D/'market_monthly_inputs.csv',index_col=0);base.index=pd.PeriodIndex(base.index,freq='M');market=base.Market
 idx=pd.period_range('2004-01','2025-12',freq='M');x=x.reindex(idx);market=market.reindex(idx);assert x.notna().all().all() and market.notna().all()
 families={NAMES[s]:{s:1.} for s in SIGNALS};behavior=['Mom12m','EarningsSurprise','REV6','AnnouncementReturn']
 for a,b in itertools.combinations(behavior,2):families[NAMES[a]+' + '+NAMES[b]]={a:.5,b:.5}
 families['Behavioral vierfach']={s:.25 for s in behavior};families['QVM Gross Profit']={s:1/3 for s in ['Mom12m','BM','GP']};families['QVM Operative Profitabilität']={s:1/3 for s in ['Mom12m','BM','OperProf']};families['50% Markt + QVM']={'Market':.5,'Mom12m':1/6,'BM':1/6,'GP':1/6};families['80% Markt + Momentum']={'Market':.8,'Mom12m':.2}
 meta=dict(signals=SIGNALS,original_period=original,stock_weights=weights,long_portfolios=ports,families=families,source_holdper_means_signal_refresh=True,not_forced_individual_stock_liquidation=True)
 (O/'academic_metadata.json').write_text(json.dumps(meta,indent=2,ensure_ascii=False));return x,market,meta

def main():
 x,market,meta=build();evaluation=pd.period_range('2014-01','2025-12',freq='M');records=[];curves=[];choices=[];tests=[]
 for name,w in meta['families'].items():
  active=1-w.get('Market',0);fee=COST/12*active
  series={k:sum(a*(market if s=='Market' else x[(s,k)]) for s,a in w.items())-fee for k in KS}
  original=sum(a*(market if s=='Market' else x[(s,meta['original_period'][s])]) for s,a in w.items())-fee
  selected=pd.Series(index=evaluation,dtype=float)
  for year in range(2014,2026):
   train=pd.period_range(f'{year-10}-01',f'{year-1}-12',freq='M');scores={k:stats(series[k].loc[train],market.loc[train])['information_ratio'] for k in KS};best=max(KS,key=lambda k:(scores[k],k));test=evaluation[evaluation.year==year];selected.loc[test]=series[best].loc[test];choices.append(dict(strategy=name,year=year,chosen_months=best,train_start=str(train[0]),train_end=str(train[-1]),score=scores[best],all_scores=scores))
  bench=market.loc[evaluation]
  for k,s in list(series.items())+[('original',original),('past_selected',selected)]:
   r=s.loc[evaluation];st=stats(r,bench);st.update(strategy=name,policy=str(k),active_cost_annual=COST*active);records.append(st)
   for dt,rr,bb in zip(evaluation,r,bench):curves.append(dict(strategy=name,policy=str(k),month=str(dt),net_return=float(rr),market_return=float(bb)))
  dif=selected.to_numpy()-original.loc[evaluation].to_numpy();e=boot(dif);e.update(strategy=name,reference='published_source_interval',chosen_frequency={str(k):sum(c['strategy']==name and c['chosen_months']==k for c in choices) for k in KS},sensitivity={str(k):boot(dif,k) for k in [6,24]});tests.append(e)
  print('Academic factor evaluated:',name,flush=True)
 # Cost sensitivity does not choose different model settings on the test sample.
 sensitive=[]
 for cost in [0,.02]:
  for row in curves:
   z=row.copy();active=1-meta['families'][row['strategy']].get('Market',0);z['net_return']=z['net_return']+(COST-cost)/12*active;z['annual_headwind']=cost;sensitive.append(z)
 pd.DataFrame(sensitive).to_csv(O/'academic_cost_sensitivity_returns.csv',index=False)
 pd.DataFrame(records).to_csv(O/'academic_metrics.csv',index=False);pd.DataFrame(curves).to_csv(O/'academic_returns.csv',index=False);(O/'academic_choices.json').write_text(json.dumps(choices,indent=2,ensure_ascii=False));(O/'academic_tests_uncorrected.json').write_text(json.dumps(tests,indent=2,ensure_ascii=False));print('Academic module DONE',len(meta['families']),'families.',flush=True)
if __name__=='__main__':main()
