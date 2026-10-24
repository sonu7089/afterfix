"""Verify or materialize the pinned NF4 release using only the Python standard library."""
import argparse
import hashlib
import json
from pathlib import Path
import time

EXPECTED_MANIFEST_SHA256='78cb8b4cc2bbfa3efe4f5ac4ff04a384e7d11d6c480b0260018f5fbdaaf3953e'
MANIFEST_NAME='nf4-checkpoint-manifest.json'
SOURCE='google/gemma-4/transformers/gemma-4-12b-it/2'

def digest(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for b in iter(lambda:f.read(8*1024*1024),b''):h.update(b)
    return h.hexdigest()

def load_manifest():
    path=Path(__file__).with_name(MANIFEST_NAME)
    if digest(path)!=EXPECTED_MANIFEST_SHA256:raise ValueError('Checkpoint manifest checksum mismatch')
    data=json.loads(path.read_text(encoding='utf-8'))
    if data['source_model']!=SOURCE or data['source_notebook_version']!=1:
        raise ValueError('Incorrect historical model or checkpoint version')
    for name,record in data['files'].items():
        if Path(name).name!=name or '/' in name or '\\' in name or name in ['.','..']:
            raise ValueError('Unsafe manifest filename')
        if not isinstance(record['bytes'],int) or record['bytes']<=0:raise ValueError('Invalid file size')
        if len(record['sha256'])!=64:raise ValueError('Invalid SHA-256 digest')
    return data

def check_files(directory,records,copy_to=None):
    """Hash every file, optionally copying it once to a NEW local directory."""
    directory=Path(directory).resolve(strict=True)
    if not directory.is_dir():raise ValueError('Checkpoint must be a directory')
    dest=Path(copy_to).resolve() if copy_to is not None else None
    if dest is not None:
        if dest.exists() or dest.is_relative_to(directory) or directory.is_relative_to(dest):
            raise ValueError('Copy destination must be new and outside the source directory')
        dest.mkdir(parents=True,exist_ok=False)
    observed={}
    for name,record in records.items():
        if Path(name).name!=name or '/' in name or '\\' in name or name in ['.','..']:
            raise ValueError('Unsafe checkpoint filename')
        source=directory/name
        if source.is_symlink() or not source.is_file() or source.resolve().parent!=directory:
            raise ValueError('Missing, symlinked or external file: '+name)
        if source.stat().st_size!=record['bytes']:raise ValueError('Checkpoint size mismatch: '+name)
        h=hashlib.sha256();count=0
        tmp=(dest/(name+'.partial')) if dest else None
        out=tmp.open('xb') if tmp else None
        try:
            with source.open('rb') as f:
                for b in iter(lambda:f.read(8*1024*1024),b''):
                    count+=len(b);h.update(b)
                    if out:out.write(b)
        finally:
            if out:out.close()
        if count!=record['bytes'] or h.hexdigest()!=record['sha256']:
            raise ValueError('Checkpoint checksum mismatch: '+name)
        if tmp:tmp.replace(dest/name)
        observed[name]=dict(bytes=count,sha256=h.hexdigest())
    return observed

def validate_metadata(directory,manifest):
    directory=Path(directory)
    p=json.loads((directory/'AFTERFIX_PROVENANCE.json').read_text())
    if p.get('status')!='completed' or p.get('source')!=SOURCE:raise ValueError('Invalid original provenance')
    q=json.loads((directory/'config.json').read_text()).get('quantization_config',{})
    required=dict(quant_method='bitsandbytes',load_in_4bit=True,bnb_4bit_quant_type='nf4',
                  bnb_4bit_use_double_quant=True,bnb_4bit_compute_dtype='float16')
    if any(q.get(k)!=v for k,v in required.items()):raise ValueError('Invalid quantization settings')
    weights={x['name']:x['bytes'] for x in p['weight_files']}
    if len(weights)!=13:raise ValueError('Expected 13 NF4 shards')
    expected={n for n in manifest['files'] if n.endswith('.safetensors')}
    if set(weights)!=expected:raise ValueError('Provenance and release shard sets differ')
    if {p.name for p in directory.glob('*.safetensors')}!=expected:raise ValueError('Unexpected shard files')
    if any(manifest['files'][n]['bytes']!=size for n,size in weights.items()):raise ValueError('Provenance sizes differ')
    index=json.loads((directory/'model.safetensors.index.json').read_text())
    if set(index['weight_map'].values())!=expected:raise ValueError('Shard index differs')
    return dict(source=SOURCE,preparation_kernel='nitishsongara/afterfix-checkpoint-cpu/1',
                quantization_backend=p['quantization_backend'],weight_files=13,weight_bytes=sum(weights.values()),
                config_sha256=manifest['files']['config.json']['sha256'])

def verify_checkpoint(directory,copy_to=None):
    start=time.monotonic();manifest=load_manifest()
    observed=check_files(directory,manifest['files'],copy_to)
    dest=Path(copy_to) if copy_to else Path(directory)
    metadata=validate_metadata(dest,manifest)
    return dict(status='passed',artifact_version=manifest['artifact_version'],files=observed,
                checkpoint_manifest_sha256=EXPECTED_MANIFEST_SHA256,validation=metadata,
                total_bytes=sum(x['bytes'] for x in observed.values()),seconds=time.monotonic()-start,
                destination=str(dest.resolve()),model_loaded=False,gpu_used=False)

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--checkpoint',required=True)
    p.add_argument('--copy-to');p.add_argument('--report');a=p.parse_args()
    if a.report and Path(a.report).exists():p.error('Report already exists; use a new path')
    report=verify_checkpoint(a.checkpoint,a.copy_to)
    if a.report:
        path=Path(a.report);path.parent.mkdir(parents=True,exist_ok=True)
        path.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:v for k,v in report.items() if k!='files'},indent=2))

if __name__=='__main__':main()
