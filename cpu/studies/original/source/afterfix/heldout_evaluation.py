"""Descriptive family-aware analysis of the locked 72-cell design; no model calls."""
from .heldout_grade import grade,COMPONENTS


def evaluate(plan,runs,grade_fn=grade):
    roster={c['id']:c for c in plan['roster']}
    methods=plan['primary_methods']+plan['exploratory_methods']
    expected={(i,m) for i in roster for m in methods}
    indexed={}
    for run in runs:
        key=(run['id'],run['method'])
        if key not in expected or key in indexed:
            raise ValueError('Unknown or duplicate scheduled cell; diagnostic retries must remain separate')
        indexed[key]=run
    scores=[]
    for batch in plan['batches']:
        for block in batch['blocks']:
            for method in block['methods']:
                ident=block['id'];run=indexed.get((ident,method))
                common=dict(id=ident,family=roster[ident]['family'],method=method)
                if not run or run.get('status')!='completed':
                    scores.append(dict(common,complete=None,outcome='infrastructure_incomplete'))
                elif not run.get('artifact'):
                    scores.append(dict(common,complete=False,outcome='no_valid_artifact'))
                else:
                    scores.append(dict(grade_fn(ident,run['artifact']),**common))
    summary={'by_method':{},'paired_contrasts':{},'comparison_ready':all(s['complete'] is not None for s in scores),
             'note':'Descriptive case-level results. Seed variants are not observations. Families were purposively designed; no population significance claim.'}
    def stats(subset):
        observed=[s for s in subset if s['complete'] is not None]
        n=len(observed);passed=sum(s['complete'] is True for s in observed)
        return dict(planned=len(subset),evaluated=n,infrastructure_incomplete=len(subset)-n,complete_recoveries=passed,
                    complete_recovery_rate=passed/n if n else None,
                    outcomes={o:sum(s['outcome']==o for s in subset) for o in
                              ('complete','executable_but_wrong','sql_execution_failure','no_valid_artifact','infrastructure_incomplete')})
    for method in methods:
        subset=[s for s in scores if s['method']==method]
        families={f:stats([s for s in subset if s['family']==f]) for f in plan['families']}
        full=all(v['evaluated']==v['planned'] for v in families.values())
        mr=[r for r in runs if r['method']==method]
        summary['by_method'][method]={**stats(subset),'families':families,
            'family_macro_rate':sum(f['complete_recovery_rate'] for f in families.values())/len(families) if full else None,
            'macro_note':'Only computed when every scheduled family cell is observed.',
            'component_pass_counts':{c:sum(s.get('components',{}).get(c) is True for s in subset) for c in COMPONENTS},
            'component_note':'Future is supplied-patch validation, not generated model capability. No artifact contributes no passes.',
            'trace_calls':sum(t.get('action')=='trace' for r in mr for t in r.get('turns',[])),
            'attempts_using_trace':sum(any(t.get('action')=='trace' for t in r.get('turns',[])) for r in mr),
            'protocol_errors':sum(t.get('error_category')=='protocol' for r in mr for t in r.get('turns',[])),
            'output_tokens':sum(r.get('generated_tokens',0) for r in mr),
            'wall_seconds_including_partial_runs':sum(r.get('wall_seconds',0) for r in mr)}
    index={(s['id'],s['method']):s for s in scores}
    for baseline,intervention in [('ordinary','checklist'),('ordinary','provenance'),('checklist','provenance')]:
        pairs=[];excluded=[]
        for ident in roster:
            a=index[ident,baseline];b=index[ident,intervention]
            if a['complete'] is None or b['complete'] is None:excluded.append(ident)
            else:pairs.append((ident,int(b['complete'])-int(a['complete'])))
        family_differences={f:([d for i,d in pairs if roster[i]['family']==f]) for f in plan['families']}
        summary['paired_contrasts'][intervention+'-minus-'+baseline]=dict(
            role='primary' if intervention=='checklist' and baseline=='ordinary' else 'exploratory',
            paired_cases=len(pairs),excluded_case_ids=excluded,
            intervention_only_successes=sum(d==1 for _,d in pairs),baseline_only_successes=sum(d==-1 for _,d in pairs),
            ties=sum(d==0 for _,d in pairs),rate_difference=sum(d for _,d in pairs)/len(pairs) if pairs else None,
            family_differences={f:sum(ds)/len(ds) if ds else None for f,ds in family_differences.items()},
            family_macro_difference=sum(sum(ds)/len(ds) for ds in family_differences.values())/len(family_differences) if not excluded else None)
    return scores,summary
