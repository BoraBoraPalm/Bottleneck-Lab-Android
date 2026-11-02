#!/usr/bin/env python3
"""Restore an existing original artifact, without downloading data or fitting models."""
from __future__ import annotations
import argparse,hashlib,json,pathlib,stat,zipfile
ROOT=pathlib.Path(__file__).resolve().parents[2]
def main():
 ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('study_id');ap.add_argument('bundle',type=pathlib.Path);ap.add_argument('--destination',type=pathlib.Path,default=ROOT/'.research_cache');args=ap.parse_args()
 index=json.loads((ROOT/'research/index.json').read_text());valid={s['id']:s for s in index['tests']}
 if args.study_id not in valid:ap.error('Unknown study ID; see research/index.json')
 meta=json.loads((ROOT/'research/tests'/args.study_id/'test.json').read_text());data=args.bundle.read_bytes();actual=hashlib.sha256(data).hexdigest()
 if actual!=meta['source_artifact']['sha256']:ap.error('SHA-256 differs from the exact archived original artifact; no files restored')
 dest=(args.destination/args.study_id).resolve();dest.mkdir(parents=True,exist_ok=True)
 with zipfile.ZipFile(args.bundle) as z:
  assert z.testzip() is None, 'Corrupt ZIP'
  for info in z.infolist():
   p=pathlib.PurePosixPath(info.filename)
   if p.is_absolute() or '..' in p.parts or stat.S_ISLNK(info.external_attr>>16):ap.error('Unsafe archive member; no path traversal or symbolic links allowed')
   target=(dest/info.filename).resolve()
   if not target.is_relative_to(dest):ap.error('Unsafe archive path')
  z.extractall(dest);count=len([i for i in z.infolist() if not i.is_dir()])
 print(f'Verified original bundle; restored {count} cached files to {dest}. No downloads or evaluations performed.')
 if meta['source_artifact'].get('archive_root'):print('Original project root:',dest/meta['source_artifact']['archive_root'])
if __name__=='__main__':main()
