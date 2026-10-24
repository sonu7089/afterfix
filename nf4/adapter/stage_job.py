"""Stage an explicitly labeled NF4 replication locally. No upload or execution."""
import argparse
import ast
import hashlib
import json
from pathlib import Path
import re

ROOT=Path(__file__).resolve().parent

def sha(data):return hashlib.sha256(data).hexdigest()
def read(path):return json.loads(path.read_text(encoding='utf-8'))
def json_text(data):return json.dumps(data,indent=2)+'\n'

def verify_package():
    manifest=read(ROOT/'MANIFEST.json')
    for name,digest in manifest['files'].items():
        if sha((ROOT/name).read_bytes())!=digest:raise ValueError('Adapter package checksum mismatch: '+name)

def stage(job_key,new_id,checkpoint_path,output,dataset_source=None):
    verify_package();jobs=read(ROOT/'JOBS.json')
    job=next((j for j in jobs if j['key']==job_key),None)
    if job is None:raise ValueError('Unsupported job; v3 uses separate QAT weights')
    if not re.fullmatch(r'[A-Za-z0-9_-]+/[a-z0-9]+(?:-[a-z0-9]+)*',new_id):raise ValueError('Expected owner/new-slug')
    if new_id.casefold() in {value.casefold() for value in read(ROOT/'PROTECTED_NOTEBOOK_IDS.json')}:
        raise ValueError('Historical notebook ID cannot be reused')
    if not checkpoint_path or not (checkpoint_path.startswith('/') or re.match(r'^[A-Za-z]:[\\/]',checkpoint_path)):
        raise ValueError('Checkpoint path must be an absolute runtime path')
    out=Path(output).resolve()
    if out.exists() or out.is_relative_to(ROOT) or ROOT.is_relative_to(out):raise ValueError('Use a new directory outside the adapter package')
    if dataset_source and not re.fullmatch(r'[A-Za-z0-9_-]+/[a-z0-9]+(?:-[a-z0-9]+)*',dataset_source):
        raise ValueError('Dataset source must have owner/slug format')
    source=ROOT/'historical'/job_key/'pilot.py';source_bytes=source.read_bytes();text=source_bytes.decode('utf-8')
    tree=ast.parse(text)
    assignment=next(n for n in tree.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='FILES' for t in n.targets))
    original=ast.literal_eval(assignment.value);files=dict(original)
    original_manifest=json.loads(files['payload-manifest.json'])
    for name,digest in original_manifest['files'].items():
        if sha(files[name].encode())!=digest:raise ValueError('Historical embedded payload differs: '+name)
    files['afterfix/checkpoint_download.py']=(ROOT/'checkpoint_download.py').read_text(encoding='utf-8')
    files['afterfix/nf4_checkpoint.py']=(ROOT/'nf4_checkpoint.py').read_text(encoding='utf-8')
    files['afterfix/nf4-checkpoint-manifest.json']=(ROOT/'nf4-checkpoint-manifest.json').read_text(encoding='utf-8')
    files['afterfix/nf4-runtime.json']=json_text(dict(checkpoint_directory=checkpoint_path,adapter_version='afterfix-nf4-adapter-v1'))
    changes={n:dict(historical_sha256=sha(original[n].encode()) if n in original else None,
                    replication_sha256=sha(v.encode())) for n,v in files.items() if n not in original or v!=original[n]}
    record=dict(role='new replication, not a historical observation',adapter_version='afterfix-nf4-adapter-v1',
                job=job_key,notebook_id=new_id,historical_launcher_sha256=sha(source_bytes),
                historical_payload_manifest_sha256=sha(original['payload-manifest.json'].encode()),
                checkpoint_manifest_sha256=sha(files['afterfix/nf4-checkpoint-manifest.json'].encode()),
                replaced_payload_files=['afterfix/checkpoint_download.py'],payload_changes=changes,
                prompts_tasks_schedule_decoding_budgets_and_workers_unchanged=True,
                access_change='Local mounted checkpoint copied to local storage and fully SHA-256 checked; original private HTTP resolver bypassed',
                timing_caveat='Copy/hash time is included in the unchanged 180-second artifact-access timeout. This adapter has not been GPU-executed.',
                historical_scores_must_not_be_replaced=True,uploaded=False,executed=False)
    files['afterfix-results/replication.json']=json_text(record)
    # Preserve inherited seal as a historical reference, and explicitly distinguish the new payload.
    manifest=dict(original_manifest)
    manifest.update(reproduction_adapter='afterfix-nf4-adapter-v1',
                    seal_scope='seal_sha256 identifies the historical study, not this modified replication payload',
                    historical_payload_manifest_sha256=record['historical_payload_manifest_sha256'],
                    files={n:sha(v.encode()) for n,v in files.items() if n!='payload-manifest.json'})
    files['payload-manifest.json']=json_text(manifest)
    for name in original:
        if name not in ['afterfix/checkpoint_download.py','payload-manifest.json']:
            assert files[name]==original[name],name
    lines=text.splitlines(keepends=True)
    prefix=''.join(lines[:assignment.lineno-1])
    guard='\nif not ROOT.is_dir():\n raise RuntimeError("Kaggle runtime required; staging does not execute jobs locally")\nif (ROOT/"afterfix").exists() or (ROOT/"afterfix-results").exists():\n raise RuntimeError("Use a fresh session to preserve earlier files")\n'
    launcher=prefix+guard+'FILES='+repr(files)+'\n'+''.join(lines[assignment.end_lineno:])
    compile(launcher,'replication-pilot.py','exec')
    metadata=read(ROOT/'historical'/job_key/'kernel-metadata.recorded.json')
    metadata.update(id=new_id,title='AfterFix NF4 replication '+job_key,is_private=True)
    if dataset_source:metadata['dataset_sources']=[dataset_source]
    out.mkdir(parents=True,exist_ok=False)
    (out/'pilot.py').write_text(launcher,encoding='utf-8',newline='\n')
    (out/'kernel-metadata.json').write_text(json_text(metadata),encoding='utf-8')
    (out/'REPLICATION.json').write_text(json_text(record),encoding='utf-8')
    (out/'STAGED_FILES.json').write_text(json_text({p.name:sha(p.read_bytes()) for p in sorted(out.iterdir())}),encoding='utf-8')
    return record

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--job',required=True);p.add_argument('--id',required=True)
    p.add_argument('--checkpoint-path',required=True,help='Absolute path inside the future Kaggle runtime, ending in checkpoint')
    p.add_argument('--output',required=True);p.add_argument('--dataset-source',help='Optional future attached artifact owner/slug; never uploads')
    a=p.parse_args()
    try:record=stage(a.job,a.id,a.checkpoint_path,a.output,a.dataset_source)
    except (ValueError,FileNotFoundError) as e:p.error(str(e))
    print(json_text(dict(status='staged_locally',job=record['job'],output=str(Path(a.output).resolve()),uploaded=False,executed=False)))

if __name__=='__main__':main()
