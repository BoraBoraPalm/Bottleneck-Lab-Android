import pathlib,sys,json
R=pathlib.Path(__file__).resolve().parents[1];sys.path.insert(0,str(R.parent/'pca_forecast_study/deps'))
import numpy as np,pandas as pd
O=R/'output'
a=json.loads((O/'academic_tests_uncorrected.json').read_text());b=json.loads((O/'trading_tests_uncorrected.json').read_text());rows=[]
for family,items in [('academic_refresh',a),('trading_interval',b)]:
 for x in items:rows.append(dict(module=family,**x))
order=np.argsort([x['p_one_sided'] for x in rows]);adj=np.zeros(len(rows));last=0
for i,j in enumerate(order):last=max(last,min(1,(len(rows)-i)*rows[j]['p_one_sided']));adj[j]=last
for x,p in zip(rows,adj):x['p_holm_all_strategies']=float(p)
(O/'primary_tests_joint.json').write_text(json.dumps(rows,indent=2,ensure_ascii=False))
A=pd.read_csv(O/'academic_metrics.csv');B=pd.read_csv(O/'trading_metrics.csv');C=pd.read_csv(O/'forecast_horizon_metrics.csv');summ=[]
for name,g in A.groupby('strategy'):
 selected=g[g.policy=='past_selected'].iloc[0];ref=g[g.policy=='original'].iloc[0];best=g[g.policy.isin(['1','3','6','12'])].sort_values('cagr').iloc[-1];e=next(x for x in rows if x['module']=='academic_refresh' and x['strategy']==name)
 summ.append(dict(module='academic_refresh',strategy=name,selected_cagr=selected.cagr,reference_cagr=ref.cagr,market_cagr=selected.benchmark_cagr,improvement_cagr=selected.cagr-ref.cagr,hindsight_max_cagr=best.cagr,hindsight_max_interval=best.policy,p_holm=e['p_holm_all_strategies']))
for name,g in B.groupby('strategy'):
 selected=g[g.policy=='past_selected'].iloc[0];ref=g[g.policy=='20'].iloc[0];best=g[g.policy!='past_selected'].sort_values('cagr').iloc[-1];e=next(x for x in rows if x['module']=='trading_interval' and x['strategy']==name)
 summ.append(dict(module='trading_interval',strategy=name,selected_cagr=selected.cagr,reference_cagr=ref.cagr,market_cagr=selected.acwi_cagr,improvement_cagr=selected.cagr-ref.cagr,hindsight_max_cagr=best.cagr,hindsight_max_interval=best.policy,p_holm=e['p_holm_all_strategies'],realized_closed_trade_median=selected.median_actual_hold_sessions,realized_closed_trade_mean=selected.mean_actual_hold_sessions))
pd.DataFrame(summ).to_csv(O/'strategy_summary.csv',index=False)
print('ACADEMIC: selected net CAGR / original / market / selected improvement p(Holm)')
for x in summ:
 if x['module']=='academic_refresh' and x['strategy'] in ['Momentum','Value','Gross-Profit-Quality','Gewinnüberraschung','Analystenrevisionen','Konservatives Bilanzwachstum']:print(x['strategy'],*[round(x[k]*100,2) for k in ['selected_cagr','reference_cagr','market_cagr']],round(x['p_holm'],4))
print('TRADING: selected / 20 / market / median hold / p(Holm)')
for x in summ:
 if x['module']=='trading_interval':print(x['strategy'],*[round(x[k]*100,2) for k in ['selected_cagr','reference_cagr','market_cagr']],round(x['realized_closed_trade_median'],1),round(x['p_holm'],4))
print('FORECAST: R2 percentage points by horizon')
print(C.pivot(index='horizon_weeks',columns='method',values='r2_zero').mul(100).round(2).to_string())
