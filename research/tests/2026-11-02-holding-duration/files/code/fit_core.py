import pathlib,sys
R=pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0,str(R.parent/'pca_forecast_study/deps'))
import numpy as np,pandas as pd
from sklearn.preprocessing import StandardScaler,OneHotEncoder
from sklearn.impute import SimpleImputer
from sklearn.decomposition import PCA
from sklearn.cross_decomposition import PLSRegression
from sklearn.linear_model import Ridge,ElasticNet
from sklearn.ensemble import HistGradientBoostingRegressor
SEED=20261102

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
