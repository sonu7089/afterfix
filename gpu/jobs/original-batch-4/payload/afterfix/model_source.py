"""Validate the private prepared checkpoint before loading it."""
import hashlib
import json
import pathlib

SOURCE='google/gemma-4/transformers/gemma-4-12b-it/2'


def validate_prepared_checkpoint(path):
    path=pathlib.Path(path)
    provenance=json.loads((path/'AFTERFIX_PROVENANCE.json').read_text())
    if provenance.get('status')!='completed' or provenance.get('source')!=SOURCE:
        raise ValueError('Prepared checkpoint provenance is incomplete or has the wrong source')
    config_bytes=(path/'config.json').read_bytes()
    q=json.loads(config_bytes).get('quantization_config',{})
    required={'quant_method':'bitsandbytes','load_in_4bit':True,'bnb_4bit_quant_type':'nf4',
              'bnb_4bit_use_double_quant':True,'bnb_4bit_compute_dtype':'float16'}
    if any(q.get(k)!=v for k,v in required.items()):
        raise ValueError('Prepared checkpoint has unexpected quantization settings')
    files=provenance.get('weight_files',[])
    if not files:raise ValueError('Prepared checkpoint has no weight manifest')
    for item in files:
        name=item['name']
        if pathlib.Path(name).name!=name or not name.endswith('.safetensors'):
            raise ValueError('Invalid checkpoint weight filename')
        if (path/name).stat().st_size!=item['bytes']:
            raise ValueError('Prepared checkpoint weight size mismatch: '+name)
    return {'source':SOURCE,'preparation_kernel':'nitishsongara/afterfix-checkpoint-cpu/1',
            'quantization_backend':provenance['quantization_backend'],
            'config_sha256':hashlib.sha256(config_bytes).hexdigest(),
            'weight_bytes':sum(x['bytes'] for x in files),'weight_files':len(files)}
