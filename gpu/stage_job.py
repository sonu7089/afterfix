"""Make a local copy with a new Kaggle ID. Does not upload or run anything."""
import argparse
import json
from pathlib import Path
import re
import runpy
import shutil

ROOT=Path(__file__).resolve().parent


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--job',required=True)
    parser.add_argument('--id',required=True,help='Your Kaggle username and a NEW slug, owner/slug')
    parser.add_argument('--output',required=True,help='New local staging directory')
    args=parser.parse_args()
    jobs=json.loads((ROOT/'JOBS.json').read_text())
    job=next((j for j in jobs if j['key']==args.job),None)
    if job is None:parser.error('Unknown job. Choose: '+', '.join(j['key'] for j in jobs))
    if not re.fullmatch(r'[A-Za-z0-9_-]+/[a-z0-9]+(?:-[a-z0-9]+)*',args.id):
        parser.error('Expected owner/new-lowercase-slug')
    old_ids={json.loads((ROOT/j['folder']/'kernel-metadata.recorded.json').read_text())['id'] for j in jobs}
    if args.id in old_ids:parser.error('Use a new notebook ID to preserve historical versions.')
    out=Path(args.output).resolve()
    if out.exists() or out.is_relative_to(ROOT) or ROOT.is_relative_to(out):
        parser.error('Use a new directory outside this supplement.')
    runpy.run_path(str(ROOT/'verify.py'))['verify']()
    recorded=ROOT/job['folder']
    metadata=json.loads((recorded/'kernel-metadata.recorded.json').read_text())
    metadata.update(id=args.id,title='AfterFix reproduction '+args.job,is_private=True)
    out.mkdir(parents=True)
    shutil.copyfile(recorded/job['code_file'],out/job['code_file'])
    (out/'kernel-metadata.json').write_text(json.dumps(metadata,indent=2)+'\n',encoding='utf-8')
    (out/'STAGING.json').write_text(json.dumps(dict(job=args.job,payload_unchanged=True,
        metadata_changes=['id','title','is_private'],uploaded=False,executed=False),indent=2)+'\n',encoding='utf-8')
    print('Prepared locally: '+str(out))
    print('No upload or run performed. Follow README before spending GPU quota.')


if __name__=='__main__':
    main()
