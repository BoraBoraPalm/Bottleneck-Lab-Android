"""Post-result diagnostics; these never select a strategy or duration."""
import pathlib,sys,json
R=pathlib.Path(__file__).resolve().parents[1];sys.path.insert(0,str(R.parent/'pca_forecast_study/deps'))
import numpy as np,pandas as pd
from run_trading import prepare,stats
O=R/'output';rng=np.random.default_rng(20261102)

def main():
 p=pd.read_parquet(O/'forecast_horizon_predictions.parquet');annual=[];cis=[]
 methods=['price_ridge','elastic_net','pca_ridge','pls_ridge','small_boosting']
 for (h,year),g in p.groupby(['horizon_weeks','year']):
  den=float(np.mean(g.observed_excess.to_numpy()**2))
  for m in methods:annual.append(dict(horizon_weeks=int(h),year=int(year),method=m,n=len(g),r2_zero=1-float(np.mean((g.observed_excess-g[m])**2))/den))
 for h,g in p.groupby('horizon_weeks'):
  for m in methods:
   daily=g.assign(loss=(g.observed_excess-g[m])**2,zero_loss=g.observed_excess**2).groupby('date').agg(loss=('loss','sum'),zero_loss=('zero_loss','sum'))
   n=len(daily);block=52;st=rng.integers(0,n,size=(5000,int(np.ceil(n/block))));ix=((st[:,:,None]+np.arange(block))%n).reshape(5000,-1)[:,:n]
   z=1-daily.loss.to_numpy()[ix].sum(axis=1)/daily.zero_loss.to_numpy()[ix].sum(axis=1)
   cis.append(dict(horizon_weeks=int(h),method=m,r2_zero=1-daily.loss.sum()/daily.zero_loss.sum(),low=float(np.quantile(z,.025)),high=float(np.quantile(z,.975)),bootstrap_block_weeks=52,iterations=5000,independent_regimes_caveat='156 weekly prediction dates; long targets overlap; descriptive post-result interval, no winner test'))
 pd.DataFrame(annual).to_csv(O/'forecast_yearly_metrics.csv',index=False);pd.DataFrame(cis).to_csv(O/'forecast_block_intervals.csv',index=False)
 # Passive historical-cohort diagnostic, added after primary results. It is
 # not a selection benchmark and deliberately has no ten-stock region cap.
 d=prepare();cal=d['calendar'];i0=int(cal.searchsorted(pd.Timestamp('2019-01-01')));i1=int(cal.searchsorted(pd.Timestamp('2025-12-31'),side='right')-1);entry=i0+2
 good=np.flatnonzero(np.isfinite(d['open'][entry])&np.isfinite(d['fx'][entry])&(d['ends']>entry));budget=10000/len(good);units={int(j):(budget-1)/(d['open'][entry,j]*d['fx'][entry,j]*1.001) for j in good};cash=0.;fees=len(good);prev=10000.;rows=[]
 for i in range(i0,i1+1):
  if i<entry:equity=10000.
  else:
   for j in list(units):
    if i>=d['ends'][j] and np.isfinite(d['close'][i,j]):cash+=units.pop(j)*d['close'][i,j]*d['fx'][i,j]*.999-1;fees+=1
   equity=cash+sum(u*d['value'][i,j]*d['fx'][i,j] for j,u in units.items())
  rows.append(dict(date=cal[i],equity=equity,net_return=equity/prev-1));prev=equity
 f=pd.DataFrame(rows);base=pd.read_parquet(O/'trading_daily_paths.parquet');base=base[(base.strategy=='momentum_market')&(base.policy=='20')].sort_values('date')
 for col in ['acwi_return','spy_return','acwi_equity','spy_equity']:f[col]=base[col].to_numpy()
 f['exposure']=1.;s=stats(f);s.update(initial_companies=len(good),fees_eur=fees,diagnostic_added_after_primary_results=True,construction='Equal initial EUR weights, no rebalancing, 1 EUR per actual order, 0.1% per side, same 2018 cohort, corporate boundaries converted to cash; no region/ten-stock caps.')
 (O/'passive_cohort_diagnostic.json').write_text(json.dumps(s,indent=2));f.to_csv(O/'passive_cohort_diagnostic_path.csv',index=False)
 print('Diagnostics completed; passive historical cohort CAGR',round(s['cagr']*100,2),'percent; constituents',len(good))

if __name__=='__main__':main()
