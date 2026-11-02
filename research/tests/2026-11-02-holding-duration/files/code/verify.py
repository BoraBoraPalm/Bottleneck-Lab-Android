"""Integrity and temporal checks against frozen inputs, not a new search."""
import pathlib,sys,json,hashlib,importlib.metadata,datetime
R=pathlib.Path(__file__).resolve().parents[1];sys.path.insert(0,str(R.parent/'pca_forecast_study/deps'))
import numpy as np,pandas as pd
from run_trading import prepare,simulate
from run_academic import build
O=R/'output';D=R/'data'

def main():
 checks=[]
 def check(ok,label):
  assert bool(ok),label
  checks.append(label)
 check(hashlib.sha256((R/'sources/protocol_initial.md').read_bytes()).hexdigest()==json.loads((O/'protocol_initial_lock.json').read_text())['sha256'],'Provenance: exact initially locked protocol retained')
 check(hashlib.sha256((R/'sources/run_academic_before_portable_cache.py').read_bytes()).hexdigest()==json.loads((O/'academic_code_lock.json').read_text())['sha256'],'Provenance: original A code matches pre-result lock')
 check(hashlib.sha256((R/'sources/run_forecast_before_portable_cache.py').read_bytes()).hexdigest()==json.loads((O/'forecast_code_lock.json').read_text())['sha256']['code/run_forecast_horizons.py'],'Provenance: original C code matches pre-result lock')
 check(hashlib.sha256((R/'code/run_trading.py').read_bytes()).hexdigest()==json.loads((O/'trading_code_lock_execution_caps.json').read_text())['code_sha256'],'Provenance: final B code matches documented integrity correction')
 x,market,meta=build();a=pd.read_csv(O/'academic_returns.csv');choices=json.loads((O/'academic_choices.json').read_text())
 check(len(choices)==20*12,'A: 20 strategies x 12 annual past-only selections')
 for c in choices:
  check(pd.Period(c['train_end'],'M')<pd.Period(str(c['year'])+'-01','M'),'A: train end before selected year '+c['strategy']+' '+str(c['year']))
  check(len(pd.period_range(c['train_start'],c['train_end'],freq='M'))==120,'A: 120 completed months '+c['strategy']+' '+str(c['year']))
  best=max([1,3,6,12],key=lambda k:(c['all_scores'][str(k)],k));check(best==c['chosen_months'],'A: choice matches locked score '+c['strategy']+' '+str(c['year']))
  g=a[(a.strategy==c['strategy'])&(a.policy=='past_selected')&a.month.str.startswith(str(c['year']))];w=meta['families'][c['strategy']];idx=pd.PeriodIndex(g.month,freq='M');expected=sum(ww*(market.loc[idx].to_numpy() if sig=='Market' else x.loc[idx,(sig,best)].to_numpy()) for sig,ww in w.items())-.01/12*(1-w.get('Market',0))
  check(np.allclose(g.net_return,expected,rtol=1e-12,atol=1e-14),'A: selected returns reconstructed '+c['strategy']+' '+str(c['year']))
 d=prepare();check(d['calendar'].max()<=pd.Timestamp('2025-12-31'),'B: input cache cuts all price/FX arrays at 2025-12-31')
 b=pd.read_csv(O/'trading_metrics.csv');paths=pd.read_parquet(O/'trading_daily_paths.parquet');bc=json.loads((O/'trading_choices.json').read_text());tr=pd.read_csv(O/'trading_closed_trades.csv');dec=pd.read_csv(O/'trading_decisions.csv')
 check(len(b)==12*7 and len(bc)==12*7,'B: complete twelve-policy, six-interval and adaptive grid')
 check(b.max_positions.max()<=10 and b.max_region_positions.max()<=4,'B: actual entry respects total and region position caps in every evaluation')
 check(paths.cash.min()>=-1e-7 and np.isfinite(paths.equity).all(),'B: no borrowed cash and finite equity')
 check((tr.holding_sessions>=1).all() and (pd.to_datetime(tr.exit_day)>=pd.to_datetime(tr.buy_day)).all(),'B: completed trades have causal entry/exit dates')
 for c in bc:
  year=c['year'];check(pd.Timestamp(c['training_end'])<pd.Timestamp(year,1,1),'B: completed training ends before '+c['strategy']+' '+str(year))
  best=max(c['candidates'],key=lambda z:(z['metrics']['information_ratio'],z['interval']))['interval'];check(best==c['selected_interval'],'B: duration equals past score winner '+c['strategy']+' '+str(year))
 for model in sorted(b.strategy.unique()):
  annual={c['year']:c['selected_interval'] for c in bc if c['strategy']==model};f,_,_,_=simulate(d,model,20,'2019-01-01','2025-12-31',annual=annual,detail=True);saved=paths[(paths.strategy==model)&(paths.policy=='past_selected')].sort_values('date')
  check(np.array_equal(f.equity.to_numpy(),saved.equity.to_numpy()),'B: exact replay from frozen cache '+model)
  ds=dec[(dec.strategy==model)&(dec.policy=='past_selected')];check(all(row.interval==annual[pd.Timestamp(row.date).year] for row in ds.itertuples()),'B: annual choice used only at a new review '+model)
 p=pd.read_parquet(D/'forecast_horizon_panel.parquet');fm=json.loads((D/'pca_feature_metadata.json').read_text());features=fm['main_features'];q=pd.read_parquet(O/'forecast_horizon_predictions.parquet');audit=json.loads((O/'forecast_horizon_audit.json').read_text());fc=json.loads((O/'forecast_horizon_choices.json').read_text())
 check(len(features)==44 and not any(s.startswith(('y_','return_','exit_','available_')) or s in ['state','next_state','observed_excess'] for s in features),'C: only 44 declared past features; no target/state columns')
 check(len(fc)==7*3*5,'C: all horizons, years and model choices present')
 keysets=[set(zip(g.date,g.company_id)) for _,g in q.groupby('horizon_weeks')];check(all(k==keysets[0] for k in keysets),'C: identical stock-date evaluation sample at all horizons')
 for row in audit:
  h=row['horizon'];cutoff=pd.Timestamp(row['cutoff']);t=p[(p.date<cutoff)&(p[f'available_{h}']<cutoff)&p[f'y_{h}'].notna()]
  check(len(t)==row['train_rows'] and t[f'available_{h}'].max()==pd.Timestamp(row['latest_known_target']),'C: train labels and regional benchmark matured before cutoff '+str(h)+' '+str(row['year']))
  check((t[f'exit_{h}']<=t[f'available_{h}']).all(),'C: benchmark availability covers own exit '+str(h)+' '+str(row['year']))
 check(np.isfinite(q[['observed_excess','zero','price_ridge','elastic_net','pca_ridge','pls_ridge','small_boosting']]).all().all(),'C: every saved outcome and prediction finite')
 check((q.entry_date>q.date).all() and (q.exit_date>q.entry_date).all(),'C: target starts after prediction, ends after entry')
 check(all(c['fallback_for_insufficient_inner_data'] for c in fc if c['horizon_weeks']==52),'C: empty 52-week inner validation uses predeclared fixed fallback')
 joint=json.loads((O/'primary_tests_joint.json').read_text());check(len(joint)==32 and all(z['p_holm_all_strategies']>=z['p_one_sided'] for z in joint),'Primary tests: Holm correction over all twenty plus twelve strategies')
 out=dict(status='passed',checks=len(checks),unique_checks=checks,completed_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),qualification='Checks detect implementation/time-boundary errors; they cannot prove pristine point-in-time source vintages or eliminate historical research selection.',code_sha256={str(f.relative_to(R)):hashlib.sha256(f.read_bytes()).hexdigest() for f in sorted((R/'code').glob('*.py'))},input_sha256={str(f.relative_to(R)):hashlib.sha256(f.read_bytes()).hexdigest() for f in D.iterdir() if f.is_file() and f.name in ['academic_selected_long_returns.csv','academic_source_metadata.json','SignalDoc.csv','market_monthly_inputs.csv','trading_input_cache.joblib','forecast_horizon_panel.parquet','pca_feature_metadata.json','cohort.csv']},versions={n:importlib.metadata.version(n) for n in ['numpy','pandas','scipy','scikit-learn','joblib','pyarrow','matplotlib','threadpoolctl']})
 (O/'verification.json').write_text(json.dumps(out,indent=2,ensure_ascii=False));print('PASSED',len(checks),'integrity/time/replay checks.')

if __name__=='__main__':main()
