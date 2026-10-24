"""One model's full 72-cell evaluation; no private fixtures or graders imported."""
import hashlib
import json
import os
import pathlib
import re
import subprocess
import sys
import time
import traceback
import sqlite3
from afterfix import protocol_v2 as protocol
from afterfix.runner import run_case,BudgetStop
from deep_http import request,format_prompt,read_stream,BOS_TOKEN,BOS_ID,TRANSPORT_VERSION,validate_bos_tokens
from startup_verification import LOG_ARGUMENTS,gpu_snapshot,verify_placement


def atomic(path,data):
    temp=path.with_suffix('.tmp');temp.write_text(json.dumps(data,indent=2));temp.replace(path)


def main():
    root=pathlib.Path(sys.argv[1]);model_key=sys.argv[2];model_path=sys.argv[3];binary=sys.argv[4]
    plan=json.loads((root/'plan.json').read_text());model=next(m for m in plan['models'] if m['key']==model_key)
    out=root/model_key;out.mkdir(exist_ok=True);tasks={t['id']:t for t in json.loads((root/'public-incidents.json').read_text())}
    started=time.monotonic();server=None;log=None
    result=dict(status='starting',study_version=plan['version'],transport_version=TRANSPORT_VERSION,model=model,configuration=protocol.configuration(),runs=[],
                versions={'python':sys.version,'sqlite':sqlite3.sqlite_version,'llama_cpp':plan['runtime']['release']})
    def save():
        result['worker_elapsed_seconds']=time.monotonic()-started;atomic(out/'agent-results.json',result)
    save()
    try:
        command=[binary,'--model',model_path,'--host','127.0.0.1','--port','8080','--n-gpu-layers','all',
            '--split-mode','layer','--tensor-split','1,1','--ctx-size','10240','--parallel','1',
            '--batch-size','512','--ubatch-size','128','--flash-attn','on','--cache-type-k','f16','--cache-type-v','f16',
            '--threads','4','--threads-batch','4','--jinja','--reasoning','off','--no-context-shift',
            '--cache-ram','0','--ctx-checkpoints','0','--fit','off','--no-warmup']+LOG_ARGUMENTS
        result['server_command']=command;result['status']='loading';save()
        log=(out/'server.log').open('w');server=subprocess.Popen(command,stdout=log,stderr=subprocess.STDOUT)
        load_started=time.monotonic()
        while time.monotonic()-load_started<300:
            if server.poll() is not None:raise RuntimeError('Server exited during load; see server.log')
            try:
                if request('/health',timeout=2).get('status')=='ok':break
            except Exception:pass
            time.sleep(1)
        else:raise TimeoutError('300-second loading cutoff')
        result['load_seconds']=time.monotonic()-load_started
        text=(out/'server.log').read_text(errors='replace')
        snapshot=gpu_snapshot();atomic(out/'startup-gpu-snapshot.json',snapshot)
        evidence=verify_placement(text,snapshot,server.pid,plan['startup_amendment']['expected_offload_layers'][model_key])
        atomic(out/'startup-verification.json',evidence)
        result['startup_verification']=evidence;save()
        if not evidence['passed']:raise RuntimeError('GPU startup verification failed: '+', '.join(evidence['failed_checks']))
        result['layer_offload']=evidence['offloaded_layers']
        result['server_props']=request('/props');result['server_models']=request('/v1/models')
        result['status']='preflight';save()
        if result['server_props'].get('bos_token')!=BOS_TOKEN:raise RuntimeError('Unexpected runtime BOS text')
        if request('/tokenize',dict(content=BOS_TOKEN,add_special=False,parse_special=True))['tokens']!=[BOS_ID]:
            raise RuntimeError('Runtime BOS ID does not match pinned model contract')
        if not re.search(r'tokenizer\.ggml\.bos_token_id\s+u32\s*=\s*2\b',text):
            raise RuntimeError('BOS ID not confirmed in model metadata')
        if not re.search(r'tokenizer\.ggml\.add_bos_token\s+bool\s*=\s*true\b',text):
            raise RuntimeError('Model does not declare the expected BOS policy')
        # Validate actual model templates/tokenizer for every initial task/method
        # before generating any benchmark answer. No private references are used.
        gates=[]
        for cell in plan['schedule']:
            messages=[{'role':'system','content':protocol.system_prompt(cell['method'])},
                      {'role':'user','content':json.dumps(protocol.public_task(tasks[cell['id']]),separators=(',',':'))}]
            prompt,tokens=format_prompt(messages)
            validate_bos_tokens(tokens)
            if len(tokens)>protocol.BUDGET['max_input_tokens']:raise ValueError('Initial prompt exceeds budget')
            if '<|turn>model' not in prompt:raise ValueError('Unexpected Gemma chat-template format')
            if not prompt.endswith('<|channel>thought\n<channel|>'):
                raise ValueError('Thinking-disabled empty-thought prefill not confirmed')
            gates.append(dict(**cell,input_tokens=len(tokens),bos_id=BOS_ID,bos_count=tokens.count(BOS_ID),formatted_prompt_sha256=hashlib.sha256(prompt.encode()).hexdigest(),
                              public_task_sha256=protocol.digest(protocol.public_task(tasks[cell['id']])),system_prompt_sha256=protocol.digest(protocol.system_prompt(cell['method']))))
        atomic(out/'tokenizer-preflight.json',gates)
        call_count=0
        def generate(messages,max_tokens,seconds):
            nonlocal call_count
            call_count+=1;t=time.monotonic()
            prompt,tokens=format_prompt(messages)
            validate_bos_tokens(tokens)
            if len(tokens)>protocol.BUDGET['max_input_tokens']:raise BudgetStop('context_budget')
            if not prompt.endswith('<|channel>thought\n<channel|>'):raise RuntimeError('Unexpected thinking-disabled suffix')
            atomic(out/f'prompt-{call_count:04d}.json',dict(messages=messages,formatted_prompt=prompt,
                tokens=tokens,bos_id=BOS_ID,bos_count=tokens.count(BOS_ID),input_tokens=len(tokens),
                formatted_prompt_sha256=hashlib.sha256(prompt.encode()).hexdigest()))
            remaining=seconds-(time.monotonic()-t)
            if remaining<1:raise BudgetStop('generation_time_budget')
            payload=dict(prompt=tokens,n_predict=max_tokens,temperature=0,seed=17,stream=True,return_tokens=True,
                         cache_prompt=False,repeat_penalty=1.0,samplers=['temperature'],sse_ping_interval=1)
            req=out/f'request-{call_count:04d}.json';stream=out/f'stream-{call_count:04d}.jsonl'
            atomic(req,payload)
            proc=subprocess.Popen([sys.executable,'-u',str(pathlib.Path(__file__).with_name('deep_http.py')),str(req),str(stream),str(remaining+10)])
            cutoff=False
            try:proc.wait(timeout=remaining)
            except subprocess.TimeoutExpired:cutoff=True;proc.kill();proc.wait()
            content,output_ids,final=read_stream(stream)
            if proc.returncode and not cutoff:raise RuntimeError('Generation transport failed')
            if not cutoff and final is None:raise RuntimeError('Missing final generation metadata')
            if final and final.get('truncated'):raise RuntimeError('Unexpected context truncation')
            if final and final.get('tokens_evaluated')!=len(tokens):raise RuntimeError('Server prompt token count differs from transmitted IDs')
            if not output_ids and content:raise RuntimeError('Generated tokens missing from native stream')
            # Include stop/EOG tokens in accounting when reported by the server.
            charged=max(len(output_ids),int((final or {}).get('tokens_predicted',len(output_ids))))
            if charged>max_tokens:raise RuntimeError('Server exceeded generation budget')
            if cutoff:
                # Disconnecting the killed streaming client cancels its request.
                # Require an idle slot before the next action; otherwise abort model.
                idle=False
                for _ in range(10):
                    if all(not s.get('is_processing',False) for s in request('/slots',timeout=1)):
                        idle=True;break
                    time.sleep(.1)
                if not idle:raise RuntimeError('Server did not cancel timed-out generation')
            return dict(response=content,input_tokens=len(tokens),output_tokens=charged,generation_seconds=time.monotonic()-t,
                        reached_token_limit=charged>=max_tokens,request_time_cutoff=cutoff,generated_token_ids=output_ids,
                        completion_metadata=final,formatted_prompt_sha256=hashlib.sha256(prompt.encode()).hexdigest())
        # A non-benchmark SQL action smoke check. Failure stops; never tune a prompt.
        smoke=generate([{'role':'user','content':'Return exactly this JSON object and nothing else: {"action":"query","sql":"SELECT 1;"}'}],96,80)
        atomic(out/'smoke.json',smoke)
        action,_=protocol.parse_response(smoke['response'],'ordinary')
        if action!={'action':'query','sql':'SELECT 1;'}:raise RuntimeError('Predeclared JSON generation smoke failed')
        result['status']='running';save()
        for cell in plan['schedule']:
            run={};result['runs'].append(run);save()
            run_case(tasks[cell['id']],cell['method'],generate,run,on_save=save,protocol=protocol)
            run['gpu_snapshot_after']=subprocess.run(['nvidia-smi','--query-gpu=memory.used,temperature.gpu,power.draw,clocks.sm',
                '--format=csv,noheader'],capture_output=True,text=True,timeout=5).stdout
            save()
        result['status']='completed'
    except Exception:result['status']='infrastructure_error';result['error']=traceback.format_exc()
    finally:
        if server is not None and server.poll() is None:
            server.terminate()
            try:server.wait(timeout=10)
            except subprocess.TimeoutExpired:server.kill();server.wait()
        if log:log.close()
        save()
    return 0 if result['status']=='completed' else 1


if __name__=='__main__':sys.exit(main())
