from __future__ import annotations
import pathlib,sys,json
R=pathlib.Path(__file__).resolve().parent;sys.path.insert(0,str(R/'deps'))
import numpy as np,pandas as pd
from data_build import quote
from run_study import METHODS
D=R/'data';O=R/'output'
def rank_weights(g,method):
 scores=g[method].to_numpy();k=max(1,int(np.ceil(.2*len(g))));boundary=np.sort(scores)[-k];above=scores>boundary+1e-12;tied=np.abs(scores-boundary)<=1e-12
 w=above.astype(float)/k
 if tied.any():w[tied]=(k-int(above.sum()))/int(tied.sum())/k
 assert np.allclose(w.sum(),1)
 return w

def main():
 q=pd.read_parquet(O/'predictions_primary_4.parquet');co=pd.read_csv(D/'cohort.csv');wr=co.groupby('region').size()/len(co);dates=sorted(q.date.unique())[::4]
 f,_=quote('ACWI');f=f.dropna(subset=['adjclose','close','open']);f['adjusted_open']=f.open*f.adjclose/f.close;fx,_=quote('EURUSD=X');fx=fx.close.dropna()
 curves=[];skipped=[]
 def fund_return(dt):
  mon=pd.Timestamp(dt)+pd.Timedelta(days=5);exit_=mon+pd.Timedelta(weeks=4);ee=f.loc[mon:mon+pd.Timedelta(days=4)];xx=f.loc[exit_:exit_+pd.Timedelta(days=4)]
  if not len(ee) or not len(xx):return np.nan
  fe=float(fx.reindex([ee.index[0]-pd.Timedelta(days=1)],method='ffill').iloc[0]);fx_=float(fx.reindex([xx.index[0]-pd.Timedelta(days=1)],method='ffill').iloc[0]);return float(xx.adjusted_open.iloc[0]/ee.adjusted_open.iloc[0]*fe/fx_-1)
 common=[]
 for dt in dates:
  a=q[q.date==dt];ok=a[['forward_return_4','eurusd_entry_date','eurusd_exit_date_4']].notna().all().all() and set(a.region)==set(wr.index)
  ar=fund_return(dt)
  if not ok or not np.isfinite(ar):skipped.append(str(pd.Timestamp(dt).date()));continue
  a=a.copy();a['eur_return']=(1+a.forward_return_4)*a.eurusd_entry_date/a.eurusd_exit_date_4-1
  bench=sum(float(w)*a[a.region==reg].eur_return.mean() for reg,w in wr.items());common.append((dt,a,bench,ar))
 for method in METHODS:
  eq={'gross':10000.,'fees_only':10000.,'net':10000.};be=10000.;ac=10000.
  for dt,a,benchmark,acwi in common:
   ret=0.;n=0;selected=[]
   for region,w in wr.items():
    b=a[a.region==region];wlocal=rank_weights(b,method);ret+=float(w)*float(np.dot(wlocal,b.eur_return));n+=int((wlocal>0).sum());selected.extend(b.loc[wlocal>0,'company_id'])
   eq['gross']*=1+ret
   eq['fees_only']=(eq['fees_only']-n)*(1+ret)-n
   eq['net']=(eq['net']-n)/1.001*(1+ret)*.999-n
   be*=1+benchmark;ac*=1+acwi
   curves.append(dict(model=method,date=dt,stock_count=n,gross_return=ret,benchmark_gross_return=benchmark,acwi_gross_return=acwi,gross_equity=eq['gross'],fees_equity=eq['fees_only'],net_equity=eq['net'],benchmark_equity=be,acwi_equity=ac))
 curves=pd.DataFrame(curves);curves.to_csv(O/'portfolio_common_curves.csv',index=False);summary=[]
 for method,g in curves.groupby('model'):
  z=g.iloc[-1];summary.append(dict(model=method,cohorts=len(g),gross_end_eur=float(z.gross_equity),fees_end_eur=float(z.fees_equity),net_end_eur=float(z.net_equity),benchmark_gross_end_eur=float(z.benchmark_equity),acwi_gross_end_eur=float(z.acwi_equity),net_excess_to_benchmark_eur=float(z.net_equity-z.benchmark_equity),mean_gross_cohort_excess=float((g.gross_return-g.benchmark_gross_return).mean()),gross_better_cohort_fraction=float((g.gross_return>g.benchmark_gross_return).mean())))
 (O/'portfolio_common_summary.json').write_text(json.dumps(dict(initial_eur=10000,first_signal=str(pd.Timestamp(common[0][0]).date()),last_signal=str(pd.Timestamp(common[-1][0]).date()),scheduled_cohorts=len(dates),valid_cohorts=len(common),skipped_dates=skipped,candidates=summary,warning='Shared complete-data cohorts; gross benchmarks, active fees, conservative full round trips. Descriptive approximation; no actual executable portfolio claim.'),indent=2));print('Financial diagnostic completed on',len(common),'common cohorts; skipped',len(skipped))
if __name__=='__main__':main()
