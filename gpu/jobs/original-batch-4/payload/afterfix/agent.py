"""Bounded 12B pilot worker; imports only public task data and restricted SQL tools."""
import importlib.metadata
import json
import os
import pathlib
import sqlite3
import sys
import time
import traceback

from .protocol import BUDGET, configuration, schedule
from .runner import BudgetStop, run_case
from .model_source import validate_prepared_checkpoint
from . import protocol as active_protocol
if os.environ.get('AFTERFIX_PROTOCOL') == 'v2':
    from . import protocol_v2 as active_protocol
    from .protocol_v2 import BUDGET, configuration, schedule



def main():
    import torch
    from transformers import AutoProcessor, AutoModelForMultimodalLM, BitsAndBytesConfig
    root=pathlib.Path(sys.argv[1]);model_path=sys.argv[2]
    tasks=json.loads((root/'public-incidents.json').read_text())
    methods=json.loads(os.environ.get('AFTERFIX_METHODS','["ordinary", "checklist", "provenance"]'))
    plan=schedule(tasks,methods)
    result={'status':'loading','runs':[],'configuration':{
        **configuration(), 'model':'google/gemma-4/transformers/gemma-4-12b-it/2',
        'quantization':'CPU NF4 double quantization; FP16 compute',
        'selected_methods':methods,
        'schedule':[{'id':t['id'],'method':m} for t,m in plan]}}
    start=time.monotonic()
    def save():
        result['worker_elapsed_seconds']=time.monotonic()-start
        temporary=root/'agent-results.tmp'
        temporary.write_text(json.dumps(result,indent=2))
        temporary.replace(root/'agent-results.json')
    save()
    try:
        torch.manual_seed(17)
        result['versions']={n:importlib.metadata.version(n) for n in ['torch','transformers','accelerate','bitsandbytes']}
        result['versions']['sqlite']=sqlite3.sqlite_version
        result['versions']['python']=sys.version
        result['gpus']=[{'name':torch.cuda.get_device_name(i),'total_GiB':torch.cuda.get_device_properties(i).total_memory/2**30} for i in range(torch.cuda.device_count())]
        result['host']={'cpu_count':os.cpu_count(),'torch_threads':torch.get_num_threads(),
                        'cuda_runtime':torch.version.cuda}
        meminfo=pathlib.Path('/proc/meminfo')
        if meminfo.exists():
            result['host']['memory']=[line for line in meminfo.read_text().splitlines()
                                     if line.startswith(('MemTotal:','MemAvailable:','SwapTotal:','SwapFree:'))]
        result['loading_phase']='processor';save()
        processor=AutoProcessor.from_pretrained(model_path,local_files_only=True)
        if not (pathlib.Path(model_path)/'AFTERFIX_PROVENANCE.json').exists():
            raise RuntimeError('Protocol v1 requires the pinned prepared checkpoint')
        if (pathlib.Path(model_path)/'AFTERFIX_PROVENANCE.json').exists():
            result['configuration']['prepared_checkpoint']=validate_prepared_checkpoint(model_path)
            quantization_kwargs={}
        else:
            quantization_kwargs={'quantization_config':BitsAndBytesConfig(load_in_4bit=True,bnb_4bit_quant_type='nf4',bnb_4bit_use_double_quant=True,bnb_4bit_compute_dtype=torch.float16)}
        result['loading_phase']='prepared_weights' if not quantization_kwargs else 'weights_and_quantization';save()
        model=AutoModelForMultimodalLM.from_pretrained(model_path,local_files_only=True,
            **quantization_kwargs,dtype=torch.float16,device_map={'':0},attn_implementation='sdpa')
        model.eval();torch.cuda.synchronize()
        result['load_seconds']=time.monotonic()-start
        result['parameter_devices']=sorted({str(p.device) for p in model.parameters()})
        if result['parameter_devices']!=['cuda:0']:raise RuntimeError('Unexpected parameter device placement')
        result['status']='running';result['loading_phase']='ready';save()
        def generate(messages, max_tokens, seconds):
            inputs=processor.apply_chat_template(messages,tokenize=True,return_dict=True,
                return_tensors='pt',add_generation_prompt=True,enable_thinking=False).to('cuda:0')
            n=inputs['input_ids'].shape[-1]
            if n>BUDGET['max_input_tokens']:
                raise BudgetStop('context_budget')
            torch.cuda.synchronize();ts=time.monotonic()
            with torch.inference_mode():
                output=model.generate(**inputs,max_new_tokens=max_tokens,do_sample=False,max_time=seconds)
            torch.cuda.synchronize();duration=time.monotonic()-ts
            tokens=output[0,n:]
            return {'input_tokens':n,'output_tokens':len(tokens),'generation_seconds':duration,
                    'response':processor.decode(tokens,skip_special_tokens=True),
                    'reached_token_limit':len(tokens)>=max_tokens}

        for task,method in plan:
            torch.manual_seed(BUDGET['seed'])
            torch.cuda.reset_peak_memory_stats()
            run={};result['runs'].append(run)
            run_case(task,method,generate,run,on_save=save,protocol=active_protocol)
            run['peak_allocated_GiB']=torch.cuda.max_memory_allocated()/2**30
            run['peak_reserved_GiB']=torch.cuda.max_memory_reserved()/2**30
            save();print('Completed '+task['id']+'/'+method+': '+run['stop_reason']+
                         ' in %.1fs'%run['wall_seconds'],flush=True)
        result['status']='completed'
    except Exception:result['status']='error';result['error']=traceback.format_exc()
    finally:save()


if __name__=='__main__':main()
