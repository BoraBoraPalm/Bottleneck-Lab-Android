from __future__ import annotations
import pathlib,sys,json
R=pathlib.Path(__file__).resolve().parent
sys.path.insert(0,str(R/'deps'))
import numpy as np,pandas as pd
D=R/'data';O=R/'output'
DATES=pd.date_range('2019-01-02','2025-09-24',freq='W-WED')
FX={'HKD':('HKD=X',False,1),'KRW':('KRW=X',False,1),'JPY':('JPY=X',False,1),'TWD':('TWD=X',False,1),'CHF':('CHF=X',False,1),'EUR':('EURUSD=X',True,1),'GBP':('GBPUSD=X',True,1),'GBp':('GBPUSD=X',True,.01),'CNY':('CNY=X',False,1),'BRL':('BRL=X',False,1),'CAD':('CAD=X',False,1),'AUD':('AUDUSD=X',True,1),'ZAR':('ZAR=X',False,1),'ZAc':('ZAR=X',False,.01),'DKK':('DKK=X',False,1)}
GROUPS={
'momentum':['ret_5','ret_20','ret_60','ret_120','ret_252','mom_252_42'],
'trend':['ma50_gap','ma200_gap','high252_gap','low252_gap','drawdown60'],
'risk':['vol20','vol60','vol20_60','downside20','atr14_pct'],
'volume':['volume5_20','volume20_60'],
'market':['market_ret20','market_ret60','market_vol20','market_breadth'],
'news':['tone','positive','negative','polarity','dispersion','log_news','log_sources','translated_share','focus_share','coverage','archive_fraction','tone_4w','news_4w','tone_change','tone_lag1','log_news_lag1'],
'interactions':['ret20_x_market','mom_x_breadth','atr_x_marketvol','tone_x_attention','tone_change_x_vol','tone4_x_market']}
PRICE_GROUPS=['momentum','trend','risk','volume','market']
MAIN_FEATURES=sum(GROUPS.values(),[]);PRICE_FEATURES=sum((GROUPS[g] for g in PRICE_GROUPS),[])

def quote(t):
 r=json.loads((D/'prices'/(t+'.json')).read_text())['chart']['result'][0];q=r['indicators']['quote'][0]
 idx=pd.to_datetime(r['timestamp'],unit='s',utc=True).tz_convert(r['meta'].get('exchangeTimezoneName','UTC')).tz_localize(None).normalize()
 f=pd.DataFrame(q,index=idx);f['adjclose']=r['indicators'].get('adjclose',[{}])[0].get('adjclose',q['close'])
 return f.loc[~f.index.duplicated()].sort_index(),r['meta']

def target_at(f,dates):
 ix=f.index.searchsorted(dates);safe=np.minimum(ix,len(f)-1);day=f.index[safe]
 valid=(ix<len(f))&(day<=dates+pd.Timedelta(days=4))
 val=f.usdopen.to_numpy()[safe].copy();val[~valid]=np.nan
 ld=day.to_numpy().copy();ld[~valid]=np.datetime64('NaT')
 return val,ld,safe,valid

def build():
 cohort=pd.read_csv(D/'cohort.csv');frames=[];qcache={t:quote(t)[0] for t in set(v[0] for v in FX.values())};audit=[]
 for c in cohort.itertuples():
  f,meta=quote(c.ticker);f=f.dropna(subset=['close','open','high','low','adjclose','volume']);f=f[(f.close>0)&(f.open>0)&(f.volume>0)]
  if len(f)<260:continue
  adj=f.adjclose/f.close;cur=meta['currency'];usd=np.ones(len(f))
  if cur!='USD':
   ft,inv,mul=FX[cur];s=qcache[ft].close.dropna();usd=s.reindex(f.index-pd.Timedelta(days=1),method='ffill').to_numpy();usd=(usd if inv else 1/usd)*mul
  f['usdopen']=f.open*adj*usd
  r=f.adjclose.pct_change(fill_method=None);tech=pd.DataFrame(index=f.index)
  for n in [5,20,60,120,252]:tech[f'ret_{n}']=f.adjclose.pct_change(n,fill_method=None)
  tech['mom_252_42']=f.adjclose.shift(42)/f.adjclose.shift(252)-1
  for n in [50,200]:tech[f'ma{n}_gap']=f.adjclose/f.adjclose.rolling(n,min_periods=n).mean()-1
  tech['high252_gap']=f.adjclose/f.adjclose.rolling(252).max()-1;tech['low252_gap']=f.adjclose/f.adjclose.rolling(252).min()-1
  tech['drawdown60']=f.adjclose/f.adjclose.rolling(60).max()-1
  tech['vol20']=r.rolling(20).std();tech['vol60']=r.rolling(60).std();tech['vol20_60']=tech.vol20/tech.vol60
  tech['downside20']=np.sqrt(r.clip(upper=0).pow(2).rolling(20).mean())
  tr=pd.concat([(f.high-f.low)*adj,(f.high*adj-f.adjclose.shift()).abs(),(f.low*adj-f.adjclose.shift()).abs()],axis=1).max(axis=1)
  tech['atr14_pct']=tr.rolling(14).mean()/f.adjclose
  tech['volume5_20']=f.volume.rolling(5).mean()/f.volume.rolling(20).mean();tech['volume20_60']=f.volume.rolling(20).mean()/f.volume.rolling(60).mean()
  x=tech.reindex(DATES-pd.Timedelta(days=1),method='ffill').copy();x.index=DATES;x.index.name='date';x=x.reset_index()
  x['feature_price_date']=pd.Series(f.index,index=f.index).reindex(DATES-pd.Timedelta(days=1),method='ffill').to_numpy()
  x['company_id']=c.rank;x['company']=c.company;x['ticker']=c.ticker;x['region']=c.region;x['country']=c.country
  mon=DATES+pd.Timedelta(days=5);entry,ed,ei,ev=target_at(f,mon);x['entry_date']=ed;x['entry_usd']=entry
  for h in [4,12]:
   exit_,xd,xi,xv=target_at(f,mon+pd.Timedelta(weeks=h));x[f'exit_date_{h}']=xd;x[f'forward_return_{h}']=exit_/entry-1
   if pd.notna(c.end_date):
    too_late=pd.to_datetime(x[f'exit_date_{h}'])>pd.Timestamp(c.end_date);x.loc[too_late,[f'forward_return_{h}',f'exit_date_{h}']]=[np.nan,pd.NaT]
  valid=(x.feature_price_date<=x.date-pd.Timedelta(days=1))&((x.date-x.feature_price_date).dt.days<=8)&x[GROUPS['momentum']+GROUPS['trend']].notna().all(axis=1)
  if pd.notna(c.end_date):valid&=x.date<=pd.Timestamp(c.end_date)
  frames.append(x.loc[valid].copy());audit.append(dict(company=c.company,ticker=c.ticker,currency=cur,feature_rows=int(valid.sum())))
 panel=pd.concat(frames,ignore_index=True).sort_values(['date','company_id']).reset_index(drop=True)
 market=panel.groupby('date').agg(market_ret20=('ret_20','mean'),market_ret60=('ret_60','mean'),market_vol20=('vol20','mean'),market_breadth=('ma200_gap',lambda s:float((s>0).mean())))
 panel=panel.join(market,on='date')
 news=pd.read_parquet(D/'news_features.parquet');news['date']=pd.to_datetime(news.date)
 panel=panel.merge(news[['date','company_id']+GROUPS['news']],on=['date','company_id'],how='left',validate='one_to_one')
 panel['ret20_x_market']=panel.ret_20*panel.market_ret60;panel['mom_x_breadth']=panel.mom_252_42*panel.market_breadth;panel['atr_x_marketvol']=panel.atr14_pct*panel.market_vol20
 panel['tone_x_attention']=panel.tone*panel.log_news;panel['tone_change_x_vol']=panel.tone_change*panel.vol20;panel['tone4_x_market']=panel.tone_4w*panel.market_ret60
 for h in [4,12]:
  b=panel.groupby(['date','region'])[f'forward_return_{h}'].agg(['mean','count']);b.columns=[f'reg_benchmark_{h}',f'reg_n_{h}'];panel=panel.join(b,on=['date','region'])
  glob=panel.groupby('date')[f'forward_return_{h}'].transform('mean');panel[f'benchmark_{h}']=panel[f'reg_benchmark_{h}'].where(panel[f'reg_n_{h}']>=5,glob)
  panel[f'y_{h}']=panel[f'forward_return_{h}']-panel[f'benchmark_{h}']
 # Research-factor regime add-on. Availability lag is conservative but original
 # data vintages/holdings are unavailable; never part of the primary PIT claim.
 factors=pd.read_csv(R/'sources'/'behavioral_liquid_original_inputs.csv');factors.index=pd.PeriodIndex(factors.iloc[:,0],freq='M').to_timestamp('M')
 base=['Mom12m','EarningsSurprise','REV6','AnnouncementReturn','BM','GP','Mkt-RF','SMB','HML','RMW','CMA','Mom'];lagged=pd.DataFrame(index=factors.index+pd.Timedelta(days=62))
 for col in base:
  lagged['factor_last_'+col]=factors[col].to_numpy();lagged['factor_3m_'+col]=((1+factors[col]).rolling(3).apply(np.prod,raw=True)-1).to_numpy()
 lagged['factor_latest_month_end']=factors.index.to_numpy();lagged['factor_assumed_available_date']=lagged.index.to_numpy()
 mapped=lagged.reindex(DATES,method='ffill');mapped.index.name='date';panel=panel.join(mapped,on='date');extended=[c for c in lagged.columns if c.startswith('factor_') and c not in ['factor_latest_month_end','factor_assumed_available_date']]
 # EUR per USD based on last actual FX close strictly before session date.
 eur=qcache['EURUSD=X'].close.dropna()
 for k in ['entry_date','exit_date_4','exit_date_12']:
  ds=pd.DatetimeIndex(panel[k]);valid=~ds.isna();vals=np.full(len(panel),np.nan);vals[valid]=eur.reindex(ds[valid]-pd.Timedelta(days=1),method='ffill').to_numpy();panel['eurusd_'+k]=vals
 p=D/'analysis_panel.parquet';tmp=D/'analysis_panel.tmp.parquet';panel.to_parquet(tmp,index=False);assert len(pd.read_parquet(tmp))==len(panel);tmp.replace(p)
 meta=dict(rows=len(panel),companies=panel.company_id.nunique(),countries=panel.country.nunique(),start=str(panel.date.min().date()),end=str(panel.date.max().date()),main_features=MAIN_FEATURES,price_features=PRICE_FEATURES,extended_features=extended,groups=GROUPS,source_audit=audit,news_state_and_future_columns_used=False)
 (O/'dataset_info.json').write_text(json.dumps(meta,indent=2));print('Panel complete:',len(panel),'rows,',panel.company_id.nunique(),'firms,',len(MAIN_FEATURES),'primary numeric features.',flush=True)
 return panel,meta
if __name__=='__main__':build()
