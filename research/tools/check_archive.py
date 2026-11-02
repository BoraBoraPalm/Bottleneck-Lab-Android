#!/usr/bin/env python3
"""Validate archived metadata, references and retained source bytes; no backtest."""
from __future__ import annotations
import hashlib,json,pathlib,sys
ROOT=pathlib.Path(__file__).resolve().parents[2]
def main():
 index=json.loads((ROOT/'research/index.json').read_text());ids=[s['id'] for s in index['tests']];assert len(ids)==len(set(ids)), 'Duplicate study IDs'
 files=0
 for s in index['tests']:
  folder=ROOT/'research/tests'/s['id'];meta=json.loads((folder/'test.json').read_text());assert meta['id']==s['id'];assert (folder/'README.md').is_file()
  for key in ['holding','prediction','rebalance','holding_period_search_performed','source_artifact','limits','reproduction_status','time_splits','costs','benchmark']:assert key in meta,(s['id'],key)
  artifact=meta['source_artifact'];assert len(artifact['sha256'])==64;assert artifact['url'].startswith('https://chatgpt.com/library?file_id=')
  assert (folder/meta['entry_report']).is_file(),(s['id'],'Missing entry report')
  for member in json.loads((folder/'ARTIFACT_MEMBERS.json').read_text()):
   if not member['in_repository']:continue
   path=ROOT/member['repository_path'];assert path.resolve().is_relative_to(ROOT.resolve());b=path.read_bytes();assert len(b)==member['bytes'];assert hashlib.sha256(b).hexdigest()==member['sha256'],path;files+=1
 assert (ROOT/'research/HOLDING_PERIODS.md').is_file();assert (ROOT/'research/templates/TEST.md').is_file();print(f'Archive valid: {len(ids)} studies; {files} retained original files verified; no research rerun.')
if __name__=='__main__':main()
