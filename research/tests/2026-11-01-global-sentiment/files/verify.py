"""Leakage / data-integrity audits for this research run (not predictive validation)."""
import pathlib,json,hashlib
import numpy as np,pandas as pd
ROOT=pathlib.Path(__file__).resolve().parent;D=ROOT/'data';O=ROOT/'output'
def main():
 checks={}
 lock=json.loads((O/'protocol_lock.json').read_text());checks['protocol_matches_pre_test_lock']=all(hashlib.sha256((ROOT/k).read_bytes()).hexdigest()==v for k,v in lock['sha256'].items())
 p=pd.read_parquet(D/'price_panel.parquet');n=pd.read_parquet(D/'news_features.parquet');raw=pd.read_parquet(D/'news_sample.parquet');pred=pd.read_parquet(O/'test_predictions.parquet')
 checks['features_before_news_cutoff']=bool((p.feature_price_date<p.date).all())
 valid=p.dropna(subset=['entry_date','exit_date','forward_return'])
 checks['entry_after_news_plus_4d']=bool((valid.entry_date>=valid.date+pd.Timedelta(days=5)).all())
 checks['exit_strictly_after_entry']=bool((valid.exit_date>valid.entry_date).all())
 checks['one_price_observation_per_firm_week']=not p.duplicated(['date','company_id']).any()
 checks['one_news_observation_per_firm_week']=not n.duplicated(['date','company_id']).any()
 checks['one_raw_url_per_firm_week']=not raw.duplicated(['date','company_id','url']).any()
 checks['test_only_after_2023_01_18']=bool((pred.date>=pd.Timestamp('2023-01-18')).all())
 checks['unknown_not_a_neutral_cluster']=bool((n.loc[n.coverage==0,'state']==-1).all())
 checks['six_data_categories']=set(n.loc[n.coverage==1,'state'])==set(range(6))
 checks['state_forecast_probability_sum']=bool(np.allclose(pred.loc[pred.target_kind=='state_forecast',[f'p_state_{k}' for k in range(6)]].sum(axis=1),1))
 a=n.sort_values(['company_id','date']);expected=a.groupby('company_id').state.shift(-1);checks['state_target_exactly_next_fresh_week']=bool((a.next_state.fillna(-999).to_numpy()==expected.fillna(-999).to_numpy()).all())
 # Holidays and corporate actions can produce genuine outliers; report rather than clip them.
 diagnostics=dict(max_abs_forward_return=float(valid.forward_return.abs().max()),forward_returns_abs_over_50pct=int((valid.forward_return.abs()>.5).sum()),return_available_companies=int(valid.company_id.nunique()),firms_with_test_targets=int(pred.company_id.nunique()),unknown_test_states=int(((pred.target_kind=='return')&(pred.state<0)).sum()))
 result=dict(checks={k:bool(v) for k,v in checks.items()},diagnostics=diagnostics,all_pass=all(checks.values()))
 (O/'integrity_audit.json').write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2));assert result['all_pass']
if __name__=='__main__':main()
