import pathlib,sys,urllib.request,urllib.parse,json,hashlib,concurrent.futures,datetime,time
R=pathlib.Path(__file__).resolve().parents[1];D=R/'data';P=D/'prices';P.mkdir(exist_ok=True)
COHORT=R.parent/'pca_forecast_study/data/cohort.csv'
import csv
with COHORT.open() as f:cohort=list(csv.DictReader(f))
(D/'cohort.csv').write_bytes(COHORT.read_bytes())
FX=['EURUSD=X','HKD=X','KRW=X','JPY=X','TWD=X','CHF=X','GBPUSD=X','CNY=X','BRL=X','CAD=X','AUDUSD=X','ZAR=X','DKK=X']
T0=int(datetime.datetime(2010,1,1,tzinfo=datetime.timezone.utc).timestamp());T1=int(datetime.datetime(2026,11,3,tzinfo=datetime.timezone.utc).timestamp())
def one(t):
 p=P/(t+'.json');u=f'https://query1.finance.yahoo.com/v8/finance/chart/{urllib.parse.quote(t)}?period1={T0}&period2={T1}&interval=1d&events=div%2Csplits'
 try:
  b=p.read_bytes() if p.exists() else urllib.request.urlopen(urllib.request.Request(u,headers={'User-Agent':'Mozilla/5.0 (compatible; HoldingPeriodResearch/1.0)'}),timeout=35).read();j=json.loads(b);a=j['chart']['result'][0];assert len(a['timestamp'])>250;p.write_bytes(b)
  return dict(ticker=t,ok=True,observations=len(a['timestamp']),url=u,bytes=len(b),sha256=hashlib.sha256(b).hexdigest(),retrieved_utc=datetime.datetime.now(datetime.timezone.utc).isoformat())
 except Exception as e:return dict(ticker=t,ok=False,error=str(e),url=u)
if __name__=='__main__':
 ts=list(dict.fromkeys([x['ticker'] for x in cohort]+['ACWI','SPY']+FX));a=[]
 with concurrent.futures.ThreadPoolExecutor(6) as ex:
  for i,r in enumerate(ex.map(one,ts)):
   a.append(r)
   if (i+1)%20==0:print('Price files',i+1,'/',len(ts),'failed',sum(not z['ok'] for z in a),flush=True)
 (D/'price_manifest.json').write_text(json.dumps(a,indent=2));print('Price download done; failed:',[x for x in a if not x['ok']],flush=True)
