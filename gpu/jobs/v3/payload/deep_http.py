"""Local llama.cpp transport; native token IDs and hard subprocess deadlines."""
import json
import pathlib
import sys
import time
import urllib.request

BASE='http://127.0.0.1:8080'
BOS_TOKEN='<bos>'
BOS_ID=2
TRANSPORT_VERSION='afterfix-bos-transport-v3'


def request(path,data=None,timeout=15):
    req=urllib.request.Request(BASE+path,data=None if data is None else json.dumps(data).encode(),
        headers={'Content-Type':'application/json'})
    with urllib.request.urlopen(req,timeout=timeout) as response:return json.load(response)


def normalize_bos(prompt):
    if not isinstance(prompt,str) or not prompt:raise ValueError('Empty/non-string formatted prompt')
    if not prompt.startswith(BOS_TOKEN):prompt=BOS_TOKEN+prompt
    if prompt.count(BOS_TOKEN)!=1:raise ValueError('Duplicate or embedded BOS marker')
    return prompt


def validate_bos_tokens(tokens):
    if not isinstance(tokens,list) or not tokens or any(type(t) is not int for t in tokens):
        raise ValueError('Expected nonempty integer token array')
    if tokens[0]!=BOS_ID or tokens.count(BOS_ID)!=1:raise ValueError('Exactly one leading BOS ID required')


def format_prompt(messages):
    prompt=request('/apply-template',dict(messages=messages,chat_template_kwargs={'enable_thinking':False},reasoning_effort='none'))['prompt']
    prompt=normalize_bos(prompt)
    tokens=request('/tokenize',dict(content=prompt,add_special=False,parse_special=True))['tokens']
    validate_bos_tokens(tokens)
    return prompt,tokens


def stream_to_file(payload,path,seconds):
    req=urllib.request.Request(BASE+'/completion',data=json.dumps(payload).encode(),headers={'Content-Type':'application/json'})
    with pathlib.Path(path).open('w',encoding='utf-8',buffering=1) as output:
        with urllib.request.urlopen(req,timeout=seconds) as response:
            for line in response:
                if not line.startswith(b'data: '):continue
                data=json.loads(line[6:]);output.write(json.dumps(data)+'\n');output.flush()
                if data.get('stop'):break


def read_stream(path):
    chunks=[];tokens=[];final=None
    for line in pathlib.Path(path).read_text(encoding='utf-8').splitlines() if pathlib.Path(path).exists() else []:
        try:item=json.loads(line)
        except ValueError:continue # only a final partially written line can be absent
        if 'error' in item:raise RuntimeError('Inference server error: '+str(item['error']))
        if item.get('stop'):
            final=item
        else:
            chunks.append(item.get('content',''));tokens.extend(item.get('tokens',[]))
    return ''.join(chunks),tokens,final


if __name__=='__main__':
    payload=json.loads(pathlib.Path(sys.argv[1]).read_text())
    stream_to_file(payload,sys.argv[2],float(sys.argv[3]))
