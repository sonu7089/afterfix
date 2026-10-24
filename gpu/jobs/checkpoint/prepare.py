"""CPU-only NF4 preparation and reload validation of the official 12B checkpoint."""
import json, pathlib, subprocess, sys, time, traceback
out=pathlib.Path('/kaggle/working');started=time.monotonic()
report={'status':'starting','gpu_requested':False,'worker_timeout_seconds':1800}
WORKER=r'''
import gc, importlib.metadata, json, pathlib, sys, time, traceback
root=pathlib.Path('/kaggle/working');dest=root/'gemma-4-12b-it-nf4';started=time.monotonic()
r={'status':'starting','source':'google/gemma-4/transformers/gemma-4-12b-it/2','quantization_backend':'CPU bitsandbytes NF4 double quantization, FP16 compute; not official QAT'}
def save():
    r['elapsed_seconds']=time.monotonic()-started
    (root/'preparation-result.json').write_text(json.dumps(r,indent=2))
    print(json.dumps(r),flush=True)
try:
    import torch, bitsandbytes as bnb
    from transformers import AutoProcessor, AutoModelForMultimodalLM, BitsAndBytesConfig
    torch.set_num_threads(2);torch.manual_seed(17)
    assert not torch.cuda.is_available(),'CPU job must have no CUDA device'
    r['versions']={n:importlib.metadata.version(n) for n in ['torch','transformers','accelerate','bitsandbytes']}
    t=time.monotonic()
    q=bnb.nn.Params4bit(torch.randn(1024,1024,dtype=torch.float16),requires_grad=False,
        quant_type='nf4',compress_statistics=True).to('cpu')
    assert q.quant_state is not None,'CPU quantization did not run'
    restored=bnb.functional.dequantize_4bit(q.data,q.quant_state)
    assert torch.isfinite(restored).all()
    r['cpu_quantization_control_seconds']=time.monotonic()-t
    del q,restored
    paths=[p.parent for p in pathlib.Path('/kaggle/input').rglob('config.json') if 'gemma-4-12b-it' in p.parts]
    assert len(paths)==1,paths
    r['status']='quantizing';save();t=time.monotonic()
    processor=AutoProcessor.from_pretrained(paths[0],local_files_only=True)
    model=AutoModelForMultimodalLM.from_pretrained(paths[0],local_files_only=True,
        quantization_config=BitsAndBytesConfig(load_in_4bit=True,bnb_4bit_quant_type='nf4',bnb_4bit_use_double_quant=True,bnb_4bit_compute_dtype=torch.float16),
        dtype=torch.float16,device_map={'':'cpu'},attn_implementation='sdpa')
    r['quantized_load_seconds']=time.monotonic()-t
    r['quantized_modules']=sum(isinstance(m,bnb.nn.Linear4bit) for m in model.modules())
    assert r['quantized_modules']>0
    r['footprint_GiB']=model.get_memory_footprint()/2**30
    r['status']='saving';save();t=time.monotonic()
    model.save_pretrained(dest,max_shard_size='512MB');processor.save_pretrained(dest)
    r['save_seconds']=time.monotonic()-t
    r['artifact_bytes']=sum(p.stat().st_size for p in dest.rglob('*') if p.is_file())
    r['weight_files']=[{'name':p.name,'bytes':p.stat().st_size} for p in sorted(dest.glob('*.safetensors'))]
    del model;gc.collect()
    r['status']='reloading';save();t=time.monotonic()
    model=AutoModelForMultimodalLM.from_pretrained(dest,local_files_only=True,
        dtype=torch.float16,device_map={'':'cpu'},attn_implementation='sdpa')
    model.eval();r['reload_seconds']=time.monotonic()-t
    assert sum(isinstance(m,bnb.nn.Linear4bit) for m in model.modules())==r['quantized_modules']
    assert all(p.device.type=='cpu' for p in model.parameters())
    r['status']='checking_logits';save();t=time.monotonic()
    inputs=processor.apply_chat_template([{'role':'user','content':'What is 2 + 2? Answer with the number only.'}],
        tokenize=True,return_dict=True,return_tensors='pt',add_generation_prompt=True,enable_thinking=False)
    with torch.inference_mode():
        output=model(**inputs,logits_to_keep=1)
    logits=output.logits[0,-1]
    assert torch.isfinite(logits).all(),'Non-finite reloaded model logits'
    r['cpu_forward_seconds']=time.monotonic()-t
    r['next_token_id']=int(logits.argmax());r['next_token']=processor.decode([r['next_token_id']])
    r['status']='completed'
    (dest/'AFTERFIX_PROVENANCE.json').write_text(json.dumps(r,indent=2))
except Exception:r['status']='error';r['error']=traceback.format_exc()
finally:save()
'''
try:
    with (out/'dependency-install.log').open('w') as log:
        p=subprocess.run([sys.executable,'-m','pip','install','--quiet','--disable-pip-version-check',
            'transformers==5.20.2','accelerate==1.15.0','bitsandbytes==0.50.2'],stdout=log,stderr=subprocess.STDOUT,timeout=120)
    if p.returncode:raise RuntimeError('Dependency install failed')
    worker=out/'prepare_worker.py';worker.write_text(WORKER)
    with (out/'prepare-worker.log').open('w') as log:
        try:
            p=subprocess.run([sys.executable,'-u',str(worker)],stdout=log,stderr=subprocess.STDOUT,timeout=1800)
            report['worker_returncode']=p.returncode
        except subprocess.TimeoutExpired:report['worker_timed_out']=True
    report['status']='finished'
except Exception:report['status']='error';report['error']=traceback.format_exc()
finally:
    report['elapsed_seconds']=time.monotonic()-started
    (out/'preparation-summary.json').write_text(json.dumps(report,indent=2));print(json.dumps(report),flush=True)
