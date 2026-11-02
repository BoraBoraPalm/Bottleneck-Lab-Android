from __future__ import annotations
import os,pathlib,sys,json,math,datetime,time
os.environ.setdefault('OMP_NUM_THREADS','2');os.environ.setdefault('OPENBLAS_NUM_THREADS','2')
R=pathlib.Path(__file__).resolve().parents[1];sys.path.insert(0,str(R.parent/'pca_forecast_study/deps'))
import numpy as np,pandas as pd,joblib
D=R/'data';O=R/'output';SEED=20261102;HS=[5,10,20,60,120,252]
MODELS=['momentum_market','momentum_limit','momentum_limit_stop','filtered_market','filtered_limit','filtered_market_stop','filtered_limit_stop','lowrisk_market','trend_market','momentum_keep','lowrisk_keep','trend_keep']
FX={'HKD':('HKD=X',False,1),'KRW':('KRW=X',False,1),'JPY':('JPY=X',False,1),'TWD':('TWD=X',False,1),'CHF':('CHF=X',False,1),'EUR':('EURUSD=X',True,1),'GBP':('GBPUSD=X',True,1),'GBp':('GBPUSD=X',True,.01),'CNY':('CNY=X',False,1),'BRL':('BRL=X',False,1),'CAD':('CAD=X',False,1),'AUD':('AUDUSD=X',True,1),'ZAR':('ZAR=X',False,1),'ZAc':('ZAR=X',False,.01),'DKK':('DKK=X',False,1)}

def quote(t):
 a=json.loads((D/'prices'/(t+'.json')).read_text())['chart']['result'][0];q=a['indicators']['quote'][0];dates=pd.to_datetime(a['timestamp'],unit='s',utc=True).tz_convert(a['meta'].get('exchangeTimezoneName','UTC')).tz_localize(None).normalize();f=pd.DataFrame(q,index=dates);f['adjclose']=a['indicators'].get('adjclose',[{}])[0].get('adjclose',q['close']);f=f[~f.index.duplicated()].sort_index();return f.loc[:'2025-12-31'],a['meta']

def prepare():
 cache=D/'trading_input_cache.joblib'
 if cache.exists():return joblib.load(cache)
 co=pd.read_csv(D/'cohort.csv');market,_=quote('ACWI');market=market.dropna(subset=['open','close','adjclose']);calendar=market.index;T=len(calendar);N=len(co);eurusd,_=quote('EURUSD=X');e=eurusd.close.dropna();rates={}
 for cur,(ticker,inv,mul) in FX.items():
  f,_=quote(ticker);v=f.close.dropna().reindex(calendar-pd.Timedelta(days=2),method='ffill').to_numpy();usd=(v if inv else 1/v)*mul;rates[cur]=usd/e.reindex(calendar-pd.Timedelta(days=2),method='ffill').to_numpy()
 rates['USD']=1/e.reindex(calendar-pd.Timedelta(days=2),method='ffill').to_numpy()
 opens=np.full((T,N),np.nan);lows=opens.copy();closes=opens.copy();value=opens.copy();rate=opens.copy();mom=opens.copy();trend=opens.copy();atr=opens.copy();risk=opens.copy();ret21=opens.copy();dd=opens.copy();eligible=np.zeros((T,N),bool);ends=np.full(N,T+1,int);normal=[]
 for j,c in enumerate(co.itertuples()):
  f,meta=quote(c.ticker);f=f.dropna(subset=['open','high','low','close','adjclose','volume']);f=f[(f.close>0)&(f.adjclose>0)];adj=f.adjclose/f.close;g=pd.DataFrame(index=f.index);g['open']=f.open*adj;g['high']=f.high*adj;g['low']=f.low*adj;g['close']=f.adjclose;g['rawclose']=f.close;g['volume']=f.volume
  g['mom']=g.close.shift(42)/g.close.shift(252)-1;g['trend']=g.close/g.close.rolling(200).mean()-1;g['ret21']=g.close.pct_change(21,fill_method=None);g['dd']=g.close/g.close.rolling(252).max()-1;g['risk']=np.log(g.close).diff().rolling(252).std()*np.sqrt(252)
  tr=pd.concat([g.high-g.low,(g.high-g.close.shift()).abs(),(g.low-g.close.shift()).abs()],axis=1).max(axis=1);g['atr']=tr.rolling(14).mean();g['adv']= (g.rawclose*g.volume).rolling(20).mean();g['price_date']=g.index
  curr=g.reindex(calendar,method='ffill');actual=g.reindex(calendar);r=rates[meta['currency']];rate[:,j]=r
  opens[:,j]=actual.open;lows[:,j]=actual.low;closes[:,j]=actual.close;value[:,j]=curr.close
  for name,arr in [('mom',mom),('trend',trend),('atr',atr),('risk',risk),('ret21',ret21),('dd',dd)]:arr[:,j]=curr[name]
  stale=(calendar-pd.DatetimeIndex(curr.price_date)).days;eligible[:,j]=np.isfinite(mom[:,j])&np.isfinite(atr[:,j])&(atr[:,j]>0)&(curr.rawclose.to_numpy()*r>=2)&(curr.adv.to_numpy()*r>=2e6)&(stale<=8)
  if pd.notna(c.end_date):
   ix=int(calendar.searchsorted(pd.Timestamp(c.end_date),side='right')-1);ends[j]=ix;eligible[ix+1:,j]=False;opens[ix+1:,j]=np.nan;lows[ix+1:,j]=np.nan;closes[ix+1:,j]=np.nan
  n=g[['open','high','low','close','rawclose','volume']].reset_index().rename(columns={'index':'date'});n['company_id']=c.rank;n['currency']=meta['currency'];normal.append(n)
 mf=market.adjclose.to_numpy();market_trend=mf/pd.Series(mf).rolling(200).mean().to_numpy()-1
 regions=co.region.to_numpy();tickers=co.ticker.to_numpy();rankings={key:[] for key in ['momentum','filtered','lowrisk','trend']}
 for i in range(T):
  base=eligible[i];crash=(ret21[i]<=-.15)|(dd[i]<=-.25);warn=(ret21[i]<=-.08)|(dd[i]<=-.15)
  for key in rankings:
   mask=base.copy();score=mom[i]
   if key=='filtered':mask &= (mom[i]>0)&(trend[i]>0)&~crash&~warn;mask &= bool(market_trend[i]>0)
   elif key=='lowrisk':mask &= np.isfinite(risk[i]);score=-risk[i]
   elif key=='trend':mask &= (trend[i]>0);score=trend[i]
   order=np.lexsort((tickers,-np.nan_to_num(score,nan=-np.inf)));picks=[];counts={}
   for j in order:
    if not mask[j] or counts.get(regions[j],0)>=4:continue
    picks.append(int(j));counts[regions[j]]=counts.get(regions[j],0)+1
    if len(picks)>=10:break
   rankings[key].append(picks)
 benchmarks={}
 for ticker in ['ACWI','SPY']:
  f,_=quote(ticker);a=f.reindex(calendar);factor=a.adjclose/a.close;benchmarks[ticker]=dict(open=(a.open*factor).to_numpy(),close=a.adjclose.to_numpy(),fx=rates['USD'])
 n=pd.concat(normal,ignore_index=True);n.to_parquet(D/'normalized_daily_prices.parquet',index=False)
 result=dict(calendar=calendar,cohort=co,open=opens,low=lows,close=closes,value=value,fx=rate,mom=mom,trend=trend,atr=atr,risk=risk,ret21=ret21,dd=dd,eligible=eligible,ends=ends,rankings=rankings,benchmarks=benchmarks)
 joblib.dump(result,cache,compress=3)
 return result

def simulate(data,model,h,start,end,annual=None,detail=False,slip=.001):
 cal=data['calendar'];i0=int(cal.searchsorted(pd.Timestamp(start)));i1=int(cal.searchsorted(pd.Timestamp(end),side='right')-1);cash=10000.;positions={};pending=[];plans=[];next_review=i0;next_close=None;equity_prev=10000.;rows=[];trades=[];decisions=[];fees=0.;max_live=0;max_region=0;max_weight=0.0
 keep=model.endswith('_keep');key='lowrisk' if model.startswith('lowrisk') else 'trend' if model.startswith('trend') else 'filtered' if model.startswith('filtered') else 'momentum';limit=model in ['momentum_limit','momentum_limit_stop','filtered_limit','filtered_limit_stop'];stop=model in ['momentum_limit_stop','filtered_limit_stop','filtered_market_stop'];review=model.startswith('filtered')
 bm={k:dict(cash=10000.,units=0.,prev=10000.) for k in ['ACWI','SPY']}
 def sell(j,i,px,why):
  nonlocal cash,fees
  pos=positions.pop(j);proceeds=pos['units']*px*data['fx'][i,j]*(1-slip)-1;cash+=proceeds;fees+=1
  if detail:trades.append(dict(ticker=data['cohort'].ticker.iloc[j],strategy=model,interval_at_entry=pos['h'],buy_day=str(cal[pos['entry']].date()),exit_day=str(cal[i].date()),holding_sessions=i-pos['entry']+1,holding_calendar_days=(cal[i]-cal[pos['entry']]).days,reason=why,buy_value_eur=pos['spent'],proceeds_eur=proceeds,pnl_eur=proceeds-pos['spent']))
 for i in range(i0,i1+1):
  opening_cash=cash # Only funds settled before this global session fund opening buys.
  for j,pos in list(positions.items()):
   op=data['open'][i,j];lo=data['low'][i,j]
   if not np.isfinite(op):continue
   if stop and np.isfinite(lo) and lo<=pos['stop']:sell(j,i,min(op,pos['stop']),'stop');continue
   if review and i>pos['entry']:
    if data['trend'][i-1,j]<0 or data['ret21'][i-1,j]<=-.15 or data['dd'][i-1,j]<=-.25:sell(j,i,op,'prior_close_review')
  # Reserve budgets once outgoing cash is available; no spending a future sale.
  active_pending=[p for p in pending if p['first']<=i<=p['last']]
  if active_pending and any(p['budget'] is None for p in active_pending):
   allocation=max(0,opening_cash)/len(active_pending)
   for p in active_pending:
    if p['budget'] is None and allocation>2:p['budget']=allocation
  remaining=[]
  for p in pending:
   j=p['j']
   if i<p['first']:remaining.append(p);continue
   if i>p['last'] or j in positions:continue
   region=data['cohort'].region.iloc[j]
   if len(positions)>=10 or sum(data['cohort'].region.iloc[k]==region for k in positions)>=4:
    remaining.append(p);continue
   op=data['open'][i,j];lo=data['low'][i,j];fx=data['fx'][i,j]
   if not np.isfinite(op) or not np.isfinite(fx):remaining.append(p);continue
   if limit and (not np.isfinite(lo) or lo>p['limit']):remaining.append(p);continue
   px=min(op,p['limit']) if limit else op;budget=min(cash,opening_cash,p['budget'] or 0.)
   if budget<=2:
    remaining.append(p);continue
   units=(budget-1)/(px*fx*(1+slip));cash-=budget;opening_cash-=budget;fees+=1;positions[j]=dict(units=units,entry=i,spent=budget,h=p['h'],stop=p['stop']);max_live=max(max_live,len(positions));max_region=max(max_region,sum(data['cohort'].region.iloc[k]==region for k in positions))
   if stop and np.isfinite(lo) and lo<=p['stop']:sell(j,i,min(px,p['stop']),'stop_same_day')
  pending=remaining
  # Pre-announced structural boundary is not replaced with a synthetic successor.
  for j in list(positions):
   if i>=data['ends'][j] and np.isfinite(data['close'][i,j]):sell(j,i,data['close'][i,j],'corporate_boundary')
  # Close decisions were fixed at the preceding close; execution at today's close.
  for j in list(plans):
   if j in positions and np.isfinite(data['close'][i,j]):sell(j,i,data['close'][i,j],'review_or_deadline');plans.remove(j)
   elif j not in positions:plans.remove(j)
  # All signal data precede the scheduled execution by at least two sessions.
  if i==next_review:
   hh=annual.get(int(cal[i].year),h) if annual else h;targets=data['rankings'][key][i];retain=set(targets) if keep else set();plans=[j for j in positions if j not in retain];to_buy=[j for j in targets if j not in positions or j in plans];pending=[]
   for j in to_buy:
    close=data['value'][i,j];atr=data['atr'][i,j];lim=close-atr;st=close-(3.5 if limit else 2.5)*atr
    if limit and lim<=0 or stop and st<=0:continue
    pending.append(dict(j=j,first=i+2,last=min(i+6,i+hh+1),limit=lim,stop=st,budget=None,h=hh))
   # Plans are executed tomorrow, not at the signal's still-unknown close.
   next_review=i+hh;decisions.append(dict(strategy=model,date=str(cal[i].date()),interval=hh,targets=len(targets),annual_choice_known_before=str(cal[i].year)+'-01-01'))
   # Ensure the closure loop above does not act on today's newly fixed plans.
  # Equity uses only current or prior local closes; pending orders are cash.
  position_values=[pos['units']*data['value'][i,j]*data['fx'][i,j] for j,pos in positions.items()];value=sum(position_values);equity=cash+value;max_weight=max(max_weight,max(position_values,default=0.)/equity if equity>0 else 0.);assert cash>=-1e-7 and len(positions)<=10 and max_region<=4;ret=equity/equity_prev-1;equity_prev=equity;max_live=max(max_live,len(positions))
  br={}
  for name,b in bm.items():
   a=data['benchmarks'][name]
   if i==i0+2 and np.isfinite(a['open'][i]):b['units']=(b['cash']-1)/(a['open'][i]*a['fx'][i]*(1+slip));b['cash']=0.
   v=b['cash']+b['units']*a['close'][i]*a['fx'][i];br[name]=v/b['prev']-1;b['prev']=v
  rows.append(dict(date=cal[i],strategy=model,interval=h,net_return=ret,acwi_return=br['ACWI'],spy_return=br['SPY'],equity=equity,cash=cash,exposure=value/equity if equity>0 else np.nan,positions=len(positions),acwi_equity=bm['ACWI']['prev'],spy_equity=bm['SPY']['prev']))
 # Trade summaries are closed-trade statistics; open holdings remain censored.
 return pd.DataFrame(rows),trades,decisions,dict(fees_eur=fees,open_positions=len(positions),max_positions=max_live,max_region_positions=max_region,max_single_position_weight=max_weight,closed_trades=len(trades) if detail else None)

def stats(frame):
 r=frame.net_return.to_numpy();b=frame.acwi_return.to_numpy();x=r-b;years=(frame.date.iloc[-1]-frame.date.iloc[0]).days/365.25;w=frame.equity.to_numpy();wb=frame.acwi_equity.to_numpy();s=np.std(x,ddof=1);dd=np.r_[10000,w]/np.maximum.accumulate(np.r_[10000,w])-1
 return dict(sessions=len(frame),cagr=float((w[-1]/10000)**(1/years)-1),acwi_cagr=float((wb[-1]/10000)**(1/years)-1),cagr_excess=float((w[-1]/10000)**(1/years)-(wb[-1]/10000)**(1/years)),information_ratio=float(x.mean()/s*np.sqrt(252)) if s>1e-12 else 0.,annualized_mean_excess=float(x.mean()*252),annualized_vol=float(np.std(r,ddof=1)*np.sqrt(252)),max_drawdown=float(dd.min()),end_eur=float(w[-1]),acwi_end_eur=float(wb[-1]),spy_end_eur=float(frame.spy_equity.iloc[-1]),average_exposure=float(frame.exposure.mean()))

def bootstrap(diff,block=252,n=5000):
 d=np.asarray(diff);N=len(d);rng=np.random.default_rng(SEED+block);means=[]
 # Avoid allocating 5000 x 1800 x many strategies at once.
 for s in range(0,n,250):
  st=rng.integers(0,N,size=(min(250,n-s),int(np.ceil(N/block))));ix=((st[:,:,None]+np.arange(block))%N).reshape(len(st),-1)[:,:N];means.extend((d[ix].mean(axis=1)*252).tolist())
 v=np.array(means);effect=float(d.mean()*252);return dict(effect_annualized_mean=effect,low=float(np.quantile(v,.025)),high=float(np.quantile(v,.975)),p_one_sided=float((1+np.sum(v-effect>=effect))/(n+1)),block_sessions=block,iterations=n)

def main():
 t=time.time();data=prepare();print('Trading inputs prepared',len(data['calendar']),'sessions,',len(data['cohort']),'historical firms.',flush=True);metrics=[];paths=[];alltrades=[];allchoices=[];audits=[];tests=[]
 for model in MODELS:
  selected={}
  for year in range(2019,2026):
   scores={};grid=[]
   for h in HS:
    f,_,_,_=simulate(data,model,h,f'{year-5}-01-01',f'{year-1}-12-31');st=stats(f);scores[h]=st['information_ratio'];grid.append(dict(interval=h,metrics=st))
   chosen=max(HS,key=lambda h:(scores[h],h));selected[year]=chosen;allchoices.append(dict(strategy=model,year=year,selected_interval=chosen,training_start=f'{year-5}-01-01',training_end=f'{year-1}-12-31',criterion='net_information_ratio_to_ACWI',candidates=grid));print('Trade duration chosen from past:',model,year,chosen,flush=True)
  fixed={}
  for h in HS:
   f,tr,dec,diag=simulate(data,model,h,'2019-01-01','2025-12-31',detail=True);fixed[h]=f;st=stats(f);st.update(strategy=model,policy=str(h),**diag,mean_actual_hold_sessions=float(np.mean([x['holding_sessions'] for x in tr])) if tr else None,median_actual_hold_sessions=float(np.median([x['holding_sessions'] for x in tr])) if tr else None);metrics.append(st);f['policy']=str(h);paths.append(f);alltrades.extend([dict(x,policy=str(h)) for x in tr]);audits.extend([dict(x,policy=str(h)) for x in dec])
  f,tr,dec,diag=simulate(data,model,20,'2019-01-01','2025-12-31',annual=selected,detail=True);st=stats(f);st.update(strategy=model,policy='past_selected',**diag,mean_actual_hold_sessions=float(np.mean([x['holding_sessions'] for x in tr])) if tr else None,median_actual_hold_sessions=float(np.median([x['holding_sessions'] for x in tr])) if tr else None);metrics.append(st);f['policy']='past_selected';paths.append(f);alltrades.extend([dict(x,policy='past_selected') for x in tr]);audits.extend([dict(x,policy='past_selected') for x in dec]);diff=f.net_return.to_numpy()-fixed[20].net_return.to_numpy();e=bootstrap(diff);e.update(strategy=model,reference='fixed_20_sessions',sensitivity={str(b):bootstrap(diff,b) for b in [126,504]});tests.append(e);print('Trade strategy complete:',model,flush=True)
 pd.DataFrame(metrics).to_csv(O/'trading_metrics.csv',index=False);pd.concat(paths,ignore_index=True).to_parquet(O/'trading_daily_paths.parquet',index=False);pd.DataFrame(alltrades).to_csv(O/'trading_closed_trades.csv',index=False);pd.DataFrame(audits).to_csv(O/'trading_decisions.csv',index=False);(O/'trading_choices.json').write_text(json.dumps(allchoices,indent=2));(O/'trading_tests_uncorrected.json').write_text(json.dumps(tests,indent=2));(O/'trading_runtime.json').write_text(json.dumps({'seconds':time.time()-t},indent=2));print('Trading module DONE in',round(time.time()-t),'seconds.',flush=True)
if __name__=='__main__':main()
