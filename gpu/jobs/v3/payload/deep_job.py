"""One bounded Kaggle job, serial model stages, incremental public-only outputs."""
import concurrent.futures
import hashlib
import json
import os
import pathlib
import shutil
import signal
import subprocess
import sys
import tarfile
import tempfile
import threading
import time
import traceback
import urllib.request


def sha(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda:f.read(8*1024*1024),b''):h.update(chunk)
    return h.hexdigest()


def atomic(path,data):
    tmp=path.with_suffix('.tmp');tmp.write_text(json.dumps(data,indent=2));tmp.replace(path)


def download(spec,dest):
    """Fixed-size parallel ranges, validated against official size and SHA-256."""
    size=spec['bytes'];chunk_size=64*1024*1024;lock=threading.Lock()
    with dest.open('wb') as file:file.truncate(size)
    def fetch(start):
        end=min(size-1,start+chunk_size-1)
        req=urllib.request.Request(spec['url'],headers={'Range':f'bytes={start}-{end}','User-Agent':'AfterFix-research'})
        # Range downloads are only used for HF files; release archives use ordinary HTTP below.
        with urllib.request.urlopen(req,timeout=60) as response:
            if response.status!=206 or response.headers.get('Content-Range')!=f'bytes {start}-{end}/{size}':
                raise RuntimeError('Unexpected range response')
            position=start
            with dest.open('r+b') as file:
                file.seek(start)
                while position<=end:
                    data=response.read(min(4*1024*1024,end-position+1))
                    if not data:raise RuntimeError('Truncated download')
                    file.write(data);position+=len(data)
    if spec.get('ranges',False):
        with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:list(pool.map(fetch,range(0,size,chunk_size)))
    else:
        with urllib.request.urlopen(spec['url'],timeout=60) as response,dest.open('wb') as file:
            shutil.copyfileobj(response,file,length=4*1024*1024)
    if dest.stat().st_size!=size or sha(dest)!=spec['sha256']:raise RuntimeError('Download size/hash mismatch')


def bounded_download(spec,dest,seconds):
    config=dest.with_suffix('.download.json');atomic(config,spec)
    subprocess.run([sys.executable,__file__,'download',str(config),str(dest)],check=True,timeout=seconds)


def main(workspace_path='/kaggle/working'):
    workspace=pathlib.Path(workspace_path);root=workspace/'deep-results';root.mkdir(exist_ok=True)
    plan=json.loads((root/'plan.json').read_text());manifest=json.loads((workspace/'deep-payload-manifest.json').read_text())
    started=time.monotonic();deadline=started+41400
    result=dict(status='starting',study_version=plan['version'],planned_attempts=144,stages=[],gpu_hours_ceiling=11.5)
    def save():result['elapsed_seconds']=time.monotonic()-started;atomic(root/'summary.json',result)
    save();scratch=pathlib.Path(tempfile.mkdtemp(prefix='afterfix-deep-',dir='/tmp'))
    try:
        for name,expected in manifest['files'].items():
            if sha(workspace/name)!=expected:raise ValueError('Payload mismatch: '+name)
        result['payload_verified']=True
        gpu=subprocess.run(['nvidia-smi','--query-gpu=name,memory.total,driver_version','--format=csv,noheader'],capture_output=True,text=True,check=True,timeout=10).stdout
        result['gpu_inventory']=gpu
        if len(gpu.strip().splitlines())!=2 or any('T4' not in row for row in gpu.strip().splitlines()):raise RuntimeError('Expected exactly two free T4 GPUs')
        if shutil.disk_usage(scratch).free<30*1024**3:raise RuntimeError('Insufficient scratch disk for pinned model')
        runtime=scratch/'runtime';runtime.mkdir()
        result['status']='installing_runtime';save()
        for index,spec in enumerate(plan['runtime']['archives']):
            archive=scratch/f'runtime-{index}.tar.gz';bounded_download(spec,archive,300)
            with tarfile.open(archive) as tar:tar.extractall(runtime,filter='data')
        binaries=list(runtime.rglob('llama-server'))
        if len(binaries)!=1:raise RuntimeError('Ambiguous runtime binary')
        binary=binaries[0];binary.chmod(binary.stat().st_mode|0o111)
        libs=sorted({str(p.parent) for p in runtime.rglob('*.so*')})
        os.environ['LD_LIBRARY_PATH']=os.pathsep.join(libs+[os.environ.get('LD_LIBRARY_PATH','')])
        version=subprocess.run([str(binary),'--version'],capture_output=True,text=True,check=True,timeout=20)
        result['runtime_version']=version.stdout+version.stderr
        for model in plan['models']:
            stage=dict(model=model['key'],status='downloading');result['stages'].append(stage);save()
            path=scratch/model['filename'];ts=time.monotonic()
            bounded_download(model,path,min(900,max(1,deadline-time.monotonic()-60)))
            stage['download_seconds']=time.monotonic()-ts;stage['sha256']=sha(path);stage['status']='running';save()
            log=root/f"{model['key']}-worker.log"
            with log.open('w') as output:
                proc=subprocess.Popen([sys.executable,'-u',str(workspace/'deep_worker.py'),str(root),model['key'],str(path),str(binary)],
                                      stdout=output,stderr=subprocess.STDOUT,start_new_session=True)
                # 72 * 240 seconds + preflight/loading/cleanup margin.
                cap=min(18300,max(1,deadline-time.monotonic()-60))
                try:proc.wait(timeout=cap)
                except subprocess.TimeoutExpired:
                    os.killpg(proc.pid,signal.SIGKILL);proc.wait();stage['watchdog_timeout']=True
            stage['worker_returncode']=proc.returncode
            report=root/model['key']/'agent-results.json'
            worker=json.loads(report.read_text()) if report.exists() else {}
            stage['status']=worker.get('status','no_worker_report');stage['attempted_runs']=len(worker.get('runs',[]));save()
            # Scratch weights are never saved as Kaggle output. Remove only this known file.
            path.unlink(missing_ok=True)
            if stage['status']!='completed' or proc.returncode!=0:raise RuntimeError('Model stage incomplete; stop, preserve partial evidence, no automatic fallback')
        result['status']='completed'
    except Exception:result['status']='infrastructure_error';result['error']=traceback.format_exc()
    finally:save()
    return 0 if result['status']=='completed' else 1


if __name__=='__main__':
    if len(sys.argv)>1 and sys.argv[1]=='download':download(json.loads(pathlib.Path(sys.argv[2]).read_text()),pathlib.Path(sys.argv[3]))
    else:sys.exit(main())
