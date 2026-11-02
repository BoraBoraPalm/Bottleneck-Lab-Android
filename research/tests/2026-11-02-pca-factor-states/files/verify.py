"""Independently verify time boundaries, saved transformations and predictions."""
from __future__ import annotations
import pathlib,sys,json,hashlib
R=pathlib.Path(__file__).resolve().parent;sys.path.insert(0,str(R/'deps'))
import numpy as np,pandas as pd,joblib
from sklearn.decomposition import PCA
from run_study import predict,prep_transform,MAIN_FEATURES,METHODS
D=R/'data';O=R/'output'
def main():
 p=pd.read_parquet(D/'analysis_panel.parquet');q=pd.read_parquet(O/'predictions_primary_4.parquet');lock=json.loads((O/'protocol_lock.json').read_text());checks={}
 checks['primary_sources_unchanged_after_lock']=all(hashlib.sha256((R/f).read_bytes()).hexdigest()==s for f,s in lock['sha256'].items())
 checks['one_input_per_firm_date']=not p.duplicated(['date','company_id']).any()
 checks['price_features_strictly_before_news_date']=bool((p.feature_price_date<p.date).all())
 checks['news_state_and_future_targets_absent_from_features']=not any(('forward' in f or 'benchmark' in f or f.startswith('y_') or f in ['state','next_state','entry_date','exit_date']) for f in MAIN_FEATURES)
 checks['assumed_factor_availability_not_in_future']=bool((p.factor_assumed_available_date<=p.date).all())
 checks['factor_delay_at_least_62_days']=bool(((p.date-p.factor_latest_month_end).dt.days>=62).all())
 checks['one_oof_forecast_per_firm_date']=not q.duplicated(['date','company_id']).any()
 checks['all_models_forecast_identical_rows']=bool(np.isfinite(q[METHODS]).all().all())
 checks['test_period_after_first_training_years']=bool((q.date>='2022-01-01').all())
 checks['all_news_ingested_by_cutoff']=True
 raw=pd.read_parquet(D/'news_sample.parquet');checks['all_news_ingested_by_cutoff']=bool((pd.to_datetime(raw.archive_time.astype(str),format='%Y%m%d%H%M%S')<=pd.to_datetime(raw.date)+pd.Timedelta(hours=12)).all())
 boundaries=[];roundtrips=[];spectra=[];full_loadings=[]
 for h in [4,12]:
  audits=json.loads((O/f'fold_audit_primary_{h}.json').read_text())
  checks[f'training_targets_closed_before_cutoff_{h}']=all(pd.Timestamp(a['train_latest_target_date'])<pd.Timestamp(a['cutoff']) for a in audits)
  checks[f'training_features_before_test_{h}']=all(pd.Timestamp(a['train_max_feature_date'])<pd.Timestamp(a['test_min_feature_date']) for a in audits)
  good=p.dropna(subset=[f'y_{h}']);checks[f'holding_target_after_entry_{h}']=bool((good[f'exit_date_{h}']>good.entry_date).all())
  checks[f'entry_buffer_at_least_five_days_{h}']=bool((good.entry_date>=good.date+pd.Timedelta(days=5)).all())
  r=good.groupby(['date','region'])[f'exit_date_{h}'].max();g=good.groupby('date')[f'exit_date_{h}'].max();mx=pd.Series(p.set_index(['date','region']).index.map(r).to_numpy(),index=p.index);mx=mx.where(p[f'reg_n_{h}']>=5,p.date.map(g))
  for year in [2021,2022,2023,2024,2025]:
   cut=pd.Timestamp(year,1,1);mask=(p.date<cut)&(p[f'exit_date_{h}']<cut)&p[f'y_{h}'].notna();boundaries.append(dict(horizon=h,year=year,unknown_benchmark_label_rows=int((mask&(mx>=cut)).sum())))
 checks['benchmark_constituents_also_known_before_all_inner_and_outer_cutoffs']=all(r['unknown_benchmark_label_rows']==0 for r in boundaries)
 for year in [2022,2023,2024,2025]:
  cut=pd.Timestamp(year,1,1);tr=p[(p.date<cut)&(p.exit_date_4<cut)&p.y_4.notna()];te=p[p.date.dt.year==year]
  for method in METHODS:
   m=joblib.load(O/f'model_{year}_{method}.joblib');fs=m['prep']['features'];arr=tr[fs].replace([np.inf,-np.inf],np.nan).to_numpy(float)
   med=np.nanmedian(arr,axis=0);med=np.nan_to_num(med,nan=0);stat=m['prep']['imputer'].statistics_;median_ok=np.allclose(med,stat)
   filled=m['prep']['imputer'].transform(arr);lo,hi=np.quantile(filled,[.01,.99],axis=0);bounds_ok=np.allclose(lo,m['prep']['lower']) and np.allclose(hi,m['prep']['upper']);mean_ok=np.allclose(np.clip(filled,lo,hi).mean(axis=0),m['prep']['scaler'].mean_)
   sampled=te.iloc[::max(1,len(te)//35)];yp=predict(sampled,m);stored=q[q.year==year].set_index(['date','company_id']).loc[pd.MultiIndex.from_frame(sampled[['date','company_id']]),method].to_numpy();pred_ok=np.allclose(yp,stored,rtol=1e-8,atol=1e-10)
   roundtrips.append(dict(year=year,method=method,median_fit_train_only=bool(median_ok),winsor_train_only=bool(bounds_ok),scale_train_only=bool(mean_ok),saved_predictions_reproduce=bool(pred_ok)))
   if method=='pca_ridge':
    x,_=prep_transform(tr,m['prep']);pc=PCA(svd_solver='full').fit(x)
    for k,v in enumerate(pc.explained_variance_ratio_):spectra.append(dict(year=year,component=k+1,variance_ratio=float(v),cumulative=float(pc.explained_variance_ratio_[:k+1].sum())))
    for k,w in enumerate(pc.components_[:5]):
     sign=1 if w[np.argmax(np.abs(w))]>=0 else -1
     for feature,v in zip(fs,sign*w):full_loadings.append(dict(year=year,component=k+1,feature=feature,loading=float(v)))
 checks['saved_preprocessors_fit_only_training_rows']=all(r['median_fit_train_only'] and r['winsor_train_only'] and r['scale_train_only'] for r in roundtrips)
 checks['saved_models_reproduce_oof_predictions']=all(r['saved_predictions_reproduce'] for r in roundtrips)
 pd.DataFrame(spectra).to_csv(O/'pca_full_spectrum_training_only.csv',index=False);pd.DataFrame(full_loadings).to_csv(O/'pca_first_five_loadings_training_only.csv',index=False)
 result=dict(checks={k:bool(v) for k,v in checks.items()},all_pass=all(checks.values()),model_roundtrips=roundtrips,benchmark_boundaries=boundaries,diagnostics=dict(input_rows=len(p),oof_rows=len(q),oof_labeled_rows=int(q.y_4.notna().sum()),test_weeks=q.date.nunique(),test_firms=q.company_id.nunique(),test_countries=q.country.nunique(),source_hashes_pinned=True,absolute_four_week_returns_above_50pct=int((p.forward_return_4.abs()>.5).sum())))
 (O/'integrity_audit.json').write_text(json.dumps(result,indent=2));print(json.dumps({'all_pass':result['all_pass'],'checks':result['checks'],'diagnostics':result['diagnostics']},indent=2));assert result['all_pass']
if __name__=='__main__':main()
