from __future__ import annotations
import os
os.environ.setdefault('OMP_NUM_THREADS','2');os.environ.setdefault('OPENBLAS_NUM_THREADS','2')
import pathlib,json,datetime,hashlib,warnings
import numpy as np,pandas as pd
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler,OneHotEncoder
from sklearn.impute import SimpleImputer
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import make_pipeline
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import log_loss,roc_auc_score,accuracy_score
import joblib
from cohort import COHORT
from prices import FX
ROOT=pathlib.Path(__file__).resolve().parent;D=ROOT/'data';O=ROOT/'output';O.mkdir(exist_ok=True)
DATES=pd.date_range('2019-01-02','2025-12-31',freq='W-WED');SEED=20261101
CATFEATS=['tone','polarity','dispersion','log_news','log_sources']
NEWSFEATS=['tone','positive','negative','polarity','dispersion','log_news','log_sources','translated_share','focus_share','coverage','archive_fraction','tone_4w','news_4w','tone_change','tone_lag1','log_news_lag1']
PRICEFEATS=['ret_5','ret_20','ret_60','vol_20','vol_60','volume_ratio']

def load_quote(t):
 p=D/'prices'/(t+'.json')
 if not p.exists():return None
 try:
  r=json.loads(p.read_text())['chart']['result'][0];q=r['indicators']['quote'][0]
  tz=r['meta'].get('exchangeTimezoneName','UTC')
  date=pd.to_datetime(r['timestamp'],unit='s',utc=True).tz_convert(tz).tz_localize(None).normalize()
  df=pd.DataFrame(q,index=date)
  ac=r['indicators'].get('adjclose',[{}])[0].get('adjclose',q['close'])
  df['adjclose']=ac;df['adjopen']=df['open']*df.adjclose/df.close
  return df[~df.index.duplicated()].sort_index(),r['meta']
 except Exception:return None

def build_price_panel():
 rows=[];audit=[]
 fx={c:load_quote(v[0]) for c,v in FX.items()}
 for c in COHORT:
  loaded=load_quote(c['ticker'])
  if loaded is None:audit.append(dict(company=c['company'],error='No chart'));continue
  f,meta=loaded;f=f.dropna(subset=['adjclose','adjopen','volume'])
  f=f[(f.adjclose>0)&(f.adjopen>0)&(f.volume>0)]
  cur=meta.get('currency');rfx=np.ones(len(f))
  if cur!='USD':
   if cur not in fx or fx[cur] is None:audit.append(dict(company=c['company'],error='No FX '+str(cur)));continue
   fxframe=fx[cur][0]
   vals=fxframe.close.reindex(f.index-pd.Timedelta(days=1),method='ffill').to_numpy()
   rfx=vals if FX[cur][1] else 1/vals
   if cur in ['GBp','ZAc']:rfx=rfx/100
  f['usdopen']=f.adjopen*rfx
  f['ret_5']=f.adjclose.pct_change(5);f['ret_20']=f.adjclose.pct_change(20);f['ret_60']=f.adjclose.pct_change(60)
  r=f.adjclose.pct_change();f['vol_20']=r.rolling(20,min_periods=15).std();f['vol_60']=r.rolling(60,min_periods=45).std()
  f['volume_ratio']=f.volume.rolling(5).mean()/f.volume.rolling(20).mean();f['meanvolume20']=f.volume.rolling(20).mean()
  for dt in DATES:
   if c['end_date'] and dt>pd.Timestamp(c['end_date']):continue
   prior=f.loc[:dt-pd.Timedelta(days=1)]
   if len(prior)<61 or (dt-prior.index[-1]).days>8:continue
   past=prior.iloc[-1]
   # News Wednesday; next Monday at least 4.5 days later (not same-day prices).
   mon=dt+pd.Timedelta(days=5);nmon=mon+pd.Timedelta(days=7)
   entry=f.loc[mon:mon+pd.Timedelta(days=4)];exit_=f.loc[nmon:nmon+pd.Timedelta(days=4)]
   row=dict(date=dt,company_id=c['rank'],company=c['company'],country=c['country'],region=c['region'],ticker=c['ticker'],currency=cur,feature_price_date=prior.index[-1])
   row.update({v:float(past[v]) for v in PRICEFEATS})
   if len(entry) and len(exit_):
    row.update(entry_date=entry.index[0],exit_date=exit_.index[0],forward_return=float(exit_.usdopen.iloc[0]/entry.usdopen.iloc[0]-1),local_forward_return=float(exit_.adjopen.iloc[0]/entry.adjopen.iloc[0]-1),forward_volume_ratio=float(entry.volume.mean()/past.meanvolume20))
   rows.append(row)
  audit.append(dict(company=c['company'],ticker=c['ticker'],currency=cur,first=str(f.index.min().date()),last=str(f.index.max().date()),observations=len(f)))
 panel=pd.DataFrame(rows)
 # Small regions lack a comparable peer group. Use the entire preselected global
 # cohort in those regions; no benchmark assembled from future winners.
 bench=panel.groupby(['date','region']).forward_return.agg(['mean','count']).rename(columns={'mean':'regional_return','count':'regional_n'})
 panel=panel.join(bench,on=['date','region'])
 global_=panel.groupby('date').forward_return.mean();panel['benchmark_return']=panel.regional_return.where(panel.regional_n>=5,panel.date.map(global_))
 bench_l=panel.groupby(['date','region']).local_forward_return.transform('mean');global_l=panel.groupby('date').local_forward_return.transform('mean')
 panel['local_benchmark_return']=bench_l.where(panel.regional_n>=5,global_l)
 panel['excess_return']=panel.forward_return-panel.benchmark_return
 panel['y_return']=(panel.excess_return>0).astype(float).where(panel.forward_return.notna())
 panel['y_volume']=(panel.forward_volume_ratio>1).astype(float).where(panel.forward_volume_ratio.notna())
 panel.to_parquet(D/'price_panel.parquet',index=False)
 (O/'price_coverage.json').write_text(json.dumps(audit,indent=2))
 return panel

def focused_url(row):
 # URL-slug focus is a noisy, pre-outcome robustness proxy, not an NLP truth label.
 from urllib.parse import unquote,urlparse
 from cohort import norm
 path=norm(unquote(urlparse(row.url).path))
 c=next(c for c in COHORT if c['rank']==row.company_id)
 aliases=[a for a in c['aliases'].split(';') if len(a.replace(' ',''))>=4]
 if row.company_id==20:aliases=['visa inc','visa stock','visa shares','visa earnings','visa payment','visa card']
 return any((' '+a+' ') in (' '+path+' ') for a in aliases)

def aggregate_news(news):
 n=news.copy();n['date']=pd.to_datetime(n.date)
 # Enforce contemporaneous GKG ingestion. Raw 15-minute file may include dates
 # earlier than its timestamp, but never use an archive after the cutoff.
 assert (pd.to_datetime(n.archive_time.astype(str),format='%Y%m%d%H%M%S',errors='coerce')<=n.date+pd.Timedelta(hours=12)).all()
 n['focused']=n.apply(focused_url,axis=1)
 n[['date','company_id','language','source','url','focused']].sample(min(100,len(n)),random_state=SEED).to_csv(O/'entity_audit_sample.csv',index=False)
 a=n.groupby(['date','company_id']).agg(tone=('tone','mean'),positive=('positive','mean'),negative=('negative','mean'),polarity=('polarity','mean'),dispersion=('tone','std'),n_news=('url','nunique'),n_sources=('source','nunique'),translated_share=('translated','mean'),focus_share=('focused','mean'))
 idx=pd.MultiIndex.from_product([DATES,[c['rank'] for c in COHORT]],names=['date','company_id']);a=a.reindex(idx).reset_index()
 manifests=json.loads((D/'archive_manifest.json').read_text())
 available={str(dt.date()):sum(m.get('ok',False) for m in manifests if m['date']==str(dt.date()))/2 for dt in DATES}
 a['archive_fraction']=a.date.dt.strftime('%Y-%m-%d').map(available)
 # An unavailable archive is missing measurement, not zero company attention.
 incomplete=a.archive_fraction<1
 for var in ['tone','positive','negative','polarity','dispersion','n_news','n_sources','translated_share','focus_share']:
  a.loc[incomplete,var]=np.nan
 a['coverage']=((a.n_news>=2)&(a.n_sources>=2)).astype(int)
 a['log_news']=np.log1p(a.n_news.fillna(0));a['log_sources']=np.log1p(a.n_sources.fillna(0));a['dispersion']=a.dispersion.fillna(0)
 a.loc[incomplete,['log_news','log_sources','dispersion']]=np.nan
 a=a.sort_values(['company_id','date'])
 for var in ['tone','log_news']:
  a[var+'_lag1']=a.groupby('company_id')[var].shift(1)
 a['tone_change']=a.tone-a.tone_lag1
 a['tone_4w']=a.groupby('company_id').tone.transform(lambda s:s.rolling(4,min_periods=1).mean())
 a['news_4w']=a.groupby('company_id').n_news.transform(lambda s:s.fillna(0).rolling(4,min_periods=1).sum())
 a['region']=a.company_id.map({c['rank']:c['region'] for c in COHORT})
 return a,n

def categories(a):
 fit=(a.date<'2022-01-01')&(a.coverage==1)
 scaler=StandardScaler().fit(a.loc[fit,CATFEATS]);km=KMeans(n_clusters=6,n_init=30,random_state=SEED).fit(scaler.transform(a.loc[fit,CATFEATS]))
 a['state']=-1;good=a.coverage==1;a.loc[good,'state']=km.predict(scaler.transform(a.loc[good,CATFEATS]))
 centers=pd.DataFrame(scaler.inverse_transform(km.cluster_centers_),columns=CATFEATS);centers['state']=range(6)
 # Deterministic display order by valence; names reviewed only from these centers.
 order=centers.sort_values('tone').state.tolist();mapping={old:new for new,old in enumerate(order)}
 a['state']=a.state.map(lambda s:mapping.get(s,-1));centers['state']=centers.state.map(mapping);centers=centers.sort_values('state');centers['approx_articles']=np.expm1(centers.log_news)
 centers.to_csv(O/'category_centers.csv',index=False)
 a['next_state']=a.groupby('company_id').state.shift(-1)
 a.to_parquet(D/'news_features.parquet',index=False)
 joblib.dump(dict(scaler=scaler,clusterer=km,order_mapping=mapping,features=CATFEATS),O/'category_model.joblib')
 return a,centers

def pipeline(num,cat):
 numeric=make_pipeline(SimpleImputer(strategy='median',add_indicator=True),StandardScaler())
 pre=ColumnTransformer([('numeric',numeric,num),('categorical',OneHotEncoder(handle_unknown='ignore'),cat)])
 return make_pipeline(pre,LogisticRegression(C=1,max_iter=2500,random_state=SEED))

def split(df,which):
 # Two complete embargo weeks at each boundary, plus no training target after gap.
 if which=='train':return (df.date>='2019-01-01')&(df.date<='2021-12-08')
 if which=='validation':return (df.date>='2022-01-19')&(df.date<='2022-12-07')
 return (df.date>='2023-01-18')&(df.date<='2025-12-17')

def binary_metrics(y,p):
 return dict(n=len(y),base_rate=float(np.mean(y)),brier=float(np.mean((y-p)**2)),logloss=float(log_loss(y,p,labels=[0,1])),auc=float(roc_auc_score(y,p)),accuracy=float(accuracy_score(y,p>=.5)))

def losses_multi(y,p):return -np.log(np.clip(p[np.arange(len(y)),np.asarray(y,int)],1e-12,1))
def multi_metrics(y,p):
 oh=np.eye(6)[np.asarray(y,int)]
 return dict(n=len(y),logloss=float(losses_multi(y,p).mean()),brier=float(np.mean(np.sum((p-oh)**2,axis=1))),accuracy=float(np.mean(np.argmax(p,axis=1)==y)))

def bootstrap_effect(dates,dif,block=8,iterations=5000):
 d=pd.DataFrame({'date':pd.to_datetime(dates),'d':dif});a=d.groupby('date').d.agg(['sum','count']).sort_index()
 # Preserve genuinely missing calendar weeks in the bootstrap sequence.
 idx=pd.date_range(a.index.min(),a.index.max(),freq='W-WED');a=a.reindex(idx,fill_value=0)
 sums=a['sum'].to_numpy();counts=a['count'].to_numpy();n=len(a);effect=float(sums.sum()/counts.sum());rng=np.random.default_rng(SEED+block)
 starts=rng.integers(0,n,size=(iterations,int(np.ceil(n/block))));ix=(starts[:,:,None]+np.arange(block)[None,None,:])%n;ix=ix.reshape(iterations,-1)[:,:n]
 b=sums[ix].sum(axis=1)/counts[ix].sum(axis=1)
 # Centered bootstrap one-sided H0: effect<=0, H1: reduction in loss>0.
 p=float((1+np.sum((b-effect)>=effect))/(iterations+1))
 return dict(effect=effect,ci_low=float(np.quantile(b,.025)),ci_high=float(np.quantile(b,.975)),p_one_sided=p,block_weeks=block,weeks=n,iterations=iterations)

def holm(ps):
 order=np.argsort(ps);out=np.zeros(len(ps));last=0
 for j,k in enumerate(order):last=max(last,min(1,(len(ps)-j)*ps[k]));out[k]=last
 return out.tolist()

def fit_all(panel,a):
 summary={};predictions=[];effects=[];models={}
 n=a.copy();n['state_str']=n.state.astype(str)
 smask=(n.state>=0)&(n.next_state>=0)&(n.next_state.notna());nd=n.loc[smask].copy();nd['target']=nd.next_state.astype(int)
 train=nd.loc[split(nd,'train')];classes=np.arange(6)
 freq=(np.bincount(train.target,minlength=6)+1)/(len(train)+6)
 trans=np.ones((6,6))
 for row in train.itertuples():trans[int(row.state),int(row.target)]+=1
 trans/=trans.sum(axis=1,keepdims=True)
 smodel=pipeline(NEWSFEATS,['state_str','company_id','region']);smodel.fit(train,train.target);models['state_forecast']=smodel
 summary['state_forecast']={}
 for part in ['validation','test']:
  q=nd.loc[split(nd,part)].copy();y=q.target.to_numpy();p=smodel.predict_proba(q);p=p[:,[list(smodel.classes_).index(c) for c in classes]];pm=trans[q.state.to_numpy(int)];pf=np.tile(freq,(len(q),1))
  summary['state_forecast'][part]={k:multi_metrics(y,v) for k,v in [('climatology',pf),('transition',pm),('news_model',p)]}
  if part=='test':
   dif=losses_multi(y,pm)-losses_multi(y,p);e=bootstrap_effect(q.date,dif);e['target']='state_forecast';effects.append(e)
   q['target_kind']='state_forecast';q['observed']=y;q['predicted_state']=p.argmax(axis=1);q['loss_model']=losses_multi(y,p);q['loss_baseline']=losses_multi(y,pm)
   for k in range(6):q[f'p_state_{k}']=p[:,k]
   predictions.append(q[['date','company_id','region','state','target_kind','observed','predicted_state','loss_model','loss_baseline']+[f'p_state_{k}' for k in range(6)]])
 # Price/reaction tasks include no-news observations; unknown is explicit.
 p=panel.merge(a.drop(columns=['region']),on=['date','company_id'],how='left',validate='one_to_one');p['state_str']=p.state.fillna(-1).astype(str)
 for task in ['return','volume']:
  df=p.dropna(subset=['y_'+task]+PRICEFEATS).copy();tr=df.loc[split(df,'train')];y=tr['y_'+task].astype(int)
  price=pipeline(PRICEFEATS,['company_id','region']);news=pipeline(PRICEFEATS+NEWSFEATS,['state_str','company_id','region'])
  price.fit(tr,y);news.fit(tr,y);models[task+'_price']=price;models[task+'_news_price']=news
  summary[task]={}
  for part in ['validation','test']:
   q=df.loc[split(df,part)].copy();y=q['y_'+task].to_numpy();pp=price.predict_proba(q)[:,1];pn=news.predict_proba(q)[:,1];pc=np.repeat(np.mean(tr['y_'+task]),len(q))
   summary[task][part]={k:binary_metrics(y,v) for k,v in [('frequency',pc),('price_only',pp),('news_price',pn)]}
   if part=='test':
    dif=(y-pp)**2-(y-pn)**2;e=bootstrap_effect(q.date,dif);e['target']=task;effects.append(e)
    summary[task]['regions']={reg:{'price_only':binary_metrics(y[ix],pp[ix]),'news_price':binary_metrics(y[ix],pn[ix])} for reg in sorted(q.region.unique()) if len(ix:=np.flatnonzero(q.region.to_numpy()==reg))>=20 and len(np.unique(y[ix]))==2}
    # Descriptive conditional frequencies, not effects caused by mood.
    q['p_baseline']=pp;q['p_model']=pn;q['observed']=y;q['target_kind']=task;q['loss_baseline']=(y-pp)**2;q['loss_model']=(y-pn)**2
    predictions.append(q[['date','company_id','region','state','coverage','focus_share','target_kind','observed','p_baseline','p_model','loss_baseline','loss_model','forward_return','excess_return','forward_volume_ratio']])
    summary[task]['by_state']={str(int(s)):dict(n=len(g),event_rate=float(g.observed.mean()),predicted_rate=float(g.p_model.mean()),baseline_rate=float(g.p_baseline.mean()),mean_forward_return=float(g.forward_return.mean()),mean_excess_return=float(g.excess_return.mean()),mean_forward_volume_ratio=float(g.forward_volume_ratio.mean())) for s,g in q.groupby('state')}
    summary[task]['subset']={}
    for label,sel in [('sufficient_news',q.coverage==1),('focused_news',q.focus_share>=.5),('low_news',q.coverage!=1),('local_return_sensitivity',pd.Series(False,index=q.index))]:
     if label=='local_return_sensitivity' and task=='return':
      yl=(q.local_forward_return>q.local_benchmark_return).to_numpy(int);summary[task]['subset'][label]={'price_only':binary_metrics(yl,pp),'news_price':binary_metrics(yl,pn)}
     elif sel.sum()>=50 and len(q.loc[sel,'observed'].unique())==2:
      summary[task]['subset'][label]={'price_only':binary_metrics(y[sel],pp[sel]),'news_price':binary_metrics(y[sel],pn[sel])}
    summary[task]['sensitivity_blocks']={str(b):bootstrap_effect(q.date,dif,block=b) for b in [4,13]}
 adj=holm([e['p_one_sided'] for e in effects])
 for e,h in zip(effects,adj):e['p_holm']=h
 summary['primary_tests']=effects
 preds=pd.concat(predictions,ignore_index=True);preds.to_parquet(O/'test_predictions.parquet',index=False)
 pd.DataFrame(effects).to_csv(O/'primary_tests.csv',index=False)
 (O/'results.json').write_text(json.dumps(summary,indent=2,allow_nan=True))
 joblib.dump(models,O/'forecast_models.joblib')
 return summary,preds

def main():
 news=pd.read_parquet(D/'news_sample.parquet');a,n=aggregate_news(news);a,centers=categories(a)
 print('CATEGORY CENTERS (without price outcomes):\n',centers.to_string(index=False),flush=True)
 print('News rows',len(n),'languages',n.language.nunique(),'firm-weeks',int(a.coverage.sum()),'by year',a.groupby(a.date.dt.year).coverage.sum().to_dict(),flush=True)
 print('Fitting models with frozen protocol...',flush=True)
 panel=build_price_panel();summary,pred=fit_all(panel,a)
 coverage=dict(news_rows=len(n),unique_urls=n.url.nunique(),languages=n.language.nunique(),companies_with_news=n.company_id.nunique(),countries=len({c['country'] for c in COHORT}),raw_firm_weeks=len(a),sufficient_firm_weeks=int(a.coverage.sum()),news_by_year=a.groupby(a.date.dt.year).coverage.sum().to_dict(),price_rows=len(panel),price_companies=panel.company_id.nunique(),test_weeks=int(pred.date.nunique()),regions=sorted(panel.region.unique()),train_only_clustering=True)
 (O/'coverage.json').write_text(json.dumps(coverage,indent=2));print(json.dumps(summary['primary_tests'],indent=2),flush=True)
if __name__=='__main__':main()
