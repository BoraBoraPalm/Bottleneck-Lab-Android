from __future__ import annotations
import pathlib,datetime,urllib.request,json,hashlib,zipfile,io,concurrent.futures,time,collections
import pandas as pd
from cohort import COHORT,ALIASES,norm
ROOT=pathlib.Path(__file__).resolve().parent
DATA=ROOT/'data';OUT=DATA/'snapshots';OUT.mkdir(exist_ok=True)
YEARS=range(2019,2026)
DATES=pd.date_range('2019-01-02','2025-12-31',freq='W-WED')
HEADERS={'User-Agent':'GlobalSentimentResearch/1.0 (public historical data pilot)'}
def one(job):
 dt,translated=job;stamp=dt.strftime('%Y%m%d120000');kind='translation.' if translated else ''
 name=f'{stamp}.{kind}gkg.csv.zip';base=OUT/name.replace('.csv.zip','')
 if base.with_suffix(base.suffix+'.json').exists():return 'cached',0,0
 url='https://data.gdeltproject.org/gdeltv2/'+name
 started=time.time();meta=dict(file=name,url=url,date=str(dt.date()),translated=translated,retrieved_utc=datetime.datetime.now(datetime.timezone.utc).isoformat())
 try:
  local=DATA/name
  b=local.read_bytes() if local.exists() else urllib.request.urlopen(urllib.request.Request(url,headers=HEADERS),timeout=50).read()
  meta.update(bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
  rows=[];total=0;seen=set()
  with zipfile.ZipFile(io.BytesIO(b)) as z:
   with z.open(z.namelist()[0]) as stream:
    for line in io.TextIOWrapper(stream,encoding='utf-8',errors='replace'):
     total+=1;x=line.rstrip('\r\n').split('\t')
     if len(x)<26:continue
     ids={ALIASES.get(norm(org)) for org in x[13].split(';')};ids.discard(None)
     if not ids:continue
     try:tone=list(map(float,x[15].split(',')))
     except ValueError:continue
     if len(tone)<7 or tone[6]<20:continue
     language='eng'
     if translated:
      for part in x[25].split(';'):
       if part.startswith('srclc:'):language=part[6:]
      if language=='eng':language='translated_unknown'
     for cid in ids:
      key=(cid,x[4]);
      if key in seen:continue
      seen.add(key)
      rows.append(dict(date=str(dt.date()),company_id=cid,gkg_id=x[0],archive_time=x[1],source=x[3],url=x[4],tone=tone[0],positive=tone[1],negative=tone[2],polarity=tone[3],word_count=tone[6],language=language,translated=translated,n_cohort_companies=len(ids),orgs=x[13]))
  if rows:pd.DataFrame(rows).to_parquet(str(base)+'.parquet',index=False)
  meta.update(ok=True,total_rows=total,matched_rows=len(rows),seconds=round(time.time()-started,2))
 except Exception as e:meta.update(ok=False,error=type(e).__name__+': '+str(e),seconds=round(time.time()-started,2))
 pathlib.Path(str(base)+'.json').write_text(json.dumps(meta,indent=2))
 return meta.get('ok'),meta.get('bytes',0),meta.get('matched_rows',0)
def main():
 pd.DataFrame(COHORT).to_csv(DATA/'cohort.csv',index=False)
 jobs=[(dt,t) for dt in DATES for t in (False,True)]
 n=0;size=0;rows=0;start=time.time()
 with concurrent.futures.ThreadPoolExecutor(max_workers=12) as ex:
  for r in ex.map(one,jobs):
   n+=1;size+=r[1];rows+=r[2]
   if n%20==0:print(json.dumps(dict(done=n,of=len(jobs),MB=round(size/1e6),matches=rows,elapsed_s=round(time.time()-start))),flush=True)
 files=list(OUT.glob('*.parquet'))
 if files:
  df=pd.concat([pd.read_parquet(f) for f in files],ignore_index=True)
  df=df.drop_duplicates(['date','company_id','url'])
  df.to_parquet(DATA/'news_sample.parquet',index=False)
 manifests=[json.loads(f.read_text()) for f in sorted(OUT.glob('*.json'))]
 (DATA/'archive_manifest.json').write_text(json.dumps(manifests,indent=2))
 print('DONE',len(files),'archives',len(df),'deduplicated firm-articles',flush=True)
if __name__=='__main__':main()
