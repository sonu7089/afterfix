"""Private independent grading. Not imported by the model worker."""
from .cases import build, KINDS
from .engine import materialize, run_sql, snapshot


def equal(actual, expected):
    return sorted(actual,key=repr)==sorted(expected,key=repr)


def grade(kind, artifact, seeds=(0,7,19)):
    checks=[]
    app=artifact.get('application_sql','');repair=artifact.get('recovery_sql','')
    for seed in seeds:
        task,private=build(kind,seed)
        expected=private['expected'];db=materialize(task)
        before=snapshot(db,task)
        c={'seed':seed,'historical':False,'preservation':False,'repeatable':False,'future':False,'healthy_control':False}
        try:
            first=run_sql(db,task,repair);once=snapshot(db,task)
            c['historical']=all(equal(once[t],v) for t,v in expected.items())
            immutable_ok=all(once[t]==before[t] for t in task['immutable_tables'])
            # Any initially correct full row must remain present, including legitimate later activity.
            protected={t:[r for r in before[t] if r in expected[t]] for t in task['writable_tables']}
            c['preservation']=immutable_ok and all(all(r in once[t] for r in rs) for t,rs in protected.items())
            again=run_sql(db,task,repair)
            c['repeatable']=snapshot(db,task)==once
            c['rows_written_first']=first['rows_written'];c['rows_written_repeat']=again['rows_written']
        except Exception as e:c['recovery_error']=str(e)
        finally:db.close()
        # Future processing from a clean projection state, on perturbed inputs, twice.
        db=materialize(task)
        for t in task['writable_tables']:db.execute(f'DELETE FROM "{t}"')
        if kind=='inventory':db.execute('INSERT INTO stock SELECT * FROM opening')
        db.commit()
        try:
            run_sql(db,task,app);future=snapshot(db,task)
            run_sql(db,task,app)
            c['future']=all(equal(future[t],v) for t,v in expected.items()) and snapshot(db,task)==future
        except Exception as e:c['future_error']=str(e)
        finally:db.close()
        healthy,_=build(kind,seed,healthy=True);db=materialize(healthy);before=snapshot(db,healthy)
        try:
            run_sql(db,healthy,repair);c['healthy_control']=snapshot(db,healthy)==before
        except Exception as e:c['healthy_error']=str(e)
        finally:db.close()
        c['complete']=all(c[k] for k in ('historical','preservation','repeatable','future','healthy_control'))
        checks.append(c)
    return {'id':kind,'complete':all(c['complete'] for c in checks),'variants':checks,
            'components':{k:all(c[k] for c in checks) for k in ('historical','preservation','repeatable','future','healthy_control')}}


def validate_suite():
    """Admission checks against independent Python oracles and targeted wrong repairs."""
    report=[]
    for kind in KINDS:
        task,p=build(kind)
        reference={'application_sql':p['reference_application'],'recovery_sql':p['reference_recovery']}
        good=grade(kind,reference)
        assert good['complete'],(kind,'reference',good)
        source_only=grade(kind,dict(reference,recovery_sql='SELECT 1;'))
        assert not source_only['components']['historical'],(kind,'source-only should leave damage')
        state_only=grade(kind,dict(reference,application_sql=task['application_sql']))
        assert state_only['components']['historical'] and not state_only['components']['future'],(kind,'broken future code accepted')
        empty=grade(kind,dict(reference,recovery_sql='\n'.join('DELETE FROM '+t+';' for t in task['writable_tables'])))
        assert not empty['components']['historical'],(kind,'empty projection accepted')
        # Deliberately additive repair must be rejected on repeat, even if it fixes the first snapshot.
        t=next(t for t in task['writable_tables'] if t!='applied')
        if kind=='cdc':
            nonrepeat=p['reference_recovery']+" INSERT INTO catalog VALUES ('bad','extra','extra');"
        else:
            column='qty' if kind=='inventory' else 'cents'
            nonrepeat=f'UPDATE {t} SET {column}={column}+1;'
        rejected=grade(kind,dict(reference,recovery_sql=nonrepeat))
        assert not rejected['complete'],(kind,'wrong repair accepted')
        # A correct but differently structured implementation should pass.
        alternate='\n'.join('DELETE FROM '+t+';' for t in task['writable_tables'])+'\n'+p['reference_application']
        assert grade(kind,dict(reference,recovery_sql=alternate))['complete'],(kind,'alternative rejected')
        # Immutable source writes and filesystem attachment must be blocked by tools.
        for sql in [f'DELETE FROM {task["immutable_tables"][0]};',"ATTACH DATABASE '/tmp/afterfix-forbidden.db' AS other;",
                    'PRAGMA writable_schema=ON;', 'CREATE TABLE forbidden(x);']:
            db=materialize(task)
            try:
                try:run_sql(db,task,sql)
                except Exception:pass
                else:raise AssertionError((kind,'forbidden SQL accepted',sql))
            finally:db.close()
        report.append({'id':kind,'reference_passed':True,'source_only_rejected':True,'state_only_rejected':True,'empty_recovery_rejected':True,
                       'incorrect_recovery_rejected':True,'alternative_passed':True,'tool_boundary_passed':True,
                       'oracle_variants':3})
    return report


if __name__=='__main__':
    import json
    print(json.dumps(validate_suite(),indent=2))
