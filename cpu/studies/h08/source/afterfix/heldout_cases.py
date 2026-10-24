"""Private held-out builders. Do not import in a model worker or use for prompt tuning.

Full 24-case roster; the locked design is benchmark/plan-v1.json.
Python oracles below never execute the reference SQL.
"""
import copy

IMPLEMENTED = tuple(f'H{i:02d}' for i in range(1,25))


def definition(case_id, seed=0):
    n=lambda x: f'{x}_{seed}'
    q=seed%5
    if case_id=='H01':
        family='delivery_workflows'
        title='RelayDesk: acknowledged outbox messages returned to the retry queue'
        schema='''CREATE TABLE messages(id TEXT PRIMARY KEY,enabled INTEGER,body TEXT);
CREATE TABLE receipts(id TEXT PRIMARY KEY,message TEXT,result TEXT,attempt INTEGER);
CREATE TABLE work(entity TEXT PRIMARY KEY);
CREATE TABLE outbox(id TEXT PRIMARY KEY,state TEXT,attempts INTEGER);'''
        tables={'messages':[[n('m1'),1,'invoice notice'],[n('m2'),1,'delivery notice'],[n('m3'),0,'canceled reminder'],[n('m4'),1,'address rejected'],[n('m5'),1,'healthy notice']],
                'receipts':[[n('r1'),n('m1'),'accepted',1],[n('r2'),n('m1'),'retry',2],
                            [n('r3'),n('m2'),'retry',1],[n('r4'),n('m4'),'permanent',1],[n('r5'),n('m5'),'accepted',1]],'work':[]}
        queries={'outbox':'''SELECT m.id,CASE WHEN EXISTS(SELECT 1 FROM receipts r WHERE r.message=m.id AND r.result='accepted') THEN 'delivered'
WHEN m.enabled=0 THEN 'canceled' WHEN EXISTS(SELECT 1 FROM receipts r WHERE r.message=m.id AND r.result='permanent') THEN 'failed' ELSE 'pending' END,
COALESCE((SELECT MAX(attempt) FROM receipts r WHERE r.message=m.id),0) FROM messages m'''}
        keys={'outbox':['id']}
        patch="DELETE FROM outbox WHERE id IN (SELECT entity FROM work); INSERT INTO outbox "+queries['outbox']+" WHERE m.id IN (SELECT entity FROM work);"
        spec=('Every message has one outbox row. Any accepted receipt means delivered, even if a later transport retry was logged or the message was disabled. '
              'Otherwise disabled messages are canceled; otherwise any permanent receipt means failed; otherwise pending. attempts is the maximum recorded attempt number, or zero. '
              'Receipts are authoritative acknowledgements, not requests to resend. Never erase them. Reconstructing a delivered message as pending can cause duplicate delivery. '
              'The patch refreshes only message IDs in work, the immutable current change-feed batch. Historical messages are absent from work.')
        evidence=['An outbox rehydration used the last transport outcome and lost an earlier acknowledgement.',
                  'messages + receipts -> outbox; work -> outbox',
                  'A disabled reminder and an unrelated delivered notice are legitimate controls. A late retry does not undo delivery.']
        future={'receipts':tables['receipts']+[[n('r6'),n('m2'),'accepted',2]],
                'messages':tables['messages']+[[n('m6'),1,'new notice']], 'work':[[n('m2')],[n('m6')]]}
        wrong={'latest_transport_wins':"UPDATE outbox SET state=COALESCE((SELECT CASE result WHEN 'accepted' THEN 'delivered' WHEN 'permanent' THEN 'failed' ELSE 'pending' END FROM receipts WHERE message=outbox.id ORDER BY attempt DESC LIMIT 1),state);",
               'all_pending':"UPDATE outbox SET state='pending';"}
    elif case_id=='H05':
        family='coupled_resources';title='PackForge: one component of a committed kit reservation disappeared'
        schema='''CREATE TABLE inventory(sku TEXT PRIMARY KEY,total INTEGER);
CREATE TABLE bundles(id TEXT PRIMARY KEY,status TEXT);
CREATE TABLE parts(bundle TEXT,sku TEXT,units INTEGER,PRIMARY KEY(bundle,sku));
CREATE TABLE work(entity TEXT PRIMARY KEY);
CREATE TABLE allocations(bundle TEXT,sku TEXT,qty INTEGER,PRIMARY KEY(bundle,sku));
CREATE TABLE available(sku TEXT PRIMARY KEY,qty INTEGER);'''
        tables={'inventory':[[n('a'),30+q],[n('b'),20+q],[n('c'),15+q]],
                'bundles':[[n('kit1'),'committed'],[n('kit2'),'released'],[n('kit3'),'committed']],
                'parts':[[n('kit1'),n('a'),3+q],[n('kit1'),n('b'),2],[n('kit2'),n('a'),4],
                         [n('kit2'),n('c'),1],[n('kit3'),n('a'),2],[n('kit3'),n('c'),3]],'work':[]}
        queries={'allocations':"SELECT p.bundle,p.sku,p.units FROM parts p JOIN bundles b ON b.id=p.bundle WHERE b.status='committed'",
                 'available':"SELECT i.sku,i.total-COALESCE((SELECT SUM(a.qty) FROM allocations a WHERE a.sku=i.sku),0) FROM inventory i"}
        keys={'allocations':['bundle','sku'],'available':['sku']}
        patch="DELETE FROM allocations WHERE bundle IN (SELECT entity FROM work); INSERT INTO allocations "+queries['allocations']+" AND b.id IN (SELECT entity FROM work); DELETE FROM available; INSERT INTO available "+queries['available']+';'
        spec=('A committed bundle reserves exactly the units of every component listed in parts. A released bundle reserves nothing. '
              'allocations has one row per committed (bundle,sku), not a partial kit or a merged SKU total. available equals inventory.total minus all allocations per SKU. '
              'All recorded commitments fit capacity. Releases are legitimate later activity and must not be reversed. '
              'The fixed patch updates allocations only for changed bundle IDs in work, then refreshes global available quantities.')
        evidence=['A per-component retry left a half-reserved kit; another kit was legitimately released later.',
                  'bundles + parts -> allocations; inventory + allocations -> available; work -> allocations',
                  'Two committed bundles share a component; repairing only its aggregate does not restore each bundle obligation.']
        future={'bundles':[[i,'released' if i==n('kit1') else s] for i,s in tables['bundles']]+[[n('kit4'),'committed']],
                'parts':tables['parts']+[[n('kit4'),n('b'),1+q],[n('kit4'),n('c'),2]],'work':[[n('kit1')],[n('kit4')]]}
        wrong={'reserve_released_bundles':'DELETE FROM allocations; INSERT INTO allocations SELECT bundle,sku,units FROM parts;',
               'repair_only_aggregate':"DELETE FROM available; INSERT INTO available "+queries['available']+';'}
    elif case_id=='H09':
        family='versioned_storage';title='LakeSpan: an index mixed obsolete and unpublished snapshot files'
        schema='''CREATE TABLE snapshots(id TEXT PRIMARY KEY,dataset TEXT,status TEXT);
CREATE TABLE heads(dataset TEXT PRIMARY KEY,snapshot TEXT);
CREATE TABLE members(snapshot TEXT,file TEXT,PRIMARY KEY(snapshot,file));
CREATE TABLE files(id TEXT PRIMARY KEY,rows INTEGER);
CREATE TABLE work(entity TEXT PRIMARY KEY);
CREATE TABLE active_files(dataset TEXT,file TEXT,rows INTEGER,PRIMARY KEY(dataset,file));
CREATE TABLE dataset_totals(dataset TEXT PRIMARY KEY,rows INTEGER);'''
        tables={'snapshots':[[n('old'),n('sales'),'committed'],[n('current'),n('sales'),'committed'],[n('stage'),n('sales'),'staged'],[n('other'),n('returns'),'committed']],
                'heads':[[n('sales'),n('current')],[n('returns'),n('other')]],
                'members':[[n('old'),n('f0')],[n('current'),n('f1')],[n('current'),n('shared')],
                           [n('stage'),n('f2')],[n('other'),n('shared')]],
                'files':[[n('f0'),8+q],[n('f1'),10+q],[n('shared'),10+q],[n('f2'),25+q]],'work':[]}
        queries={'active_files':"SELECT h.dataset,f.id,f.rows FROM heads h JOIN snapshots s ON s.id=h.snapshot AND s.dataset=h.dataset AND s.status='committed' JOIN members m ON m.snapshot=s.id JOIN files f ON f.id=m.file",
                 'dataset_totals':"SELECT h.dataset,COALESCE((SELECT SUM(a.rows) FROM active_files a WHERE a.dataset=h.dataset),0) FROM heads h"}
        keys={'active_files':['dataset','file'],'dataset_totals':['dataset']}
        patch="DELETE FROM active_files WHERE dataset IN (SELECT entity FROM work); INSERT INTO active_files "+queries['active_files']+" WHERE h.dataset IN (SELECT entity FROM work); DELETE FROM dataset_totals; INSERT INTO dataset_totals "+queries['dataset_totals']+';'
        spec=('heads identifies the authoritative published snapshot for each dataset; heads always points to a committed snapshot belonging to that dataset. '
              'Only that snapshot membership determines active_files. Older committed snapshots and staged unpublished snapshots contribute nothing. '
              'The same file may belong to different datasets; distinct files with equal row counts must both count. dataset_totals includes every head, including zero-file snapshots. '
              'The patch refreshes only dataset IDs in work after a publication, then recomputes dataset_totals.')
        evidence=['A maintenance index unioned every snapshot membership and accidentally included a staging manifest.',
                  'heads + snapshots + members + files -> active_files -> dataset_totals; work -> active_files',
                  'A second dataset legitimately uses the shared file; physical-file deduplication across datasets would lose its rows.']
        future={'snapshots':tables['snapshots']+[[n('next'),n('sales'),'committed'],[n('empty'),n('emptyset'),'committed']],
                'heads':[[n('sales'),n('next')],[n('returns'),n('other')],[n('emptyset'),n('empty')]],
                'members':tables['members']+[[n('next'),n('f2')]],'work':[[n('sales')],[n('emptyset')]]}
        wrong={'all_snapshots':"DELETE FROM active_files; INSERT OR IGNORE INTO active_files SELECT s.dataset,f.id,f.rows FROM snapshots s JOIN members m ON m.snapshot=s.id JOIN files f ON f.id=m.file;",
               'distinct_counts':"DELETE FROM dataset_totals; INSERT INTO dataset_totals SELECT dataset,SUM(DISTINCT rows) FROM active_files GROUP BY dataset;"}
    elif case_id=='H13':
        family='authorization_graphs';title='AccessHarbor: stale effective grants after inherited-role changes'
        schema='''CREATE TABLE users(id TEXT PRIMARY KEY);
CREATE TABLE memberships(user TEXT,role TEXT,PRIMARY KEY(user,role));
CREATE TABLE role_edges(child TEXT,parent TEXT,PRIMARY KEY(child,parent));
CREATE TABLE grants(role TEXT,resource TEXT,enabled INTEGER,PRIMARY KEY(role,resource));
CREATE TABLE denies(user TEXT,resource TEXT,PRIMARY KEY(user,resource));
CREATE TABLE work(entity TEXT PRIMARY KEY);
CREATE TABLE effective_access(user TEXT,resource TEXT,PRIMARY KEY(user,resource));
CREATE TABLE access_counts(user TEXT PRIMARY KEY,n INTEGER);'''
        tables={'users':[[n(x)] for x in ['ana','bo','cy','di']],
                'memberships':[[n('ana'),n('lead')],[n('bo'),n('viewer')],[n('cy'),n('lead')]],
                'role_edges':[[n('lead'),n('analyst')],[n('analyst'),n('viewer')],[n('lead'),n('viewer')]],
                'grants':[[n('viewer'),n('read'),1],[n('analyst'),n('export'),1],[n('lead'),n('admin'),0]],
                'denies':[[n('ana'),n('export')]],'work':[]}
        cte='''WITH RECURSIVE reach(user,role) AS (SELECT user,role FROM memberships UNION
SELECT r.user,e.parent FROM reach r JOIN role_edges e ON e.child=r.role) '''
        queries={'effective_access':cte+"SELECT DISTINCT r.user,g.resource FROM reach r JOIN grants g ON g.role=r.role WHERE g.enabled=1 AND NOT EXISTS(SELECT 1 FROM denies d WHERE d.user=r.user AND d.resource=g.resource)",
                 'access_counts':"SELECT u.id,(SELECT COUNT(*) FROM effective_access a WHERE a.user=u.id) FROM users u"}
        keys={'effective_access':['user','resource'],'access_counts':['user']}
        patch="DELETE FROM effective_access WHERE user IN (SELECT entity FROM work); INSERT INTO effective_access "+queries['effective_access']+" AND r.user IN (SELECT entity FROM work); DELETE FROM access_counts; INSERT INTO access_counts "+queries['access_counts']+';'
        spec=('The role graph is a finite DAG. A user receives enabled grants on every directly assigned role and every transitively inherited parent. '
              'An explicit (user,resource) deny overrides every path. Disabled grants never authorize access; multiple paths produce one access row. '
              'access_counts includes users with zero access. The fixed patch refreshes only users listed in work; the change-feed expands affected users before invoking it. '
              'Preserve the legitimate explicit deny and grants through independent inheritance paths.')
        evidence=['A stale effective-access cache retained a denied export and omitted grants reachable through a parent role.',
                  'memberships + role_edges + grants + denies -> effective_access -> access_counts; work -> effective_access',
                  'The diamond inheritance has two paths to viewer; the later explicit deny applies only to one user.']
        future={'memberships':tables['memberships']+[[n('di'),n('viewer')]],
                'denies':tables['denies']+[[n('cy'),n('export')]],'work':[[n('di')],[n('cy')]]}
        wrong={'direct_only':"DELETE FROM effective_access; INSERT OR IGNORE INTO effective_access SELECT m.user,g.resource FROM memberships m JOIN grants g ON g.role=m.role WHERE g.enabled=1;"}
        wrong['ignore_denies']="DELETE FROM effective_access; INSERT INTO effective_access "+queries['effective_access'].split(' AND NOT EXISTS')[0]+';'
    elif case_id=='H17':
        family='ordered_state';title='GaugeLine: a late meter correction was added instead of replacing the prior reading'
        schema='''CREATE TABLE meters(id TEXT PRIMARY KEY,opening INTEGER);
CREATE TABLE commands(id TEXT PRIMARY KEY,meter TEXT,seq INTEGER,kind TEXT,amount INTEGER,arrival INTEGER,UNIQUE(meter,seq));
CREATE TABLE work(entity TEXT PRIMARY KEY);
CREATE TABLE readings(meter TEXT PRIMARY KEY,value INTEGER,last_seq INTEGER);'''
        tables={'meters':[[n('east'),10+q],[n('west'),20+q],[n('idle'),3+q]],
                'commands':[[n('c1'),n('east'),1,'ADD',5,1],[n('c2'),n('east'),2,'SET',40+q,5],
                            [n('c3'),n('east'),3,'ADD',-3,2],[n('c4'),n('east'),4,'SET',12+q,4],
                            [n('c5'),n('east'),5,'ADD',2,3],[n('c6'),n('west'),1,'ADD',4,1]],'work':[]}
        queries={'readings':'''SELECT m.id,COALESCE((SELECT amount FROM commands c WHERE c.meter=m.id AND c.kind='SET' ORDER BY seq DESC LIMIT 1),m.opening)+
COALESCE((SELECT SUM(amount) FROM commands c WHERE c.meter=m.id AND c.kind='ADD' AND c.seq>COALESCE((SELECT MAX(seq) FROM commands s WHERE s.meter=m.id AND s.kind='SET'),0)),0),
COALESCE((SELECT MAX(seq) FROM commands c WHERE c.meter=m.id),0) FROM meters m'''}
        keys={'readings':['meter']}
        patch="DELETE FROM readings WHERE meter IN (SELECT entity FROM work); INSERT INTO readings "+queries['readings']+" WHERE m.id IN (SELECT entity FROM work);"
        spec=('For each meter start at opening and process commands in increasing authoritative seq, not arrival order. SET replaces the whole current value; ADD adds a signed amount. '
              'seq is positive and unique within a meter. readings has one row per meter, value after all commands, and last_seq equal to max seq or zero for no commands. '
              'An older correction may arrive after later commands; later SET and ADD effects must still survive in authoritative order. '
              'The patch refreshes only changed meter IDs in work; all earlier readings remain untouched unless explicitly recovered.')
        evidence=['The broken materializer treated SET as an additive delta and sorted correction arrivals rather than authoritative sequences.',
                  'meters + commands -> readings; work -> readings',
                  'The late SET at sequence 2 precedes the later SET at sequence 4, regardless of arrival time. An idle meter is a zero-event control.']
        future={'commands':tables['commands']+[[n('c7'),n('east'),6,'ADD',3,6],[n('c8'),n('idle'),1,'SET',9+q,1]],'work':[[n('east')],[n('idle')]]}
        wrong={'commutative_sum':"UPDATE readings SET value=(SELECT opening FROM meters WHERE id=readings.meter)+COALESCE((SELECT SUM(amount) FROM commands WHERE meter=readings.meter),0);",
               'arrival_latest_set':"UPDATE readings SET value=COALESCE((SELECT amount FROM commands WHERE meter=readings.meter AND kind='SET' ORDER BY arrival DESC LIMIT 1),value);"}
    elif case_id=='H21':
        family='evidence_adjudication';title='ClearBatch: a stale approval released an incomplete revised batch'
        schema='''CREATE TABLE batches(id TEXT PRIMARY KEY,revision INTEGER,expected_count INTEGER);
CREATE TABLE items(batch TEXT,revision INTEGER,id TEXT,payload TEXT,PRIMARY KEY(batch,revision,id));
CREATE TABLE reviews(batch TEXT,revision INTEGER,seq INTEGER,decision TEXT,PRIMARY KEY(batch,revision,seq));
CREATE TABLE holds(batch TEXT PRIMARY KEY,active INTEGER);
CREATE TABLE work(entity TEXT PRIMARY KEY);
CREATE TABLE releases(batch TEXT PRIMARY KEY,state TEXT,item_count INTEGER);'''
        tables={'batches':[[n('b1'),2,2],[n('b2'),1,1],[n('b3'),1,1],[n('b4'),1,1],[n('b5'),1,1]],
                'items':[[n('b1'),1,n('old'),'retired'],[n('b1'),2,n('a'),'current'],
                         [n('b2'),1,n('a'),'held'],[n('b3'),1,n('a'),'healthy'],[n('b5'),1,n('a'),'awaits new review']],
                'reviews':[[n('b1'),1,99,'allow'],[n('b1'),2,1,'deny'],[n('b2'),1,1,'allow'],
                           [n('b3'),1,1,'allow'],[n('b4'),1,1,'allow'],[n('b5'),1,1,'allow'],[n('b5'),1,2,'deny']],
                'holds':[[n('b2'),1]],'work':[]}
        queries={'releases':'''SELECT b.id,CASE WHEN EXISTS(SELECT 1 FROM holds h WHERE h.batch=b.id AND h.active=1) THEN 'held'
WHEN (SELECT COUNT(*) FROM items i WHERE i.batch=b.id AND i.revision=b.revision)=b.expected_count
AND (SELECT decision FROM reviews r WHERE r.batch=b.id AND r.revision=b.revision ORDER BY seq DESC LIMIT 1)='allow' THEN 'released' ELSE 'blocked' END,
(SELECT COUNT(*) FROM items i WHERE i.batch=b.id AND i.revision=b.revision) FROM batches b'''}
        keys={'releases':['batch']}
        patch="DELETE FROM releases WHERE batch IN (SELECT entity FROM work); INSERT INTO releases "+queries['releases']+" WHERE b.id IN (SELECT entity FROM work);"
        spec=('Every batch has one releases row. An active hold means held regardless of approvals. Otherwise release only when the number of items at the batch current revision equals expected_count '
              'and the highest-seq review at that same revision is allow; missing review or any other condition means blocked. item_count counts only current-revision items. '
              'Expected counts are positive; older items and reviews remain audit evidence, not current authorization. seq is comparable only within a batch revision. '
              'The patch refreshes batch IDs in work after new evidence arrives. Recovering history must retain later holds and denied re-reviews.')
        evidence=['An approval join ignored revision and admitted a revised batch using its retired approval; arrival totals hid an incomplete current revision.',
                  'batches + items + reviews + holds -> releases; work -> releases',
                  'An independently imposed hold overrides an approval. A complete healthy released batch is an unrelated control.']
        future={'items':tables['items']+[[n('b4'),1,n('new'),'arrived']],
                'holds':tables['holds']+[[n('b3'),1]],'work':[[n('b4')],[n('b3')]]}
        wrong={'approval_any_revision':"UPDATE releases SET state='released' WHERE EXISTS(SELECT 1 FROM reviews r WHERE r.batch=releases.batch AND r.decision='allow');",
               'count_all_revisions':"UPDATE releases SET item_count=(SELECT COUNT(*) FROM items i WHERE i.batch=releases.batch);"}
    else:
        from .heldout_remaining import definition as remaining_definition
        return remaining_definition(case_id,seed)
    return dict(id=case_id,family=family,title=title,schema=schema,tables=tables,queries=queries,keys=keys,
                patch=patch,spec=spec,evidence=evidence,future=future,wrong=wrong)


def oracle(case_id, tables):
    """Independent algorithms over input records; no SQLite/reference queries."""
    t=tables
    if case_id=='H01':
        result=[]
        for ident,enabled,_ in t['messages']:
            rs=[r for r in t['receipts'] if r[1]==ident];outcomes={r[2] for r in rs}
            state='delivered' if 'accepted' in outcomes else 'canceled' if not enabled else 'failed' if 'permanent' in outcomes else 'pending'
            result.append([ident,state,max((r[3] for r in rs),default=0)])
        return {'outbox':result}
    if case_id=='H05':
        active={i for i,s in t['bundles'] if s=='committed'}
        alloc=[list(p) for p in t['parts'] if p[0] in active]
        return {'allocations':alloc,'available':[[sku,total-sum(p[2] for p in alloc if p[1]==sku)] for sku,total in t['inventory']]}
    if case_id=='H09':
        snapshots={i:(dataset,status) for i,dataset,status in t['snapshots']};files=dict(t['files']);active=[]
        for dataset,snap in t['heads']:
            assert snapshots[snap]==(dataset,'committed')
            for member,file in t['members']:
                if member==snap:active.append([dataset,file,files[file]])
        return {'active_files':active,'dataset_totals':[[d,sum(r[2] for r in active if r[0]==d)] for d,_ in t['heads']]}
    if case_id=='H13':
        access=set();denied={tuple(r) for r in t['denies']}
        for (user,) in t['users']:
            frontier=[role for u,role in t['memberships'] if u==user];reached=set()
            while frontier:
                role=frontier.pop()
                if role in reached:continue
                reached.add(role);frontier.extend(parent for child,parent in t['role_edges'] if child==role)
            for role,resource,enabled in t['grants']:
                if enabled and role in reached and (user,resource) not in denied:access.add((user,resource))
        return {'effective_access':[list(r) for r in sorted(access)],'access_counts':[[u,sum(a==u for a,_ in access)] for (u,) in t['users']]}
    if case_id=='H17':
        result=[]
        for ident,opening in t['meters']:
            value=opening;last=0
            for _,meter,seq,kind,amount,_ in sorted(t['commands'],key=lambda r:r[2]):
                if meter==ident:
                    value=amount if kind=='SET' else value+amount;last=seq
            result.append([ident,value,last])
        return {'readings':result}
    if case_id=='H21':
        held={b for b,active in t['holds'] if active};result=[]
        for batch,rev,count in t['batches']:
            actual=sum(b==batch and v==rev for b,v,_,_ in t['items'])
            reviews=sorted((r for r in t['reviews'] if r[:2]==[batch,rev]),key=lambda r:r[2])
            allowed=bool(reviews) and reviews[-1][3]=='allow'
            state='held' if batch in held else 'released' if actual==count and allowed else 'blocked'
            result.append([batch,state,actual])
        return {'releases':result}
    from .heldout_remaining import oracle as remaining_oracle
    return remaining_oracle(case_id,tables)


def rebuild_sql(d):
    return '\n'.join(f'DELETE FROM {table}; INSERT INTO {table} {query};' for table,query in d['queries'].items())


def merge_sql(d):
    """Alternative keyed synchronization; no exact reference-text matching in grading."""
    import re
    statements=[]
    for table,query in d['queries'].items():
        if d['id']=='H11':
            # A key-only anti-join avoids SQLite's optimized, database-less READ
            # callback for the epoch-default join under the frozen authorizer.
            statements.append('DELETE FROM migrated WHERE id NOT IN (SELECT id FROM documents);')
            statements.append(f'INSERT OR REPLACE INTO {table} {query};')
            continue
        # Read output column order from the trusted schema, not the answer rows.
        declaration=re.search(r'CREATE TABLE '+table+r'\((.*?)\);',d['schema'],re.S).group(1)
        columns=[]
        for item in declaration.split(','):
            token=item.strip().split()[0]
            if token in ('PRIMARY','UNIQUE') or ')' in token:break
            columns.append(token)
        names=','.join(columns)
        match=' AND '.join(f't.{k}={table}.{k}' for k in d['keys'][table])
        statements.append(f'WITH target({names}) AS ({query}) DELETE FROM {table} WHERE NOT EXISTS(SELECT 1 FROM target t WHERE {match});')
        statements.append(f'INSERT OR REPLACE INTO {table} {query};')
    return '\n'.join(statements)


def build(case_id,seed=0,healthy=False):
    d=definition(case_id,seed);expected=oracle(case_id,d['tables']);tables=copy.deepcopy(d['tables'])
    tables.update(copy.deepcopy(expected))
    n=lambda x:f'{x}_{seed}'
    if not healthy:
        if case_id=='H01':
            next(r for r in tables['outbox'] if r[0]==n('m1'))[1:] = ['pending',0]
        elif case_id=='H05':
            tables['allocations']=[r for r in tables['allocations'] if r[:2]!=[n('kit1'),n('b')]]
            tables['allocations'].append([n('kit2'),n('a'),4])
            tables['available']=[[s,total-sum(r[2] for r in tables['allocations'] if r[1]==s)] for s,total in tables['inventory']]
        elif case_id=='H09':
            files=dict(tables['files'])
            tables['active_files'] += [[n('sales'),n('f0'),files[n('f0')]],[n('sales'),n('f2'),files[n('f2')]]]
            tables['dataset_totals']=[[ds,sum(r[2] for r in tables['active_files'] if r[0]==ds)] for ds,_ in tables['heads']]
        elif case_id=='H13':
            tables['effective_access']=[r for r in tables['effective_access'] if r!=[n('cy'),n('export')]]+[[n('ana'),n('export')]]
            tables['access_counts']=[[u,sum(a==u for a,_ in tables['effective_access'])] for (u,) in tables['users']]
        elif case_id=='H17':
            next(r for r in tables['readings'] if r[0]==n('east'))[1]=dict(tables['meters'])[n('east')]+sum(r[4] for r in tables['commands'] if r[1]==n('east'))
        elif case_id=='H21':
            next(r for r in tables['releases'] if r[0]==n('b1'))[1:]=['released',2]
            next(r for r in tables['releases'] if r[0]==n('b2'))[1]='released'
        else:
            from .heldout_remaining import damage
            damage(case_id,tables,d,seed)
    task=dict(id=case_id,title=d['title'],specification=d['spec']+
              ' All evidence tables including work are immutable. Listed projections are rebuildable. Recover all historical damage, preserve unrelated correct records, '
              'and leave an already healthy snapshot unchanged. Recovery and subsequent patch processing must be repeatable.',
              schema=d['schema'],application_sql=d['patch'],writable_tables=list(d['queries']),
              immutable_tables=list(d['tables']),append_only_tables=[],tables=tables,evidence=d['evidence'],
              condition='correct_patch_given',family=d['family'],history_variant=case_id)
    private=dict(expected=expected,reference_recovery=rebuild_sql(d),alternative_recovery=merge_sql(d),
                 negative_controls=d['wrong'],future_inputs=d['future'],projection_keys=d['keys'])
    return task,private


def future_fixture(case_id,seed=0):
    task,private=build(case_id,seed,healthy=True)
    task['tables'].update(copy.deepcopy(private['future_inputs']))
    return task,oracle(case_id,task['tables'])
