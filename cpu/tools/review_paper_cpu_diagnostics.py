"""Post hoc reviewer diagnostics; public-only candidate construction, frozen grading."""
import argparse
import hashlib
import json
import pathlib
import re
import sys

ROOT=pathlib.Path(__file__).resolve().parents[1]
OUT=ROOT/'results/paper-review-v1'
PUBLIC=ROOT/'results/deep-v3-gpu/deep-results/public-incidents.json'
PATTERN=r'\s+(?:WHERE|AND)\s+[A-Za-z_]\w*(?:\.[A-Za-z_]\w*)?\s+IN\s*\(\s*SELECT\s+entity\s+FROM\s+work\s*\)'

def read(p):return json.loads(p.read_text(encoding='utf-8'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(name,data):(OUT/name).write_text(json.dumps(data,indent=2)+'\n',encoding='utf-8')

def prepare():
    OUT.mkdir(exist_ok=True)
    path=OUT/'public-candidates.json'
    if path.exists():raise RuntimeError('Refusing to overwrite constructed candidates')
    rows=[]
    for task in read(PUBLIC):
        sql,n=re.subn(PATTERN,'',task['application_sql'],flags=re.I)
        rows.append(dict(id=task['id'],family=task['family'],removed_clauses=n,
            immutable_tables=task['immutable_tables'],append_only_tables=task['append_only_tables'],
            work_initial_rows=len(task['tables']['work']),
            artifact=dict(application_sql=task['application_sql'],recovery_sql=sql)))
    save('public-candidates.json',dict(public_source_sha256=sha(PUBLIC),pattern=PATTERN,
        plan_sha256=sha(ROOT/'paper/review-scope-diagnostic-plan.md'),cases=rows,
        origin='Post hoc rule chosen after inspecting public patch structure and prior model outcomes; no private grading used in construction'))
    print(json.dumps(dict(prepared=len(rows),candidate_sha256=sha(path),removed_clauses=[r['removed_clauses'] for r in rows])))

def evaluate():
    # Private modules enter only after every public candidate has been saved.
    bundle=read(OUT/'public-candidates.json')
    assert sha(PUBLIC)==bundle['public_source_sha256']
    assert sha(ROOT/'paper/review-scope-diagnostic-plan.md')==bundle['plan_sha256']
    sys.path.insert(0,str(ROOT/'experiments/deep-v3'))
    from afterfix.heldout_grade import grade
    rows=[]
    for row in bundle['cases']:
        artifact=row['artifact']
        rows.append(dict(id=row['id'],family=row['family'],removed_clauses=row['removed_clauses'],
            scope_adaptation=grade(row['id'],artifact),
            patch_only=grade(row['id'],dict(artifact,recovery_sql=artifact['application_sql'])),
            no_op=grade(row['id'],dict(artifact,recovery_sql='SELECT 1;'))))
    metrics={}
    for key,source in [('original','results/heldout-full-evaluation/grades.json'),('v3','results/deep-v3-analysis/grades.json')]:
        grades=read(ROOT/source)
        executable=[g for g in grades if g['outcome'] in ('complete','executable_but_wrong')]
        metrics[key]=dict(attempts=len(grades),executables=len(executable),
            executable_stable=sum(g['components']['repeatable'] for g in executable),
            historical_pass_but_not_full=[dict(id=g['id'],method=g['method'],model=g.get('model'))
                for g in grades if g.get('components',{}).get('historical') and not g['complete']],
            executable_wrong=sum(g['outcome']=='executable_but_wrong' for g in executable))
    summary=dict(post_hoc=True,gpu_jobs_started=0,cases=len(rows),seeds=[0,7,19],
        candidate_sha256=sha(OUT/'public-candidates.json'),
        candidates={name:dict(full=sum(r[name]['complete'] for r in rows),
            executable=sum(r[name]['sql_executed'] for r in rows),
            stable=sum(r[name]['components']['repeatable'] for r in rows))
            for name in ('scope_adaptation','patch_only','no_op')},metric_overlap=metrics)
    save('grades.json',rows);save('summary.json',summary)
    print(json.dumps(summary,indent=2))

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('phase',choices=['prepare','evaluate']);args=parser.parse_args()
    {'prepare':prepare,'evaluate':evaluate}[args.phase]()
