"""Post hoc internal review: explicit fixture answers and separate boundary probes."""
import argparse
import copy
import hashlib
import json
from pathlib import Path
import sys


def canonical(value):
    value = json.loads(json.dumps(value))
    return {k:sorted(v,key=lambda r:json.dumps(r,sort_keys=True)) for k,v in value.items()}


def expected_rows(seed):
    n = lambda value: f'{value}_{seed}'
    q = seed % 5
    base = {
        'H01':{'outbox':[[n('m1'),'delivered',2],[n('m2'),'pending',1],[n('m3'),'canceled',0],[n('m4'),'failed',1],[n('m5'),'delivered',1]]},
        'H02':{'applied':[[n('order'),30+q,2],[n('healthy'),12,1],[n('idle'),4,0]]},
        'H03':{'compensation':[[n('s1'),'pending',3+q],[n('s2'),'none',0],[n('s3'),'done',2],[n('s4'),'none',0]]},
        'H04':{'job_results':[[n('j1'),'done',40+q],[n('j2'),'done',6],[n('j3'),'pending',0]]},
        'H05':{'allocations':[[n('kit1'),n('a'),3+q],[n('kit1'),n('b'),2],[n('kit3'),n('a'),2],[n('kit3'),n('c'),3]],'available':[[n('a'),25],[n('b'),18+q],[n('c'),12+q]]},
        'H06':{'transfer_state':[[n('t1'),10+q,4,6+q],[n('t2'),0,0,0],[n('t3'),3,3,0]],'stock':[[n('a'),90],[n('b'),31],[n('c'),23]]},
        'H07':{'line_state':[[n('l1'),4+q,4,1],[n('l2'),0,3,0],[n('l3'),3,0,0]]},
        'H08':{'escrow':[[n('a'),12,28],[n('b'),1,29],[n('c'),0,20]],'pool_free':[[n('p'),87+q]]},
        'H09':{'active_files':[[n('sales'),n('f1'),10+q],[n('sales'),n('shared'),10+q],[n('returns'),n('shared'),10+q]],'dataset_totals':[[n('sales'),20+2*q],[n('returns'),10+q]]},
        'H10':{'coverage':[[n('a'),i,n('left') if i<3 else n('old'),2 if i<3 else 1] for i in range(6)]+[[n('b'),0,n('bfile'),1]]},
        'H11':{'migrated':[[n('absent'),'legacy','default',0],[n('null'),None,'stored',0],[n('edited'),None,'operator',2],[n('healthy'),'kept','stored',0]]},
        'H12':{'cache':[[n('reuse'),3,8+q,1],[n('healthy'),1,6,1]]},
        'H13':{'effective_access':[[n('ana'),n('read')],[n('bo'),n('read')],[n('cy'),n('read')],[n('cy'),n('export')]],'access_counts':[[n('ana'),1],[n('bo'),1],[n('cy'),2],[n('di'),0]]},
        'H14':{'access':[[n('ana'),n('read'),1],[n('cy'),n('read'),1]]},
        'H15':{'membership':[[n('ana'),n('blue'),1],[n('ana'),n('red'),1],[n('bo'),n('blue'),1],[n('bo'),n('red'),1],[n('cy'),n('blue'),1]]},
        'H16':{'effective':[[n('root'),3,50],[n('child'),2,50],[n('grand'),2,50],[n('healthy'),4,90]]},
        'H17':{'readings':[[n('east'),14+q,5],[n('west'),24+q,1],[n('idle'),3+q,0]]},
        'H18':{'allocation':[[n('a'),2,7+q],[n('b'),1,3],[n('c'),1,0]]},
        'H19':{'charges':[[n('a'),n('e1'),8,0,16],[n('a'),n('e2'),2+q,4,24+2*q],[n('a'),n('e4'),3,0,6],[n('b'),n('e5'),2,0,2]]},
        'H20':{'intervals':[[n('a'),0,2,10+q],[n('a'),2,4,20+q],[n('a'),4,6,30+q],[n('a'),6,7,20+q],[n('a'),7,8,10+q],[n('b'),0,2,5]]},
        'H21':{'releases':[[n('b1'),'blocked',1],[n('b2'),'held',1],[n('b3'),'released',1],[n('b4'),'blocked',0],[n('b5'),'blocked',1]]},
        'H22':{'canonical':[[n('a'),n('a'),3],[n('b'),n('a'),3],[n('c'),n('a'),3],[n('d'),n('d'),1],[n('e'),n('e'),1]]},
        'H23':{'watermarks':[[n('a'),0,3],[n('b'),1,1]]},
        'H24':{'restored':[[n('child'),1,None,'usable'],[n('edited'),2,None,'operator update'],[n('healthy'),1,None,'kept']]}}
    future = copy.deepcopy(base)
    future['H01']['outbox'][1]=[n('m2'),'delivered',2];future['H01']['outbox'].append([n('m6'),'pending',0])
    future['H02']['applied'][0]=[n('order'),99,3]
    future['H03']['compensation'][0]=[n('s1'),'done',3+q];future['H03']['compensation'][3]=[n('s4'),'pending',5]
    future['H04']['job_results'][0]=[n('j1'),'pending',0];future['H04']['job_results'][2]=[n('j3'),'done',7+q]
    future['H05']={'allocations':[[n('kit3'),n('a'),2],[n('kit3'),n('c'),3],[n('kit4'),n('b'),1+q],[n('kit4'),n('c'),2]],'available':[[n('a'),28+q],[n('b'),19],[n('c'),10+q]]}
    future['H06']['transfer_state'][0]=[n('t1'),10+q,10+q,0];future['H06']['stock'][1]=[n('b'),37+q]
    future['H07']['line_state'][0]=[n('l1'),4+q,4,0];future['H07']['line_state'][2]=[n('l3'),1,2,0]
    future['H08']={'escrow':[[n('a'),6,34],[n('b'),1,29],[n('c'),3,17]],'pool_free':[[n('p'),90+q]]}
    future['H09']={'active_files':[[n('sales'),n('f2'),25+q],[n('returns'),n('shared'),10+q]],'dataset_totals':[[n('sales'),25+q],[n('returns'),10+q],[n('emptyset'),0]]}
    future['H10']['coverage']=[[n('a'),i,n('left') if i<3 else n('right'),2] for i in range(6)]+[[n('b'),0,n('bfile'),1]]
    future['H11']['migrated'][0]=[n('absent'),'late manual','operator',1]
    future['H12']['cache'][1]=[n('cold'),1,11+q,1]
    future['H13']={'effective_access':[[n(x),n('read')] for x in ('ana','bo','cy','di')],'access_counts':[[n(x),1] for x in ('ana','bo','cy','di')]}
    future['H14']['access'].append([n('bo'),n('read'),1])
    future['H15']['membership'][0]=[n('ana'),n('blue'),2]
    future['H16']={'effective':[[n('healthy'),4,90]]}
    future['H17']={'readings':[[n('east'),17+q,6],[n('west'),24+q,1],[n('idle'),9+q,1]]}
    future['H18']['allocation'][2]=[n('c'),1,2]
    future['H19']['charges'].append([n('a'),n('e6'),7+q,3,29+2*q])
    future['H20']={'intervals':[[n('a'),0,2,10+q],[n('a'),2,7,20+q],[n('a'),7,8,10+q],[n('b'),0,2,5]]}
    future['H21']['releases'][2]=[n('b3'),'held',1];future['H21']['releases'][3]=[n('b4'),'released',1]
    future['H22']['canonical'][3]=[n('d'),n('d'),2];future['H22']['canonical'][4]=[n('e'),n('d'),2]
    future['H23']['watermarks'][0]=[n('a'),3,4]
    future['H24']={'restored':[[n('child'),2,None,'new child value'],[n('edited'),2,None,'operator update']]}
    return base,future


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--source',required=True);ap.add_argument('--output',required=True)
    args=ap.parse_args();source=Path(args.source).resolve();dest=Path(args.output).resolve()
    if dest.exists():raise RuntimeError('Review output exists. Choose a new path.')
    sys.path.insert(0,str(source))
    from afterfix.heldout_cases import build, future_fixture, oracle, IMPLEMENTED
    from afterfix.heldout_grade import validate_suite
    from afterfix.engine import materialize,run_sql,snapshot
    checks=[]
    for seed in (0,7,19):
        expected, continued=expected_rows(seed)
        for ident in IMPLEMENTED:
            task,private=build(ident,seed);future,future_answer=future_fixture(ident,seed);healthy,_=build(ident,seed,healthy=True)
            assert canonical(expected[ident])==canonical(private['expected']),(ident,seed,'initial')
            assert canonical(continued[ident])==canonical(future_answer),(ident,seed,'continuation')
            assert canonical(expected[ident])==canonical({k:healthy['tables'][k] for k in task['writable_tables']}),(ident,seed,'healthy')
            checks.append(dict(id=ident,seed=seed,initial_expected=expected[ident],continuation_expected=continued[ident],healthy_expected=expected[ident],exact=True))
    admissions=validate_suite()
    probes=[]
    def sql_result(task,sql):
        db=materialize(task)
        try:
            run_sql(db,task,sql)
            state=snapshot(db,task)
            return dict(rows=canonical({k:state[k] for k in task['writable_tables']}),error=None)
        except Exception as exc:return dict(rows=None,error=str(exc))
        finally:db.close()
    for ident,table,row in (
        ('H04','completions',['review_tie','j1_0',2,9,'new_0',1,999]),
        ('H12','materializations',['review_tie','reuse_0',3,1,999,1])):
        task,private=build(ident);task=copy.deepcopy(task);task['tables'][table].append(row)
        actual=sql_result(task,private['reference_recovery']);answer=canonical(oracle(ident,task['tables']))
        assert actual['error'] or actual['rows']!=answer
        probes.append(dict(id=ident,probe='conflicting_equal_sequence',in_sealed_fixture=False,oracle=answer,reference=actual,
                           finding='Unspecified conflicting sequence tie; reference and oracle do not agree on this added input.'))
    task,private=build('H23');task=copy.deepcopy(task);task['tables']['streams'].append(['review_empty']);task['tables']['progress'].append(['review_empty',0])
    actual=sql_result(task,private['reference_recovery']);answer=canonical(oracle('H23',task['tables']))
    assert actual['error'] is None and actual['rows']!=answer
    probes.append(dict(id='H23',probe='stream_without_partitions',in_sealed_fixture=False,oracle=answer,reference=actual,
                       finding='No-partition stream produces NULL in reference SQL and zero in oracle. Empty-stream behavior is not established by the evaluated fixtures.'))
    task,private=build('H24',healthy=True);task=copy.deepcopy(task)
    task['tables']['versions'].append(['review_child',1,'survivor','healthy_0','keep'])
    task['tables']['restored']=oracle('H24',task['tables'])['restored']
    task['tables']['erasures'].append(['other_0']);task['tables']['work']=[['healthy_0']]
    answer=canonical(oracle('H24',task['tables']));narrow=sql_result(task,task['application_sql'])
    assert narrow['error'] is None and narrow['rows']!=answer
    task['tables']['work'].append(['review_child']);expanded=sql_result(task,task['application_sql'])
    assert expanded['error'] is None and expanded['rows']==answer
    probes.append(dict(id='H24',probe='erase_parent_with_surviving_child',in_sealed_fixture=False,oracle=answer,
        narrow_work=narrow,expanded_work=expanded,finding='Patch correctness depends on placing the surviving child in work when its parent disappears. The frozen H24 prompt does not explicitly define that expansion.'))
    # Classify rather than silently strengthening historical input contracts.
    assumptions=[]
    for seed in (0,7,19):
        for ident in ('H04','H12','H23','H24'):
            initial,_=build(ident,seed);future,_=future_fixture(ident,seed)
            for phase,task in (('initial',initial),('continuation',future)):
                t=task['tables']
                if ident=='H04':
                    keys=[tuple(r[1:6]) for r in t['completions']];assert len(keys)==len(set(keys))
                elif ident=='H12':
                    keys=[tuple(r[1:4]) for r in t['materializations'] if r[5]];assert len(keys)==len(set(keys))
                elif ident=='H23':
                    assert all(any(p[0]==s for p in t['partitions']) for s, in t['streams'])
                else:
                    # Existing continuation was checked against explicit expected rows and admission suite above.
                    assert t['work']==([] if phase=='initial' else [[f'healthy_{seed}'],[f'child_{seed}']])
                assumptions.append(dict(id=ident,seed=seed,phase=phase,checked=True))
    report=dict(status='passed_for_evaluated_fixtures_with_documented_boundaries',reviewer='Codex AI assistant',
        independent_human_review=False,post_hoc=True,cases=24,case_seed_checks=72,explicit_projection_comparisons=144,
        healthy_comparisons=72,fixture_checks=checks,admissions=admissions,boundary_probes=probes,
        relevant_fixture_assumptions=assumptions,model_attempts=0,gpu_jobs_started=0,
        source_hashes={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted((source/'afterfix').glob('*.py'))
                       if p.name in ('heldout_cases.py','heldout_remaining.py','heldout_grade.py','engine.py')},
        decision='Retain existing scores and study separation; disclose boundaries. No general correctness claim outside tested fixtures.')
    dest.parent.mkdir(parents=True,exist_ok=True);dest.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print('PASS: 24 cases, 72 case/seed reviews, 144 explicit initial/continuation comparisons, 72 healthy comparisons and 24 admission suites.')
    print('Four separate boundary probes reproduced: H04 and H12 ties, H23 empty stream, H24 work expansion. No model attempts.')


if __name__=='__main__':main()
