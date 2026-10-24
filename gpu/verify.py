"""Offline integrity, payload and transport checks. Never launches inference."""
import ast
import hashlib
import importlib.util
import json
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parent


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def verify():
    manifest = read(ROOT/'MANIFEST.json')
    for name, expected in manifest['files'].items():
        path = (ROOT/name).resolve()
        assert path.is_relative_to(ROOT) and path.is_file(), name
        assert hashlib.sha256(path.read_bytes()).hexdigest() == expected, name
    jobs = read(ROOT/'JOBS.json')
    checked = []
    for job in jobs:
        base = ROOT/job['folder']
        launcher = base/job['code_file']
        tree = ast.parse(launcher.read_text(encoding='utf-8'))
        if job['key'] == 'checkpoint':
            worker = next(ast.literal_eval(n.value) for n in tree.body if isinstance(n,ast.Assign)
                          and any(isinstance(t,ast.Name) and t.id=='WORKER' for t in n.targets))
            compile(worker,'frozen checkpoint worker','exec')
            checked.append(dict(job=job['key'],preparation_worker_compiles=True))
            continue
        payload = next(ast.literal_eval(n.value) for n in tree.body if isinstance(n,ast.Assign)
                       and any(isinstance(t,ast.Name) and t.id=='FILES' for t in n.targets))
        for name, text in payload.items():
            path=(base/'payload'/name).resolve()
            assert path.is_relative_to((base/'payload').resolve()), name
            assert path.read_bytes()==text.encode('utf-8'), name
        payload_manifest=read(base/'payload'/job['payload_manifest'])
        for name, expected in payload_manifest['files'].items():
            assert hashlib.sha256(payload[name].encode()).hexdigest()==expected, name
        assert not any('grade' in name or 'heldout_cases' in name or 'heldout_remaining' in name for name in payload)
        if job['key']=='v3':
            plan=read(base/'payload/deep-results/plan.json')
            assert plan['model_order']==['31b','12b'] and plan['planned_attempts']==144
            assert plan['budget']['max_turns']==12 and plan['budget']['max_generated_tokens_per_case']==4096
            assert plan['bos_amendment']['exactly_one_leading_bos']
            schedule=plan['schedule']
        else:
            config=read(base/'payload/afterfix-results/run-config.json')
            schedule=config['schedule']
        assert len(schedule)==job['cells_per_model']
        assert len({(cell['id'],cell['method']) for cell in schedule})==len(schedule)
        checked.append(dict(job=job['key'],payload_files=len(payload),schedule_cells=len(schedule)))
    compiled=0
    for path in ROOT.rglob('*.py'):
        compile(path.read_bytes(),str(path),'exec');compiled+=1

    # Exercise the exact packaged v3 modules with mocked local HTTP responses.
    # No server process, model import, network request or GPU is involved.
    base=ROOT/'jobs/v3/payload'
    def load(name):
        spec=importlib.util.spec_from_file_location('supplement_'+name,base/(name+'.py'))
        module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module
    transport=load('deep_http');placement=load('startup_verification');controls=0
    for value, expected in [('hello','<bos>hello'),('<bos>hello','<bos>hello')]:
        assert transport.normalize_bos(value)==expected;controls+=1
    for value in ['',None,'<bos><bos>hello','hello<bos>']:
        try:transport.normalize_bos(value)
        except ValueError:controls+=1
        else:raise AssertionError('Invalid BOS text accepted')
    transport.validate_bos_tokens([2,17,19]);controls+=1
    for value in [[],[17,2],[2,2],['2'],[True],None]:
        try:transport.validate_bos_tokens(value)
        except ValueError:controls+=1
        else:raise AssertionError('Invalid BOS token array accepted')
    calls=[]
    def fake_request(endpoint,data=None,timeout=15):
        calls.append((endpoint,data))
        return {'prompt':'hello'} if endpoint=='/apply-template' else {'tokens':[2,17,19]}
    with patch.object(transport,'request',fake_request):
        assert transport.format_prompt([{'role':'user','content':'hello'}])==('<bos>hello',[2,17,19])
    assert calls[0][1]['chat_template_kwargs']['enable_thinking'] is False
    assert calls[1][1]==dict(content='<bos>hello',add_special=False,parse_special=True);controls+=1
    snapshot=dict(devices=dict(returncode=0,stdout='0, gpu-a, Tesla T4, 15360, 9000\n1, gpu-b, Tesla T4, 15360, 9000\n',stderr=''),processes=dict(returncode=0,stdout='',stderr=''))
    log='offloaded 61/61 layers to GPU\nCUDA0 model buffer size = 8000 MiB\nCUDA1 model buffer size = 8000 MiB\n'
    assert placement.verify_placement(log,snapshot,123,61)['passed'];controls+=1
    for bad in ['',log.replace('61/61','60/61'),log.replace('CUDA1','CPU')]:
        assert not placement.verify_placement(bad,snapshot,123,61)['passed'];controls+=1
    with patch.object(transport.pathlib,'Path') as fake_path:
        fake_path.return_value.exists.return_value=True
        fake_path.return_value.read_text.return_value=json.dumps(dict(content='{}',tokens=[3,4]))+'\n'+json.dumps(dict(stop=True))+'\n'
        assert transport.read_stream('mock-stream.jsonl')==('{}',[3,4],{'stop':True});controls+=1
    return dict(status='passed',manifest_files=len(manifest['files']),jobs=checked,python_files_compiled=compiled,
                cpu_transport_and_placement_controls=controls,model_generation_performed=False,
                network_requests=0,gpu_jobs_submitted=0,
                limitation='Static payload checks and mocked CPU controls do not verify current checkpoint access, native tokenizer generation or cloud runtime availability.')


if __name__=='__main__':
    print(json.dumps(verify(),indent=2))
