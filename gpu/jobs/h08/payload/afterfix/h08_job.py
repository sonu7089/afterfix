"""Sealed public-only batch controller. Grading happens locally after download."""
import hashlib
import json
import os
import pathlib
import subprocess
import sys
import time
import traceback
from .runtime import wait_worker

DEPENDENCIES=['transformers==5.20.2','accelerate==1.15.0','bitsandbytes==0.50.2','kagglehub==1.0.2']


def verify_payload(workspace,payload):
    for name,expected in payload['files'].items():
        if hashlib.sha256((workspace/name).read_bytes()).hexdigest()!=expected:raise ValueError('Sealed file mismatch: '+name)


def main():
    workspace=pathlib.Path('/kaggle/working');root=workspace/'afterfix-results';root.mkdir(exist_ok=True)
    config=json.loads((root/'run-config.json').read_text());payload=json.loads((workspace/'payload-manifest.json').read_text())
    start=time.monotonic();summary={'status':'validating','dataset':'afterfix-heldout-v1',
        'seal_sha256':payload['seal_sha256'],'batch':config['batch'],'planned_attempts':3,'harness_version':'afterfix-harness-v2',
        'model_loading_timeout_seconds':300,'worker_timeout_seconds':4950,'notebook_timeout_seconds':5310,
        'checkpoint_download_timeout_seconds':180,'grading':'local private grader after download'}
    def save():
        summary['controller_elapsed_seconds']=time.monotonic()-start
        tmp=root/'summary.tmp';tmp.write_text(json.dumps(summary,indent=2));tmp.replace(root/'summary.json')
    save()
    try:
        verify_payload(workspace,payload)
        summary['nvidia_smi']=subprocess.run(['nvidia-smi'],capture_output=True,text=True,timeout=15).stdout
        with (root/'dependency-install.log').open('w') as log:
            subprocess.run([sys.executable,'-m','pip','install','--quiet','--disable-pip-version-check',*DEPENDENCIES],stdout=log,stderr=subprocess.STDOUT,timeout=90,check=True)
        summary['status']='downloading_checkpoint';save()
        with (root/'checkpoint-download.log').open('w') as log:
            subprocess.run([sys.executable,'-u','-m','afterfix.checkpoint_download',str(root/'checkpoint-download.json')],stdout=log,stderr=subprocess.STDOUT,timeout=180,check=True,cwd=workspace)
        download=json.loads((root/'checkpoint-download.json').read_text());model=pathlib.Path(download['destination'])
        if download['status']!='completed':raise ValueError('Checkpoint download incomplete')
        for name,sha in config['tokenizer_files'].items():
            if hashlib.sha256((model/name).read_bytes()).hexdigest()!=sha:raise ValueError('Pinned tokenizer/provenance changed: '+name)
        summary['checkpoint_download_seconds']=download['seconds'];summary['status']='agent_running';save()
        env=dict(os.environ,AFTERFIX_PROTOCOL='v2',AFTERFIX_METHODS=json.dumps(['ordinary','checklist','provenance']))
        with (root/'agent-worker.log').open('w') as log:
            with subprocess.Popen([sys.executable,'-u','-m','afterfix.h08_worker',str(root),str(model)],stdout=log,stderr=subprocess.STDOUT,cwd=workspace,env=env) as proc:
                remaining=5310-(time.monotonic()-start)-30
                summary.update(wait_worker(proc,root/'agent-results.json',loading_timeout=300,total_timeout=min(4950,max(1,remaining))))
        path=root/'agent-results.json'
        if path.exists():
            agent=json.loads(path.read_text());summary['attempted_runs']=len(agent['runs']);summary['agent_status']=agent['status']
            summary['status']='completed' if agent['status']=='completed' and not summary.get('worker_timed_out') else 'partial'
        else:summary['status']='failed_no_agent_results'
    except Exception:summary['status']='infrastructure_error';summary['error']=traceback.format_exc()
    finally:save();print(json.dumps(summary,indent=2),flush=True)


if __name__=='__main__':main()
