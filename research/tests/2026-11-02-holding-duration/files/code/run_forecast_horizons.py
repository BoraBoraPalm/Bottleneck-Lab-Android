from __future__ import annotations
import os,pathlib,sys,json,time
os.environ.setdefault('OMP_NUM_THREADS','2');os.environ.setdefault('OPENBLAS_NUM_THREADS','2')
R=pathlib.Path(__file__).resolve().parents[1];sys.path.insert(0,str(R.parent/'pca_forecast_study/deps'))
import numpy as np,pandas as pd
from scipy.stats import spearmanr
from sklearn.metrics import roc_auc_score
from threadpoolctl import threadpool_limits
from fit_core import fit,predict
from run_trading import quote,FX
D=R/'data';O=R/'output';HORIZONS=[1,2,4,8,12,26,52];METHODS=['price_ridge','elastic_net','pca_ridge','pls_ridge','small_boosting']
GRID={'price_ridge':[{'alpha':a} for a in [1,10,100]],'elastic_net':[{'alpha':a} for a in [.0001,.001,.01]],'pca_ridge':[{'k':k,'alpha':10} for k in [2,4,8,12]],'pls_ridge':[{'k':k,'alpha':10} for k in [2,4,8,12]],'small_boosting':[dict(max_iter=100,learning_rate=.05,max_leaf_nodes=7,min_samples_leaf=100,l2_regularization=10)]}

def build():
 if (D/'forecast_horizon_panel.parquet').exists():return pd.read_parquet(D/'forecast_horizon_panel.parquet'),json.loads((D/'pca_feature_metadata.json').read_text())
 p=pd.read_parquet(R.parent/'pca_forecast_study/data/analysis_panel.parquet');meta=json.loads((R.parent/'pca_forecast_study/output/dataset_info.json').read_text());cols=['date','company_id','company','ticker','region','country']+meta['main_features'];p=p[cols].copy();co=pd.read_csv(D/'cohort.csv');dates=pd.DatetimeIndex(sorted(p.date.unique()));rates={}
 for cur,(t,inv,mul) in FX.items():
  f,_=quote(t);s=f.close.dropna();rates[cur]=(s,inv,mul)
 frames=[]
 for c in co.itertuples():
  f,info=quote(c.ticker);f=f.dropna(subset=['open','close','adjclose']);f=f[(f.open>0)&(f.close>0)&(f.adjclose>0)];fx=np.ones(len(f))
  if info['currency']!='USD':
   ss,inv,mul=rates[info['currency']];v=ss.reindex(f.index-pd.Timedelta(days=2),method='ffill').to_numpy();fx=(v if inv else 1/v)*mul
  prices=(f.open*f.adjclose/f.close).to_numpy()*fx
  def at(ds):
   ix=f.index.searchsorted(ds);safe=np.minimum(ix,len(f)-1);good=(ix<len(f))&(f.index[safe]<=ds+pd.Timedelta(days=4));v=prices[safe].copy();v[~good]=np.nan;dd=f.index[safe].to_numpy().copy();dd[~good]=np.datetime64('NaT');return v,dd
  mon=dates+pd.Timedelta(days=5);entry,ed=at(mon);a=pd.DataFrame({'date':dates,'company_id':c.rank,'entry_date':ed})
  for h in HORIZONS:
   exit_,xd=at(mon+pd.Timedelta(weeks=h));a[f'return_{h}']=exit_/entry-1;a[f'exit_{h}']=xd
   if pd.notna(c.end_date):a.loc[pd.to_datetime(a[f'exit_{h}'])>pd.Timestamp(c.end_date),[f'return_{h}',f'exit_{h}']]=[np.nan,pd.NaT]
  frames.append(a)
 p=p.merge(pd.concat(frames),on=['date','company_id'],how='left',validate='one_to_one')
 for h in HORIZONS:
  g=p.groupby(['date','region'])[f'return_{h}'].agg(['mean','count']);g.columns=[f'bm_{h}',f'n_{h}'];p=p.join(g,on=['date','region']);glob=p.groupby('date')[f'return_{h}'].transform('mean');p[f'y_{h}']=p[f'return_{h}']-p[f'bm_{h}'].where(p[f'n_{h}']>=5,glob)
  known=p[p[f'return_{h}'].notna()];rg=known.groupby(['date','region'])[f'exit_{h}'].max();global_=known.groupby('date')[f'exit_{h}'].max();m=pd.Series(p.set_index(['date','region']).index.map(rg).to_numpy(),index=p.index);p[f'available_{h}']=m.where(p[f'n_{h}']>=5,p.date.map(global_))
 p.to_parquet(D/'forecast_horizon_panel.parquet',index=False);return p,meta

def main():
 t=time.time();p,meta=build();fs=meta['main_features'];pricefs=meta['price_features']+['ret20_x_market','mom_x_breadth','atr_x_marketvol'];common=(p.date.dt.year.between(2022,2024))&p[[f'y_{h}' for h in HORIZONS]].notna().all(axis=1);keys=pd.MultiIndex.from_frame(p.loc[common,['date','company_id']]);choices=[];preds=[];audits=[]
 for h in HORIZONS:
  for year in [2022,2023,2024]:
   cutoff=pd.Timestamp(year,1,1);inner=pd.Timestamp(year-1,1,1);tr=p[(p.date<cutoff)&(p[f'available_{h}']<cutoff)&p[f'y_{h}'].notna()];itr=p[(p.date<inner)&(p[f'available_{h}']<inner)&p[f'y_{h}'].notna()];iva=p[(p.date>=inner)&(p.date<cutoff)&(p[f'available_{h}']<cutoff)&p[f'y_{h}'].notna()];te=p[(p.date.dt.year==year)&pd.MultiIndex.from_frame(p[['date','company_id']]).isin(keys)].copy();q=te[['date','company_id','region','country','entry_date',f'exit_{h}',f'y_{h}']].rename(columns={f'exit_{h}':'exit_date',f'y_{h}':'observed_excess'});q['horizon_weeks']=h;q['year']=year;q['zero']=0.
   assert len(tr)>1000 and (tr[f'available_{h}']<cutoff).all();audits.append(dict(horizon=h,year=year,cutoff=str(cutoff.date()),latest_known_target=str(tr[f'available_{h}'].max().date()),train_rows=len(tr),test_rows=len(te),inner_training_rows=len(itr),inner_validation_rows=len(iva)))
   for method in METHODS:
    features=pricefs if method=='price_ridge' else fs;fallback=len(itr)<1000 or len(iva)<1000;grid=[]
    if fallback:cfg=GRID[method][0] if method in ['pca_ridge','pls_ridge','small_boosting'] else {'alpha':100} if method=='price_ridge' else {'alpha':.001}
    else:
     losses=[]
     for cfg0 in GRID[method]:
      m=fit(itr,features,itr[f'y_{h}'].to_numpy(),method,cfg0);yp=predict(iva,m);loss=float(np.mean((iva[f'y_{h}'].to_numpy()-yp)**2));grid.append(dict(config=cfg0,mse=loss));losses.append(loss)
     cfg=GRID[method][int(np.argmin(losses))]
    m=fit(tr,features,tr[f'y_{h}'].to_numpy(),method,cfg);q[method]=predict(te,m);choices.append(dict(horizon_weeks=h,year=year,method=method,selected=cfg,fallback_for_insufficient_inner_data=fallback,inner_grid=grid))
   preds.append(q);print('Forecast horizon completed:',h,'weeks, year',year,flush=True)
 q=pd.concat(preds,ignore_index=True);q.to_parquet(O/'forecast_horizon_predictions.parquet',index=False);rows=[]
 for (h,method) in [(h,m) for h in HORIZONS for m in ['zero']+METHODS]:
  a=q[q.horizon_weeks==h];y=a.observed_excess.to_numpy();v=a[method].to_numpy();mse=float(np.mean((y-v)**2));ics=[]
  for _,g in a.groupby('date'):
   if g[method].max()-g[method].min()<1e-12:ics.append(0.)
   else:ics.append(float(spearmanr(g[method],g.observed_excess).statistic))
  rows.append(dict(horizon_weeks=h,method=method,n=len(a),mse=mse,r2_zero=1-mse/float(np.mean(y*y)),auc=float(roc_auc_score(y>0,v)),mean_rank_ic=float(np.mean(ics))))
 pd.DataFrame(rows).to_csv(O/'forecast_horizon_metrics.csv',index=False);(O/'forecast_horizon_choices.json').write_text(json.dumps(choices,indent=2));(O/'forecast_horizon_audit.json').write_text(json.dumps(audits,indent=2));(O/'forecast_runtime.json').write_text(json.dumps({'seconds':time.time()-t},indent=2));print('Forecast module DONE',round(time.time()-t),'seconds.',flush=True)
if __name__=='__main__':
 with threadpool_limits(limits=2):main()
