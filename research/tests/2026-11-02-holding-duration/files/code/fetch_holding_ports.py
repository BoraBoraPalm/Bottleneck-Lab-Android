import pathlib,urllib.request,urllib.parse,json,hashlib,concurrent.futures,sys
R=pathlib.Path(__file__).resolve().parents[1];D=R/'data';D.mkdir(exist_ok=True)
PIN='ad1dfba5a6d80c4ce53ce6b8127f5a949dda1e40'
def one(h):
 name=f'PredictorAltPorts_HoldPer_{h}.parquet';rel='Portfolios/Full Sets Alt/'+name;url='https://huggingface.co/datasets/OpenSourceAP/CrossSection/resolve/'+PIN+'/'+urllib.parse.quote(rel,safe='/');p=D/name
 b=p.read_bytes() if p.exists() else urllib.request.urlopen(urllib.request.Request(url,headers={'User-Agent':'Historical-Holding-Period-Research/1.0'}),timeout=60).read();p.write_bytes(b);return dict(holding_months=h,file=name,url=url,bytes=len(b),sha256=hashlib.sha256(b).hexdigest(),source_revision=PIN)
if __name__=='__main__':
 with concurrent.futures.ThreadPoolExecutor(4) as ex:r=list(ex.map(one,[1,3,6,12]))
 (D/'holding_port_download_manifest.json').write_text(json.dumps(r,indent=2));print('Downloaded native holding-period variants:',[(x['holding_months'],x['bytes']) for x in r],flush=True)
 sys.path.insert(0,str(R.parent/'pca_forecast_study/deps'))
 import pandas as pd
 for x in r:
  d=pd.read_parquet(D/x['file']);print(x['holding_months'],'shape',d.shape,'columns',d.columns.tolist(),'dtypes',dict(d.dtypes.astype(str)),flush=True)
  for c in ['port','signalname','date']:
   if c in d:
    if c=='date':print('date coverage',str(d[c].min()),str(d[c].max()),flush=True)
    elif c=='port':print('port identifiers',d[c].drop_duplicates().tolist(),flush=True)
    else:print('number of signals',d[c].nunique(),flush=True)
