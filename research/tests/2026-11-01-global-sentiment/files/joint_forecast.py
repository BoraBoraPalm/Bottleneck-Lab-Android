"""Post-primary diagnostic: evaluate ALL currently measurable firm-weeks,
including those with no measurable state next week. Explicit availability head
prevents selecting the deployable sample using future coverage. No return
models or conditional state candidate are retuned.
"""
import pathlib,json,joblib
import numpy as np,pandas as pd
from model import pipeline,split,NEWSFEATS,losses_multi,bootstrap_effect,binary_metrics,holm
R=pathlib.Path(__file__).resolve().parent;D=R/'data';O=R/'output'
a=pd.read_parquet(D/'news_features.parquet');a['state_str']=a.state.astype(str)
a=a[(a.state>=0)&a.next_state.notna()].copy();a['available_next']=(a.next_state>=0).astype(int)
tr=a.loc[split(a,'train')];te=a.loc[split(a,'test')];baseline=pipeline([],['state_str','company_id','region']);candidate=pipeline(NEWSFEATS,['state_str','company_id','region'])
baseline.fit(tr,tr.available_next);candidate.fit(tr,tr.available_next)
pb=baseline.predict_proba(te)[:,1];pn=candidate.predict_proba(te)[:,1]
sb=joblib.load(O/'state_strong_baseline.joblib').predict_proba(te);sn=joblib.load(O/'forecast_models.joblib')['state_forecast'].predict_proba(te)
# Index 0 = no measurable next-week state; 1..6 = the six news categories.
jb=np.column_stack([1-pb,pb[:,None]*sb]);jn=np.column_stack([1-pn,pn[:,None]*sn]);y=te.next_state.to_numpy(int)+1
lb=losses_multi(y,jb);ln=losses_multi(y,jn);e=bootstrap_effect(te.date,lb-ln)
r={'status':'post-primary diagnostic; no future-coverage sample filter; conditional models unchanged','n':len(te),'firms':te.company_id.nunique(),'next_week_measurable_fraction':te.available_next.mean(),'baseline_logloss':float(lb.mean()),'candidate_logloss':float(ln.mean()),'baseline_accuracy':float(np.mean(jb.argmax(axis=1)==y)),'candidate_accuracy':float(np.mean(jn.argmax(axis=1)==y)),'comparison':e,'availability_baseline':binary_metrics(te.available_next.to_numpy(),pb),'availability_candidate':binary_metrics(te.available_next.to_numpy(),pn),'blocks':{str(b):bootstrap_effect(te.date,lb-ln,block=b) for b in [4,13]}}
primary=json.loads((O/'results.json').read_text())['primary_tests'];strong=json.loads((O/'state_robustness.json').read_text())['comparison'];r['holm_if_five_tests']=holm([x['p_one_sided'] for x in primary]+[strong['p_one_sided'],e['p_one_sided']])[-1]
joblib.dump(dict(availability_baseline=baseline,availability_candidate=candidate),O/'availability_models.joblib')
q=te[['date','company_id','region','state','next_state']].copy();q['availability_probability']=pn;q['loss_baseline']=lb;q['loss_model']=ln
for k in range(7):q[f'p_{k}']=jn[:,k]
assert np.allclose(jn.sum(axis=1),1)
q.to_parquet(O/'joint_state_predictions.parquet',index=False);(O/'joint_state_diagnostic.json').write_text(json.dumps(r,indent=2));print(json.dumps(r,indent=2))
