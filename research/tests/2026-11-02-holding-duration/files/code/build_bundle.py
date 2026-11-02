"""Package exact used inputs/results; original oversized source hashes retained."""
from pathlib import Path
import hashlib,json,zipfile
R=Path(__file__).resolve().parents[1]
OUT=R.parent/'Haltedauer_Strategien_Gesamtstudie_2026.zip'
inputs=['academic_selected_long_returns.csv','academic_source_metadata.json','SignalDoc.csv','market_monthly_inputs.csv','trading_input_cache.joblib','forecast_horizon_panel.parquet','pca_feature_metadata.json','cohort.csv','price_manifest.json','holding_port_download_manifest.json']
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 all_data=[dict(path=str(p.relative_to(R)),bytes=p.stat().st_size,sha256=digest(p),included_in_bundle=p.name in inputs,role='frozen used input' if p.name in inputs else 'original/intermediate download; compact exact used inputs bundled instead') for p in sorted((R/'data').rglob('*')) if p.is_file()]
 (R/'DATA_MANIFEST.json').write_text(json.dumps(dict(scope='All local source/input data; only exact compact calculation inputs and provenance manifests are bundled. No raw source is required for cached reproduction.',files=all_data),indent=2))
 files=[p for p in R.rglob('*') if p.is_file() and '__pycache__' not in p.parts and (not p.is_relative_to(R/'data') or p.name in inputs) and p.name!='BUNDLE_MEMBERS.json']
 members=[dict(path=str(p.relative_to(R)),bytes=p.stat().st_size,sha256=digest(p)) for p in sorted(files)]
 (R/'BUNDLE_MEMBERS.json').write_text(json.dumps(dict(scope='All ZIP members except this self-referential manifest. The repository ARTIFACT_MEMBERS.json also hashes this member.',members=members),indent=2))
 files.append(R/'BUNDLE_MEMBERS.json')
 with zipfile.ZipFile(OUT,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
  for p in sorted(files):z.write(p,'Haltedauer_Strategien_2026/'+str(p.relative_to(R)))
 result=dict(path=str(OUT),bytes=OUT.stat().st_size,sha256=digest(OUT),members=len(files));(R.parent/'holding_bundle_identity.json').write_text(json.dumps(result,indent=2));print(json.dumps(result))
if __name__=='__main__':main()
