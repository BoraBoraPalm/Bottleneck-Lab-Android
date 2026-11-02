"""Additional stronger state baseline, declared AFTER primary scores were read.
No change/refit of the tested candidate model; secondary diagnostic, not a new
pre-registered success. Keeps company fixed differences in both models.
"""
import pathlib,json,joblib
import numpy as np,pandas as pd
from model import pipeline,split,multi_metrics,losses_multi,bootstrap_effect,holm,SEED
ROOT=pathlib.Path(__file__).resolve().parent;D=ROOT/'data';O=ROOT/'output'
a=pd.read_parquet(D/'news_features.parquet');a['state_str']=a.state.astype(str)
a=a[(a.state>=0)&(a.next_state>=0)&a.next_state.notna()].copy();a['target']=a.next_state.astype(int)
tr=a.loc[split(a,'train')];te=a.loc[split(a,'test')];y=te.target.to_numpy();baseline=pipeline([],['state_str','company_id','region']);baseline.fit(tr,tr.target)
p=baseline.predict_proba(te);model=joblib.load(O/'forecast_models.joblib')['state_forecast'];pn=model.predict_proba(te)
dif=losses_multi(y,p)-losses_multi(y,pn)
r={'status':'secondary diagnostic added after primary results; candidate unchanged','baseline':'regularized state+company+region model, no continuous news features','baseline_metrics':multi_metrics(y,p),'candidate_metrics':multi_metrics(y,pn),'comparison':bootstrap_effect(te.date,dif),'blocks':{str(b):bootstrap_effect(te.date,dif,block=b) for b in [4,13]}}
prim=json.loads((O/'results.json').read_text())['primary_tests'];r['holm_if_four_tests']=holm([t['p_one_sided'] for t in prim]+[r['comparison']['p_one_sided']])[-1]
joblib.dump(baseline,O/'state_strong_baseline.joblib');(O/'state_robustness.json').write_text(json.dumps(r,indent=2));print(json.dumps(r,indent=2))
rows=[]
for reg,q in te.groupby('region'):
 ix=np.flatnonzero(te.region.to_numpy()==reg);rows.append({'region':reg,'n':len(q),'firms':q.company_id.nunique(),'baseline_logloss':float(losses_multi(y[ix],p[ix]).mean()),'model_logloss':float(losses_multi(y[ix],pn[ix]).mean())})
pd.DataFrame(rows).to_csv(O/'state_by_region.csv',index=False)
# Conditional descriptive event rates with week-block intervals.
pred=pd.read_parquet(O/'test_predictions.parquet');rows=[]
for target in ['return','volume']:
 for s,q in pred[pred.target_kind==target].groupby('state'):
  e=bootstrap_effect(q.date,q.observed.to_numpy());counts=q.company_id.value_counts()
  rows.append(dict(target=target,state=int(s),n=len(q),firms=q.company_id.nunique(),event_rate=q.observed.mean(),ci_low=e['ci_low'],ci_high=e['ci_high'],largest_firm_share=float(counts.iloc[0]/len(q))))
pd.DataFrame(rows).to_csv(O/'conditional_rates.csv',index=False)
