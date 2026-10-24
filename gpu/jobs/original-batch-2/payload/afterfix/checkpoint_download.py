"""Download the pinned private NF4 artifact directly, without mounting notebook inputs."""
import concurrent.futures
import json
import pathlib
import sys
import tempfile
import time
from .model_source import SOURCE,validate_prepared_checkpoint


def download_prepared(report_path):
    from kagglehub.http_resolver import NotebookOutputHttpResolver
    from kagglehub.handle import parse_notebook_handle
    handle=parse_notebook_handle('nitishsongara/afterfix-checkpoint-cpu').with_version(1)
    destination=pathlib.Path(tempfile.mkdtemp(prefix='afterfix-http-',dir='/tmp'))
    prefix='gemma-4-12b-it-nf4/'
    started=time.monotonic();report_path=pathlib.Path(report_path)
    r={'status':'downloading','method':'Kaggle notebook-output HTTP resolver','version':1,'files':[],
       'destination':str(destination/prefix),'workers':6}
    def save():
        r['seconds']=time.monotonic()-started
        tmp=report_path.with_suffix('.tmp');tmp.write_text(json.dumps(r,indent=2));tmp.replace(report_path)
    def fetch(name):
        if pathlib.Path(name).name!=name:raise ValueError('Invalid artifact filename')
        t=time.monotonic()
        path,version=NotebookOutputHttpResolver()._resolve(handle,path=prefix+name,output_dir=str(destination))
        if version!=1:raise ValueError('Unexpected artifact version')
        return {'name':name,'bytes':pathlib.Path(path).stat().st_size,'seconds':time.monotonic()-t}
    save()
    try:
        r['files'].append(fetch('AFTERFIX_PROVENANCE.json'))
        provenance=json.loads((destination/prefix/'AFTERFIX_PROVENANCE.json').read_text())
        if provenance.get('status')!='completed' or provenance.get('source')!=SOURCE:
            raise ValueError('Invalid source provenance')
        names=['config.json','generation_config.json','model.safetensors.index.json','processor_config.json',
               'tokenizer.json','tokenizer_config.json','chat_template.jinja']
        names.extend(x['name'] for x in provenance['weight_files'])
        with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:
            for future in concurrent.futures.as_completed([pool.submit(fetch,name) for name in names]):
                r['files'].append(future.result());save()
        r['validation']=validate_prepared_checkpoint(destination/prefix)
        r['total_bytes']=sum(f['bytes'] for f in r['files']);r['status']='completed'
    except Exception as e:
        r['status']='error';r['error_type']=type(e).__name__
    finally:save()
    return r['status']=='completed'


if __name__=='__main__':
    sys.exit(0 if download_prepared(sys.argv[1]) else 1)
