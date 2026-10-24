"""Private v3 grading with post-recovery continuation; never imported by worker."""
import copy
from .heldout_cases import IMPLEMENTED,build,future_fixture
from .engine import materialize,run_sql,snapshot
from .grade import equal

COMPONENTS=('historical','preservation','repeatable','healthy_control','future','continuation')


def projections_equal(state,expected):
    return all(equal(state[table],rows) for table,rows in expected.items())


def future_check(task,expected,patch):
    db=materialize(task)
    before=snapshot(db,task)
    try:
        run_sql(db,task,patch);once=snapshot(db,task)
        run_sql(db,task,patch)
        return (projections_equal(once,expected) and once==snapshot(db,task)
                and all(before[t]==once[t] for t in task['immutable_tables']))
    finally:db.close()


def grade(case_id,artifact,seeds=(0,7,19)):
    checks=[];repair=artifact.get('recovery_sql','')
    for seed in seeds:
        task,p=build(case_id,seed);db=materialize(task);before=snapshot(db,task)
        check={'seed':seed,'sql_executed':False,'fixed_patch_unchanged':artifact.get('application_sql')==task['application_sql'],
               **{c:False for c in COMPONENTS}}
        once=None
        try:
            first=run_sql(db,task,repair);once=snapshot(db,task);check['sql_executed']=True
            check['historical']=projections_equal(once,p['expected'])
            protected={t:[r for r in before[t] if r in expected] for t,expected in p['expected'].items()}
            check['preservation']=(all(before[t]==once[t] for t in task['immutable_tables']) and
                                   all(r in once[t] for t,rows in protected.items() for r in rows))
            repeat=run_sql(db,task,repair)
            check['repeatable']=once==snapshot(db,task)
            check.update(rows_written_first=first['rows_written'],rows_written_repeat=repeat['rows_written'])
        except Exception as exc:check['recovery_error']=str(exc)
        finally:db.close()
        healthy,_=build(case_id,seed,healthy=True);db=materialize(healthy);initial=snapshot(db,healthy)
        try:
            run_sql(db,healthy,repair);check['healthy_control']=snapshot(db,healthy)==initial
        except Exception as exc:check['healthy_error']=str(exc)
        finally:db.close()
        future,expected_future=future_fixture(case_id,seed)
        try:
            check['future']=check['fixed_patch_unchanged'] and future_check(future,expected_future,task['application_sql'])
        except Exception as exc:check['future_error']=str(exc)
        if once is not None:
            continued=copy.deepcopy(task)
            continued['tables']=copy.deepcopy(once)
            # Host supplies genuinely new evidence; it is not recovery-authored SQL.
            continued['tables'].update(copy.deepcopy(p['future_inputs']))
            try:
                check['continuation']=check['fixed_patch_unchanged'] and future_check(continued,expected_future,task['application_sql'])
            except Exception as exc:check['continuation_error']=str(exc)
        check['complete']=all(check[c] for c in COMPONENTS)
        checks.append(check)
    executed=all(c['sql_executed'] for c in checks)
    complete=all(c['complete'] for c in checks)
    return dict(id=case_id,family=build(case_id)[0]['family'],grading_version='afterfix-heldout-grader-v3',
                complete=complete,sql_executed=executed,variants=checks,
                outcome='complete' if complete else 'executable_but_wrong' if executed else 'sql_execution_failure',
                components={c:all(v[c] for v in checks) for c in COMPONENTS})


def mutations(task,private):
    """Independent negative artifacts, including protected-row damage and additive drift."""
    controls={'no_op':'SELECT 1;','patch_only':task['application_sql'],
              'empty_projection':' '.join(f'DELETE FROM {t};' for t in task['writable_tables']),
              **private['negative_controls']}
    # Introspect schema only to choose a non-key numeric counter and a protected row.
    db=materialize(task)
    try:
        for table,expected in private['expected'].items():
            info=list(db.execute(f'PRAGMA table_info({table})'))
            nonkeys=[(i,r[1],r[2]) for i,r in enumerate(info) if r[1] not in private['projection_keys'][table]]
            protected=next((r for r in task['tables'][table] if r in expected),None)
            if protected and 'collateral_mutation' not in controls and nonkeys:
                index,column,typ=nonkeys[0]
                value=column+'+1' if typ=='INTEGER' else "'invalid_control_state'"
                controls['collateral_mutation']=private['reference_recovery']+f' UPDATE {table} SET {column}={value};'
            numeric=next(((i,c) for i,c,t in nonkeys if t=='INTEGER'),None)
            if numeric and 'additive_drift' not in controls:
                controls['additive_drift']=f'UPDATE {table} SET {numeric[1]}={numeric[1]}+1;'
    finally:db.close()
    return controls


def validate_suite(case_ids=IMPLEMENTED):
    report=[]
    for case_id in case_ids:
        task,p=build(case_id);artifact={'application_sql':task['application_sql'],'recovery_sql':p['reference_recovery']}
        reference=grade(case_id,artifact);assert reference['complete'],(case_id,'reference',reference)
        alternate=grade(case_id,dict(artifact,recovery_sql=p['alternative_recovery']))
        assert alternate['complete'],(case_id,'alternative',alternate)
        negatives={name:grade(case_id,dict(artifact,recovery_sql=sql)) for name,sql in mutations(task,p).items()}
        assert all(result['sql_executed'] for result in negatives.values()),(case_id,'non-executable negative control')
        assert all(not result['complete'] for result in negatives.values()),(case_id,'accepted negative',negatives)
        assert not negatives['no_op']['components']['historical']
        assert not negatives['patch_only']['components']['historical']
        assert not negatives['collateral_mutation']['components']['preservation']
        assert not negatives['additive_drift']['components']['repeatable']
        assert all(s['components']['future'] for s in negatives.values()),'Supplied patch must be independently correct'
        # Admit only cases with genuine new-work changes and healthy unrelated controls.
        for seed in (0,7,19):
            healthy,hp=build(case_id,seed,healthy=True);future,expected=future_fixture(case_id,seed)
            assert not projections_equal(healthy['tables'],expected),(case_id,'future fixture is a no-op')
            assert any(r in hp['expected'][t] for t in hp['expected'] for r in build(case_id,seed)[0]['tables'][t])
        report.append(dict(id=case_id,family=task['family'],reference=reference,alternative=alternate,
                           negative_controls=negatives,model_runs=0))
    return report
