import pathlib,sys,json
R=pathlib.Path(__file__).resolve().parent;sys.path.insert(0,str(R/'deps'))
import numpy as np,pandas as pd
from scipy.stats import spearmanr
from portfolio_audit import rank_weights
from run_study import METHODS
O=R/'output'
rows=[]
for scope,h in [('primary',4),('primary',12),('extended',4)]:
 q=pd.read_parquet(O/f'predictions_{scope}_{h}.parquet').dropna(subset=[f'y_{h}']);methods=[m for m in METHODS if m in q]
 for method in methods:
  ics=[];top=[];flat=0
  for dt,g in q.groupby('date'):
   if g[method].max()-g[method].min()<1e-12:ics.append(0.);flat+=1
   else:ics.append(float(spearmanr(g[method],g[f'y_{h}']).statistic))
   # Same equal-selected-slot aggregation as the original descriptive metric,
   # now with neutral handling of score ties at the quintile boundary.
   selected=[];slots=[]
   for _,reg in g.groupby('region'):
    w=rank_weights(reg,method);selected.append(float(np.dot(w,reg[f'y_{h}'])));slots.append(max(1,int(np.ceil(.2*len(reg)))))
   top.append(float(np.average(selected,weights=slots)))
  rows.append(dict(scope=scope,horizon=h,model=method,stichtage=len(ics),constant_cross_section_days=flat,mean_rank_ic_zero_for_constant=float(np.mean(ics)),mean_regional_top20_excess_tie_neutral=float(np.mean(top))))
pd.DataFrame(rows).to_csv(O/'rank_diagnostics_tie_neutral.csv',index=False)
print('Tie-neutral rank diagnostics recorded; original primary MSE/AUC unchanged.')
