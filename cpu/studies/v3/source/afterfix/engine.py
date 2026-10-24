"""Public SQLite-only tool boundary. No shell, filesystem, network, or hidden checks."""
import json
import sqlite3
import time


def materialize(task):
    db=sqlite3.connect(':memory:')
    db.executescript(task['schema'])
    for table, values in task['tables'].items():
        if values:
            db.executemany(f'INSERT INTO "{table}" VALUES ({",".join("?" for _ in values[0])})',values)
    db.commit()
    # Host-owned guards also catch SQLite REPLACE's implicit deletion, which may
    # not produce an authorizer DELETE callback. Agents cannot disable triggers.
    db.execute('PRAGMA recursive_triggers=ON')
    for table in task.get('append_only_tables', []):
        if table not in task['writable_tables'] or not table.replace('_','').isalnum():
            raise ValueError('Invalid append-only policy')
        for operation in ('DELETE','UPDATE'):
            db.execute(f'''CREATE TRIGGER "afterfix_{table}_{operation}" BEFORE {operation} ON "{table}"
                BEGIN SELECT RAISE(ABORT, 'append-only policy violation'); END''')
    return db


def snapshot(db, task):
    return {t:sorted([list(r) for r in db.execute(f'SELECT * FROM "{t}"')],key=repr) for t in task['tables']}


def run_sql(db, task, sql, readonly=False):
    if not isinstance(sql,str) or not sql.strip() or len(sql)>24000:
        raise ValueError('SQL must be a nonempty string of at most 24000 characters')
    writable=set() if readonly else set(task['writable_tables'])
    readable=set(task['tables'])
    def auth(action,a,b,database,trigger):
        if action==sqlite3.SQLITE_READ:
            # SQLite may omit database/column for a table-only read, e.g.
            # EXISTS(SELECT 1 FROM an_allowed_table). Keep the exception narrow.
            allowed_database = database == 'main' or (database is None and b == '')
            return sqlite3.SQLITE_OK if allowed_database and a in readable else sqlite3.SQLITE_DENY
        if action in (sqlite3.SQLITE_INSERT,sqlite3.SQLITE_UPDATE,sqlite3.SQLITE_DELETE):
            if a in task.get('append_only_tables', []) and action != sqlite3.SQLITE_INSERT:
                return sqlite3.SQLITE_DENY
            return sqlite3.SQLITE_OK if database=='main' and a in writable else sqlite3.SQLITE_DENY
        if action==sqlite3.SQLITE_FUNCTION:
            return sqlite3.SQLITE_DENY if (b or '').lower() in {'load_extension','readfile','writefile','eval'} else sqlite3.SQLITE_OK
        if action in (sqlite3.SQLITE_SELECT,sqlite3.SQLITE_RECURSIVE):return sqlite3.SQLITE_OK
        return sqlite3.SQLITE_DENY
    statements=[]; pending=''
    for char in sql:
        pending+=char
        if char==';' and sqlite3.complete_statement(pending):statements.append(pending);pending=''
    if pending.strip():statements.append(pending)
    deadline=time.monotonic()+2
    def progress():return int(time.monotonic()>deadline)
    changes=db.total_changes
    # Transaction control belongs to the host, not submitted SQL.
    db.execute('BEGIN')
    db.set_authorizer(auth);db.set_progress_handler(progress,1000)
    output=[]
    try:
        for statement in statements:
            cursor=db.execute(statement)
            if cursor.description:
                data=cursor.fetchmany(31)
                output.append({'columns':[c[0] for c in cursor.description],'rows':data[:30],'truncated':len(data)>30})
        db.set_authorizer(None);db.set_progress_handler(None,0);db.commit()
    except Exception:
        db.set_authorizer(None);db.set_progress_handler(None,0);db.rollback();raise
    return {'results':output,'rows_written':db.total_changes-changes}


def public_check(task, application_sql, recovery_sql):
    """Feedback checks only visible snapshot repeatability and SQL execution, not gold state."""
    db=materialize(task)
    try:
        first=run_sql(db,task,recovery_sql);s1=snapshot(db,task)
        second=run_sql(db,task,recovery_sql);s2=snapshot(db,task)
        run_sql(db,task,application_sql)
        return {'sql_executed':True,'recovery_repeat_state_stable':s1==s2,
                'first_rows_written':first['rows_written'],'repeat_rows_written':second['rows_written'],
                'recovered_tables':{t:s1[t] for t in task['writable_tables']},
                'note':'No hidden correctness feedback. State stability does not imply zero writes.'}
    except Exception as e:return {'sql_executed':False,'error':str(e)}
    finally:db.close()


def parse_action(text):
    """Compatibility entry point; protocol.py owns action validation."""
    from .protocol import parse_response
    return parse_response(text, 'ordinary')[0]
