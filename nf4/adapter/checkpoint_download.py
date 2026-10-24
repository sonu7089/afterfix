"""NF4 reproduction adapter v1: copy a local reviewed checkpoint and verify all hashes.

This replaces only artifact access in newly staged replications. It is not the
historical downloader and never contacts a private notebook or starts a GPU job.
"""
import json
import os
from pathlib import Path
import sys
import tempfile
import time
from .nf4_checkpoint import verify_checkpoint

def download_prepared(report_path):
    start=time.monotonic();report_path=Path(report_path)
    report=dict(status='validating',method='NF4 reproduction adapter v1: local copy with SHA-256 validation',
                historical_notebook_version=1,replication=True,network_used=False)
    def save():
        report['seconds']=time.monotonic()-start
        report_path.parent.mkdir(parents=True,exist_ok=True)
        tmp=report_path.with_suffix('.tmp');tmp.write_text(json.dumps(report,indent=2)+'\n');tmp.replace(report_path)
    save()
    try:
        config=json.loads(Path(__file__).with_name('nf4-runtime.json').read_text())
        directory=os.environ.get('AFTERFIX_NF4_CHECKPOINT') or config.get('checkpoint_directory')
        if not directory:raise ValueError('Set AFTERFIX_NF4_CHECKPOINT to the reviewed checkpoint directory')
        # Match the original worker's local-storage loading path, avoiding repeated reads from mounted inputs.
        scratch=Path(tempfile.mkdtemp(prefix='afterfix-nf4-replication-'))/'checkpoint'
        result=verify_checkpoint(directory,copy_to=scratch)
        report.update(status='completed',destination=result['destination'],total_bytes=result['total_bytes'],
                      validation=result['validation'],checkpoint_manifest_sha256=result['checkpoint_manifest_sha256'],
                      files=[dict(name=n,**r) for n,r in result['files'].items()])
    except Exception as e:
        report.update(status='error',error_type=type(e).__name__,error=str(e))
    finally:save()
    return report['status']=='completed'

if __name__=='__main__':sys.exit(0 if download_prepared(sys.argv[1]) else 1)
