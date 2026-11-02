from __future__ import annotations
import os
os.environ.setdefault('OMP_NUM_THREADS','2');os.environ.setdefault('OPENBLAS_NUM_THREADS','2');os.environ.setdefault('MKL_NUM_THREADS','2')
import pathlib,sys,json,time,warnings
R=pathlib.Path(__file__).resolve().parent;sys.path.insert(0,str(R/'deps'))
import numpy as np,pandas as pd,joblib
from scipy.stats import spearmanr
from sklearn.preprocessing import StandardScaler,OneHotEncoder
from sklearn.impute import SimpleImputer
from sklearn.decomposition import PCA
from sklearn.cross_decomposition import PLSRegression
from sklearn.linear_model import Ridge,ElasticNet
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.metrics import roc_auc_score
from threadpoolctl import threadpool_limits
from data_build import build,MAIN_FEATURES,PRICE_FEATURES,GROUPS
D=R/'data';O=R/'output';SEED=20261102
PRICE_FEATURES=PRICE_FEATURES+['ret20_x_market','mom_x_breadth','atr_x_marketvol']
METHODS=['price_ridge','all_ridge','elastic_net','pca_ridge','pls_ridge','small_boosting']
GRID={
'price_ridge':[dict(alpha=a) for a in [1,10,100]],
'all_ridge':[dict(alpha=a) for a in [1,10,100]],
'elastic_net':[dict(alpha=a) for a in [.0001,.001,.01]],
'pca_ridge':[dict(k=k,alpha=10) for k in [2,4,8,12,20]],
'pls_ridge':[dict(k=k,alpha=10) for k in [2,4,8,12]],
'small_boosting':[dict(max_iter=100,learning_rate=.05,max_leaf_nodes=7,min_samples_leaf=100,l2_regularization=10)]}

# Standard sklearn estimators plus numeric arrays only are serialized; no custom
# transformer class is needed to reload the fitted snapshots.
def prep_fit(df,features):
 raw=df[features].replace([np.inf,-np.inf],np.nan).to_numpy(float);missing=np.isnan(raw).astype(float)
 imputer=SimpleImputer(strategy='median',keep_empty_features=True);x=imputer.fit_transform(raw);lo,hi=np.quantile(x,[.01,.99],axis=0);x=np.clip(x,lo,hi);scale=StandardScaler().fit(x);x=scale.transform(x)
 enc=OneHotEncoder(handle_unknown='ignore',sparse_output=False,dtype=np.float64);cat=enc.fit_transform(df[['company_id','region']].astype(str));control=np.column_stack([cat,missing])
 return x,control,dict(features=features,imputer=imputer,lower=lo,upper=hi,scaler=scale,encoder=enc)
def prep_transform(df,p):
 raw=df[p['features']].replace([np.inf,-np.inf],np.nan).to_numpy(float);missing=np.isnan(raw).astype(float);x=p['imputer'].transform(raw);x=p['scaler'].transform(np.clip(x,p['lower'],p['upper']));control=np.column_stack([p['encoder'].transform(df[['company_id','region']].astype(str)),missing]);return x,control

def fit(df,features,y,method,config):
 x,c,p=prep_fit(df,features);reduce=None
 if method=='pca_ridge':reduce=PCA(n_components=min(config['k'],x.shape[1]),svd_solver='full',random_state=SEED);z=reduce.fit_transform(x)
 elif method=='pls_ridge':
  reduce=PLSRegression(n_components=min(config['k'],x.shape[1]),scale=False,max_iter=1000);reduce.fit(x,y);z=reduce.transform(x)
 else:z=x
 design=np.column_stack([z,c])
 if method=='elastic_net':est=ElasticNet(alpha=config['alpha'],l1_ratio=.5,max_iter=15000,tol=1e-5,selection='cyclic',random_state=SEED)
 elif method=='small_boosting':est=HistGradientBoostingRegressor(**config,early_stopping=False,random_state=SEED)
 else:est=Ridge(alpha=config.get('alpha',10),solver='lsqr',tol=1e-7)
 est.fit(design,y);return dict(prep=p,reducer=reduce,regressor=est,method=method,config=config)
def predict(df,m):
 x,c=prep_transform(df,m['prep']);z=m['reducer'].transform(x) if m['reducer'] is not None else x;return m['regressor'].predict(np.column_stack([z,c]))

def choose(df,h,year,features,method):
 inner_start=pd.Timestamp(year-1,1,1);outer_cut=pd.Timestamp(year,1,1)
 tr=df[(df.date<inner_start)&(df[f'exit_date_{h}']<inner_start)&df[f'y_{h}'].notna()]
 va=df[(df.date>=inner_start)&(df.date<outer_cut)&(df[f'exit_date_{h}']<outer_cut)&df[f'y_{h}'].notna()]
 assert len(tr)>1000 and len(va)>1000
 rows=[];best=None;bestloss=np.inf
 for cfg in GRID[method]:
  m=fit(tr,features,tr[f'y_{h}'].to_numpy(),method,cfg);yp=predict(va,m);loss=float(np.mean((va[f'y_{h}'].to_numpy()-yp)**2));rows.append(dict(config=cfg,mse=loss,train_n=len(tr),validation_n=len(va)))
  if loss<bestloss:bestloss=loss;best=cfg
 return best,rows

def bootstrap(dates,diff,block=13,iters=5000):
 s=pd.DataFrame({'date':pd.to_datetime(dates),'diff':diff}).groupby('date')['diff'].agg(['sum','count']).sort_index();idx=pd.date_range(s.index.min(),s.index.max(),freq='W-WED');s=s.reindex(idx,fill_value=0);sums=s['sum'].to_numpy();cnt=s['count'].to_numpy();n=len(s);effect=float(sums.sum()/cnt.sum());rng=np.random.default_rng(SEED+block)
 st=rng.integers(0,n,size=(iters,int(np.ceil(n/block))));ix=(st[:,:,None]+np.arange(block)[None,None,:])%n;ix=ix.reshape(iters,-1)[:,:n];b=sums[ix].sum(axis=1)/cnt[ix].sum(axis=1)
 p=float((1+np.sum(b-effect>=effect))/(iters+1));return dict(effect=effect,low=float(np.quantile(b,.025)),high=float(np.quantile(b,.975)),p_one_sided=p,block_weeks=block,iterations=iters,weeks=n)
def holm(ps):
 order=np.argsort(ps);out=np.zeros(len(ps));last=0
 for j,k in enumerate(order):last=max(last,min(1,(len(ps)-j)*ps[k]));out[k]=last
 return out.tolist()

def metrics(q,predcol,h):
 a=q.dropna(subset=[f'y_{h}',predcol]);y=a[f'y_{h}'].to_numpy();p=a[predcol].to_numpy();mse=float(np.mean((y-p)**2));null=float(np.mean(y*y));ics=[];top=[];hits=[]
 for _,g in a.groupby('date'):
  if len(g)<20:continue
  corr=spearmanr(g[f'y_{h}'],g[predcol]).statistic
  if np.isfinite(corr):ics.append(float(corr))
  # Within-region ranking avoids making an incidental regional allocation bet.
  chosen=[]
  for _,r in g.groupby('region'):chosen.append(r.nlargest(max(1,int(np.ceil(.2*len(r)))),predcol))
  pick=pd.concat(chosen);top.append(float(pick[f'y_{h}'].mean()));hits.append(float(((pick[f'forward_return_{h}']>=.10)&(pick[f'y_{h}']>0)).mean()))
 return dict(n=len(a),mse=mse,rmse=float(np.sqrt(mse)),r2_zero=1-mse/null,auc=float(roc_auc_score(y>0,p)),direction_accuracy=float(np.mean((p>0)==(y>0))),mean_rank_ic=float(np.mean(ics)),mean_top20_excess=float(np.mean(top)),top20_big_gain_hit=float(np.mean(hits)),null_mse=null)

def save_factors(m,year,h,scope):
 p=m['prep'];features=p['features'];method=m['method'];reduce=m['reducer'];base=O/'loadings';base.mkdir(exist_ok=True)
 if method=='pca_ridge':
  rows=[]
  for k,w in enumerate(reduce.components_):
   for feat,v in zip(features,w):rows.append(dict(scope=scope,horizon=h,year=year,component=k+1,feature=feat,loading=float(v),explained_variance_ratio=float(reduce.explained_variance_ratio_[k])))
  pd.DataFrame(rows).to_csv(base/f'{scope}_{h}_{year}_pca.csv',index=False)
 if method!='small_boosting':
  coef=m['regressor'].coef_;numeric=coef[:len(features)] if reduce is None else (reduce.components_.T@coef[:reduce.n_components_] if method=='pca_ridge' else reduce.x_rotations_@coef[:reduce.n_components])
  pd.DataFrame(dict(scope=scope,horizon=h,year=year,model=method,feature=features,standardized_coefficient=numeric)).to_csv(base/f'{scope}_{h}_{year}_{method}_coef.csv',index=False)

def run_panel(df,meta,h=4,scope='primary',ablations=True):
 ext=meta['extended_features'] if scope=='extended' else [];features=MAIN_FEATURES+ext
 out=[];selection=[];ablation_rows=[];fold_audit=[]
 for year in [2022,2023,2024,2025]:
  cutoff=pd.Timestamp(year,1,1);train=df[(df.date<cutoff)&(df[f'exit_date_{h}']<cutoff)&df[f'y_{h}'].notna()].copy();test=df[df.date.dt.year==year].copy()
  fold_audit.append(dict(scope=scope,horizon=h,year=year,cutoff=str(cutoff.date()),train_n=len(train),train_max_feature_date=str(train.date.max().date()),train_latest_target_date=str(train[f'exit_date_{h}'].max().date()),test_min_feature_date=str(test.date.min().date()),test_n=len(test),test_labeled_n=int(test[f'y_{h}'].notna().sum())))
  keep=['date','company_id','company','region','country','feature_price_date','entry_date',f'exit_date_{h}',f'y_{h}',f'forward_return_{h}',f'benchmark_{h}','eurusd_entry_date',f'eurusd_exit_date_{h}','coverage','archive_fraction'];q=test[keep].copy();q['scope']=scope;q['horizon']=h;q['year']=year;q['zero']=0.
  for method in METHODS:
   if scope=='extended' and method in ['price_ridge','small_boosting']:continue
   fs=PRICE_FEATURES if method=='price_ridge' else features
   cfg,grid=choose(df,h,year,fs,method);selection.append(dict(scope=scope,horizon=h,year=year,method=method,selected=cfg,inner_grid=grid))
   m=fit(train,fs,train[f'y_{h}'].to_numpy(),method,cfg);q[method]=predict(test,m);save_factors(m,year,h,scope)
   if h==4 and scope=='primary':joblib.dump(m,O/f'model_{year}_{method}.joblib',compress=3)
   if ablations and scope=='primary' and h==4 and method in ['all_ridge','elastic_net','pca_ridge','pls_ridge']:
    for group,columns in GROUPS.items():
     af=[f for f in fs if f not in columns];am=fit(train,af,train[f'y_{h}'].to_numpy(),method,cfg);ap=predict(test,am)
     v=pd.DataFrame({'date':test.date,'company_id':test.company_id,'scope':scope,'year':year,'method':method,'removed_group':group,'y':test[f'y_{h}'],'prediction_full':q[method].to_numpy(),'prediction_ablated':ap});ablation_rows.append(v)
   print(json.dumps(dict(scope=scope,horizon=h,year=year,method=method,selected=cfg,train=len(train),test=len(test))),flush=True)
  out.append(q)
 q=pd.concat(out,ignore_index=True);q.to_parquet(O/f'predictions_{scope}_{h}.parquet',index=False)
 (O/f'selection_{scope}_{h}.json').write_text(json.dumps(selection,indent=2));(O/f'fold_audit_{scope}_{h}.json').write_text(json.dumps(fold_audit,indent=2))
 if ablation_rows:
  ab=pd.concat(ablation_rows,ignore_index=True);ab.to_parquet(O/'group_ablation_predictions.parquet',index=False)
  a=[]
  for (method,group),g in ab.groupby(['method','removed_group']):
   g=g.dropna(subset=['y']);dif=(g.y-g.prediction_ablated)**2-(g.y-g.prediction_full)**2;e=bootstrap(g.date,dif);e.update(method=method,group=group);a.append(e)
  pd.DataFrame(a).to_csv(O/'group_ablation_summary.csv',index=False)
 return q

def summarize(q,h=4):
 cols=[m for m in ['zero']+METHODS if m in q];result={'overall':{m:metrics(q,m,h) for m in cols},'by_year':{},'by_region':{}}
 for year,g in q.groupby('year'):result['by_year'][str(year)]={m:metrics(g,m,h) for m in cols}
 for region,g in q.groupby('region'):
  if len(g)>100 and g[f'y_{h}'].dropna().nunique()>1:
   result['by_region'][region]={m:metrics(g,m,h) for m in cols}
 return result

def primary_tests(q):
 pairs=[(m,'price_ridge') for m in METHODS if m!='price_ridge']+[('pca_ridge','all_ridge'),('pls_ridge','all_ridge')];q=q.dropna(subset=['y_4']);rows=[]
 for model,base in pairs:
  y=q.y_4.to_numpy();dif=(y-q[base].to_numpy())**2-(y-q[model].to_numpy())**2;e=bootstrap(q.date,dif);e.update(model=model,baseline=base,relative_loss_reduction=e['effect']/np.mean((y-q[base])**2),sensitivity={str(b):bootstrap(q.date,dif,block=b) for b in [8,26]});rows.append(e)
 ps=holm([x['p_one_sided'] for x in rows])
 for e,p in zip(rows,ps):e['p_holm']=p
 return rows

def portfolio(q):
 # Predeclared diagnostic of ranking; fixed 4-week calendar grid, no stop search.
 # Missing selected/benchmark returns invalidate the whole cohort, never silently
 # rerank based on which selected stocks have a known profitable outcome.
 cohort=pd.read_csv(D/'cohort.csv');weights=cohort.groupby('region').size()/len(cohort);dates=sorted(q.date.unique())[::4];records=[];curves=[]
 for method in METHODS+['benchmark']:
  equity=10000.;previous=None;valid=0;skipped=[]
  for dt in dates:
   a=q[q.date==dt];picks=[];gross=0.;n_orders=0;bad=False;weight_total=0.
   for region,wr in weights.items():
    g=a[a.region==region]
    if not len(g):bad=True;break
    g=g if method=='benchmark' else g.nlargest(max(1,int(np.ceil(.2*len(g)))),method)
    if g[['forward_return_4','eurusd_entry_date','eurusd_exit_date_4']].isna().any().any():bad=True;break
    eur_return=(1+g.forward_return_4)*g.eurusd_entry_date/g.eurusd_exit_date_4-1
    gross+=float(wr*eur_return.mean());weight_total+=wr;n_orders+=2*len(g);picks.extend(g.company_id.tolist())
   if bad or abs(weight_total-1)>1e-7:skipped.append(str(pd.Timestamp(dt).date()));continue
   # Round-trip costs charged for the explicit close/reopen cohort schedule,
   # including names present in successive portfolios (conservative simplification).
   entry_fee=n_orders/2;exit_fee=n_orders/2;investable=max(0,equity-entry_fee)/1.001;end=investable*(1+gross)*.999-exit_fee;net=end/equity-1
   curves.append(dict(model=method,date=dt,exit_anchor=pd.Timestamp(dt)+pd.Timedelta(days=33),equity=end,gross_return=gross,net_return=net,orders=n_orders,holding_count=len(picks)))
   equity=end;valid+=1
  records.append(dict(model=method,end_eur=equity,initial_eur=10000,return_pct=(equity/10000-1)*100,valid_cohorts=valid,skipped_dates=skipped))
 pd.DataFrame(curves).to_csv(O/'portfolio_diagnostic_curves.csv',index=False);(O/'portfolio_diagnostic.json').write_text(json.dumps(records,indent=2));return records

def main():
 start=time.time();df,meta=build();primary=run_panel(df,meta,4,'primary',True);r=summarize(primary,4);r['primary_tests']=primary_tests(primary);r['portfolio_diagnostic']=portfolio(primary);(O/'results_primary.json').write_text(json.dumps(r,indent=2))
 print('Primary scores recorded. Running prespecified secondary analyses.',flush=True)
 secondary=run_panel(df,meta,12,'primary',False);(O/'results_12weeks.json').write_text(json.dumps(summarize(secondary,12),indent=2))
 extended=run_panel(df,meta,4,'extended',False);# carry original unchanged price baseline for reference
 extended=extended.merge(primary[['date','company_id','price_ridge']],on=['date','company_id'],how='left',validate='one_to_one');extended.to_parquet(O/'predictions_extended_4.parquet',index=False);(O/'results_extended.json').write_text(json.dumps(summarize(extended,4),indent=2))
 (O/'runtime.json').write_text(json.dumps({'elapsed_seconds':time.time()-start},indent=2));print('ALL DONE',round(time.time()-start),'seconds',flush=True)
if __name__=='__main__':
 with threadpool_limits(limits=2):main()
