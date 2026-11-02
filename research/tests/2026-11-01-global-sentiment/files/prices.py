import urllib.request,json,pathlib,datetime,concurrent.futures,time,hashlib
from cohort import COHORT
ROOT=pathlib.Path(__file__).resolve().parent;OUT=ROOT/'data'/'prices';OUT.mkdir(exist_ok=True)
T0=int(datetime.datetime(2018,1,1,tzinfo=datetime.timezone.utc).timestamp());T1=int(datetime.datetime(2026,1,15,tzinfo=datetime.timezone.utc).timestamp())
FX={'HKD':('HKD=X',False),'KRW':('KRW=X',False),'JPY':('JPY=X',False),'TWD':('TWD=X',False),'CHF':('CHF=X',False),'EUR':('EURUSD=X',True),'GBP':('GBPUSD=X',True),'GBp':('GBPUSD=X',True),'CNY':('CNY=X',False),'BRL':('BRL=X',False),'CAD':('CAD=X',False),'AUD':('AUDUSD=X',True),'ZAR':('ZAR=X',False),'DKK':('DKK=X',False)}
FX['ZAc']=FX['ZAR']
def one(ticker):
 p=OUT/(ticker+'.json');u=f'https://query1.finance.yahoo.com/v8/finance/chart/{ticker}?period1={T0}&period2={T1}&interval=1d'
 try:
  b=p.read_bytes() if p.exists() else urllib.request.urlopen(urllib.request.Request(u,headers={'User-Agent':'Mozilla/5.0'}),timeout=35).read()
  d=json.loads(b);r=d['chart']['result'][0];n=len(r['timestamp']);p.write_bytes(b)
  return dict(ticker=ticker,ok=True,n=n,currency=r['meta'].get('currency'),first=r['timestamp'][0],last=r['timestamp'][-1],sha256=hashlib.sha256(b).hexdigest(),url=u,retrieved_utc=datetime.datetime.now(datetime.timezone.utc).isoformat())
 except Exception as e:return dict(ticker=ticker,ok=False,error=str(e))
def main():
 ts=[d['ticker'] for d in COHORT]+[v[0] for v in FX.values()];ts=list(dict.fromkeys(ts))
 with concurrent.futures.ThreadPoolExecutor(6) as ex:
  result=[]
  for n,r in enumerate(ex.map(one,ts)):
   result.append(r)
   if (n+1)%20==0:print(n+1,'/',len(ts),'errors',sum(not x['ok'] for x in result),flush=True)
 (ROOT/'data'/'prices_manifest.json').write_text(json.dumps(result,indent=2))
 print('DONE',len(result),'errors',[r for r in result if not r['ok']],flush=True)
if __name__=='__main__':main()
