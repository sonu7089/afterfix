"""Private definitions for the remaining frozen-roster cases; no model imports.

SQL projections and Python oracles are intentionally separate implementations.
Work scopes the fixed application patch; historical work is initially empty.
"""
import copy


def definition(case_id, seed=0):
    n = lambda x: f'{x}_{seed}'
    q = seed % 5
    if case_id == 'H02':
        family='delivery_workflows'; title='InboxLane: a failed consumer transaction overwrote an accepted revision'
        schema='''CREATE TABLE entities(id TEXT PRIMARY KEY,initial INTEGER);
CREATE TABLE events(id TEXT PRIMARY KEY,entity TEXT,revision INTEGER,value INTEGER,UNIQUE(entity,revision));
CREATE TABLE attempts(id TEXT PRIMARY KEY,event TEXT,outcome TEXT);
CREATE TABLE applied(entity TEXT PRIMARY KEY,value INTEGER,revision INTEGER);'''
        tables={'entities':[[n('order'),5],[n('healthy'),9],[n('idle'),4]],
                'events':[[n('e1'),n('order'),1,20+q],[n('e2'),n('order'),2,30+q],[n('e3'),n('order'),3,99],[n('e4'),n('healthy'),1,12]],
                'attempts':[[n('a1'),n('e1'),'committed'],[n('a2'),n('e1'),'failed'],[n('a3'),n('e2'),'committed'],[n('a4'),n('e3'),'failed'],[n('a5'),n('e4'),'committed']]}
        accepted="EXISTS(SELECT 1 FROM attempts a WHERE a.event=e.id AND a.outcome='committed')"
        queries={'applied':f"SELECT x.id AS entity,COALESCE((SELECT value FROM events e WHERE e.entity=x.id AND {accepted} ORDER BY revision DESC LIMIT 1),x.initial),COALESCE((SELECT MAX(revision) FROM events e WHERE e.entity=x.id AND {accepted}),0) FROM entities x"}
        keys={'applied':['entity']}
        spec='Each event is a full replacement value, not a delta. An event is accepted if any transaction attempt committed, even if a duplicate retry failed. Materialize the highest accepted revision for each entity; with none use initial and revision zero. Failed-only events have no effect. Later accepted replacements supersede earlier ones.'
        evidence=['An inbox rebuild read the highest seen revision before checking transaction commit.', 'entities + events + attempts -> applied; work -> applied']
        future={'attempts':tables['attempts']+[[n('a6'),n('e3'),'committed']], 'work':[[n('order')]]}
        dirty={'applied':{n('order'):[99,3]}}
        wrong={'seen_equals_committed':"UPDATE applied SET value=COALESCE((SELECT value FROM events e WHERE e.entity=applied.entity ORDER BY revision DESC LIMIT 1),value);", 'sum_replacements':"UPDATE applied SET value=COALESCE((SELECT SUM(value) FROM events e WHERE e.entity=applied.entity),value);"}
    elif case_id == 'H03':
        family='delivery_workflows'; title='SagaDock: compensation intents included unfinished child steps'
        schema='''CREATE TABLE parents(id TEXT PRIMARY KEY,state TEXT);
CREATE TABLE steps(id TEXT PRIMARY KEY,parent TEXT,state TEXT,cost INTEGER);
CREATE TABLE undo_receipts(step TEXT PRIMARY KEY,accepted INTEGER);
CREATE TABLE compensation(step TEXT PRIMARY KEY,state TEXT,units INTEGER);'''
        tables={'parents':[[n('p1'),'canceled'],[n('p2'),'active']],
                'steps':[[n('s1'),n('p1'),'completed',3+q],[n('s2'),n('p1'),'pending',4],[n('s3'),n('p1'),'completed',2],[n('s4'),n('p2'),'completed',5]],
                'undo_receipts':[[n('s3'),1],[n('s1'),0]]}
        queries={'compensation':"SELECT s.id AS step,CASE WHEN p.state='canceled' AND s.state='completed' THEN CASE WHEN EXISTS(SELECT 1 FROM undo_receipts u WHERE u.step=s.id AND u.accepted=1) THEN 'done' ELSE 'pending' END ELSE 'none' END,CASE WHEN p.state='canceled' AND s.state='completed' THEN s.cost ELSE 0 END FROM steps s JOIN parents p ON p.id=s.parent"}
        keys={'compensation':['step']}
        spec='compensation is a rebuildable intent/status projection, not an external side-effect log. Include every child step. Only completed steps of canceled parents require undo: state done if an accepted undo receipt exists, otherwise pending; units equals cost. All other steps have state none and zero units. Never enqueue undo again for an acknowledged compensation. Parent changes expand work to child step IDs.'
        evidence=['A saga retry generated undo intents for every child and reset an acknowledged undo.', 'parents + steps + undo_receipts -> compensation; work -> compensation']
        future={'parents':[[n('p1'),'canceled'],[n('p2'),'canceled']], 'undo_receipts':[[n('s3'),1],[n('s1'),1]],'work':[[n('s1')],[n('s4')]]}
        dirty={'compensation':{n('s2'):['pending',4],n('s3'):['pending',2]}}
        wrong={'undo_unfinished':"UPDATE compensation SET state='pending',units=(SELECT cost FROM steps WHERE id=compensation.step) WHERE step IN (SELECT s.id FROM steps s JOIN parents p ON p.id=s.parent WHERE p.state='canceled');", 'forget_acknowledgement':"UPDATE compensation SET state='pending' WHERE state='done';"}
    elif case_id == 'H04':
        family='delivery_workflows';title='FenceRun: a retired lease owner published a late completion'
        schema='''CREATE TABLE leases(job TEXT PRIMARY KEY,generation INTEGER,fence INTEGER,owner TEXT);
CREATE TABLE completions(id TEXT PRIMARY KEY,job TEXT,generation INTEGER,fence INTEGER,owner TEXT,seq INTEGER,value INTEGER);
CREATE TABLE job_results(job TEXT PRIMARY KEY,state TEXT,value INTEGER);'''
        tables={'leases':[[n('j1'),2,9,n('new')],[n('j2'),1,3,n('other')],[n('j3'),2,8,n('new')]],
                'completions':[[n('c1'),n('j1'),2,9,n('new'),1,40+q],[n('c2'),n('j1'),1,8,n('old'),9,99],
                               [n('c3'),n('j1'),2,9,n('old'),10,88],[n('c4'),n('j2'),1,3,n('other'),1,6],
                               [n('c5'),n('j3'),2,7,n('new'),1,55]]}
        match='c.job=l.job AND c.generation=l.generation AND c.fence=l.fence AND c.owner=l.owner'
        queries={'job_results':f"SELECT l.job,CASE WHEN EXISTS(SELECT 1 FROM completions c WHERE {match}) THEN 'done' ELSE 'pending' END,COALESCE((SELECT value FROM completions c WHERE {match} ORDER BY seq DESC LIMIT 1),0) FROM leases l"}
        keys={'job_results':['job']}
        spec='One result per current lease. A completion is valid only when job, generation, fencing token AND owner match the current lease exactly. Choose the highest seq among valid completions: done and its value. With none: pending and value zero. seq breaks ties within a lease; late arrival does not grant authority to an old owner or token.'
        evidence=['Late stale-owner output replaced the new owner result. Another job has only a wrong-token completion.', 'leases + completions -> job_results; work -> job_results']
        future={'leases':[[n('j1'),3,10,n('next')],*tables['leases'][1:]], 'completions':tables['completions']+[[n('c6'),n('j3'),2,8,n('new'),2,7+q]], 'work':[[n('j1')],[n('j3')]]}
        dirty={'job_results':{n('j1'):['done',88],n('j3'):['done',55]}}
        wrong={'latest_arrival_wins':"UPDATE job_results SET state='done',value=(SELECT value FROM completions c WHERE c.job=job_results.job ORDER BY seq DESC LIMIT 1);", 'discard_new_owner_too':"UPDATE job_results SET state='pending',value=0;"}
    elif case_id == 'H06':
        family='coupled_resources';title='StockBridge: partial transfer receipts were credited as full deliveries'
        schema='''CREATE TABLE warehouses(id TEXT PRIMARY KEY,opening INTEGER);
CREATE TABLE transfers(id TEXT PRIMARY KEY,source TEXT,destination TEXT,qty INTEGER,accepted INTEGER);
CREATE TABLE receipts(id TEXT PRIMARY KEY,transfer TEXT,qty INTEGER,accepted INTEGER);
CREATE TABLE transfer_state(id TEXT PRIMARY KEY,debit INTEGER,credit INTEGER,in_transit INTEGER);
CREATE TABLE stock(warehouse TEXT PRIMARY KEY,qty INTEGER);'''
        tables={'warehouses':[[n('a'),100+q],[n('b'),30],[n('c'),20]],
                'transfers':[[n('t1'),n('a'),n('b'),10+q,1],[n('t2'),n('a'),n('c'),7,0],[n('t3'),n('b'),n('c'),3,1]],
                'receipts':[[n('r1'),n('t1'),4,1],[n('r2'),n('t1'),2,0],[n('r3'),n('t2'),7,1],[n('r4'),n('t3'),3,1]]}
        credit="CASE WHEN t.accepted=1 THEN COALESCE((SELECT SUM(qty) FROM receipts r WHERE r.transfer=t.id AND r.accepted=1),0) ELSE 0 END"
        queries={'transfer_state':f'SELECT t.id,t.qty*t.accepted,{credit},t.qty*t.accepted-({credit}) FROM transfers t',
                 'stock':"SELECT w.id,w.opening-COALESCE((SELECT SUM(s.debit) FROM transfer_state s JOIN transfers t ON t.id=s.id WHERE t.source=w.id),0)+COALESCE((SELECT SUM(s.credit) FROM transfer_state s JOIN transfers t ON t.id=s.id WHERE t.destination=w.id),0) FROM warehouses w"}
        keys={'transfer_state':['id'],'stock':['warehouse']}
        spec='Accepted transfers debit their full quantity from source. Credit destination only for accepted receipt quantities of accepted transfers; ignore rejected receipts and all evidence for rejected transfers. Receipt IDs identify distinct parts; accepted receipt sum never exceeds quantity. in_transit=debit-credit. Stock equals opening minus outgoing debits plus incoming credits. Stock plus all in_transit conserves opening inventory.'
        evidence=['Transfer finalization assumed shipment meant full receipt and honored a receipt for a rejected transfer.', 'transfers + receipts -> transfer_state; warehouses + transfers + transfer_state -> stock; work -> transfer_state']
        future={'receipts':tables['receipts']+[[n('r5'),n('t1'),6+q,1]],'work':[[n('t1')]]}
        dirty={'transfer_state':{n('t1'):[10+q,10+q,0],n('t2'):[7,7,0]}}
        wrong={'credit_on_dispatch':'UPDATE transfer_state SET credit=debit,in_transit=0;', 'honor_rejected_transfers':'UPDATE transfer_state SET debit=(SELECT qty FROM transfers t WHERE t.id=transfer_state.id);'}
    elif case_id == 'H07':
        family='coupled_resources';title='SplitCart: returns freed unshipped reservations and duplicated replacements'
        schema='''CREATE TABLE lines(id TEXT PRIMARY KEY,ordered INTEGER);
CREATE TABLE shipments(id TEXT PRIMARY KEY,line TEXT,qty INTEGER);
CREATE TABLE returns(id TEXT PRIMARY KEY,shipment TEXT,qty INTEGER,accepted INTEGER);
CREATE TABLE replacements(return_id TEXT PRIMARY KEY,shipped INTEGER);
CREATE TABLE line_state(line TEXT PRIMARY KEY,reserved INTEGER,net_delivered INTEGER,replacement_due INTEGER);'''
        tables={'lines':[[n('l1'),10+q],[n('l2'),4],[n('l3'),3]],
                'shipments':[[n('s1'),n('l1'),4],[n('s2'),n('l1'),2],[n('s3'),n('l2'),4]],
                'returns':[[n('r1'),n('s1'),2,1],[n('r2'),n('s2'),1,0],[n('r3'),n('s3'),1,1]],
                'replacements':[[n('r1'),1],[n('r3'),1]]}
        queries={'line_state':"SELECT l.id AS line,l.ordered-COALESCE((SELECT SUM(qty) FROM shipments s WHERE s.line=l.id),0),COALESCE((SELECT SUM(qty) FROM shipments s WHERE s.line=l.id),0)-COALESCE((SELECT SUM(r.qty) FROM returns r JOIN shipments s ON s.id=r.shipment WHERE s.line=l.id AND r.accepted=1),0),COALESCE((SELECT SUM(r.qty-COALESCE(p.shipped,0)) FROM returns r JOIN shipments s ON s.id=r.shipment LEFT JOIN replacements p ON p.return_id=r.id WHERE s.line=l.id AND r.accepted=1),0) FROM lines l"}
        keys={'line_state':['line']}
        spec='Original shipments reserve ordered minus shipped, regardless of returns. net_delivered counts original shipped units minus accepted returns on those shipments. Every accepted return requests the same quantity of replacement; replacement_due subtracts replacements already shipped for that return. Replacements are tracked separately and are not original shipments. Rejected returns do nothing. Valid quantities never over-return or over-replace.'
        evidence=['An order-level refund freed still-unshipped allocations; replay also forgot an already sent replacement.', 'lines + shipments + returns + replacements -> line_state; work -> line_state']
        future={'shipments':tables['shipments']+[[n('s4'),n('l3'),2]],'replacements':[[n('r1'),2],[n('r3'),1]],'work':[[n('l1')],[n('l3')]]}
        dirty={'line_state':{n('l1'):[2+q,3,2]}}
        wrong={'free_unshipped_on_return':'UPDATE line_state SET reserved=0 WHERE replacement_due>0;', 'resend_completed_replacement':"UPDATE line_state SET replacement_due=COALESCE((SELECT SUM(r.qty) FROM returns r JOIN shipments s ON s.id=r.shipment WHERE s.line=line_state.line AND r.accepted=1),0);"}
    elif case_id == 'H08':
        family='coupled_resources';title='QuotaNest: expiry returned consumed escrow to the parent pool'
        schema='''CREATE TABLE clock(now INTEGER);
CREATE TABLE pools(id TEXT PRIMARY KEY,capacity INTEGER);
CREATE TABLE tenants(id TEXT PRIMARY KEY,pool TEXT,capacity INTEGER);
CREATE TABLE leases(id TEXT PRIMARY KEY,tenant TEXT,issued INTEGER,consumed INTEGER,expires INTEGER);
CREATE TABLE escrow(tenant TEXT PRIMARY KEY,committed INTEGER,free INTEGER);
CREATE TABLE pool_free(pool TEXT PRIMARY KEY,free INTEGER);'''
        tables={'clock':[[20]],'pools':[[n('p'),100+q]],'tenants':[[n('a'),n('p'),40],[n('b'),n('p'),30],[n('c'),n('p'),20]],
                'leases':[[n('x'),n('a'),10+q,4,20],[n('y'),n('a'),8,2,30],[n('z'),n('b'),5,1,10]]}
        committed="COALESCE((SELECT SUM(CASE WHEN l.expires>c.now THEN l.issued ELSE l.consumed END) FROM leases l CROSS JOIN clock c WHERE l.tenant=t.id),0)"
        queries={'escrow':f'SELECT t.id AS tenant,{committed},t.capacity-({committed}) FROM tenants t',
                 'pool_free':'SELECT p.id,p.capacity-COALESCE((SELECT SUM(e.committed) FROM escrow e JOIN tenants t ON t.id=e.tenant WHERE t.pool=p.id),0) FROM pools p'}
        keys={'escrow':['tenant'],'pool_free':['pool']}
        spec='An unexpired lease commits issued units, including consumed units. At expires<=clock.now only consumed units remain committed permanently; unused escrow returns. Sum commitments per tenant, subtract from tenant capacity and shared parent capacity. Consumption never exceeds issued; valid fixtures fit both limits. A clock tick puts all affected tenants in work.'
        evidence=['An expiry sweep refunded entire leases, including irrevocably consumed units.', 'clock + leases + tenants -> escrow; pools + tenants + escrow -> pool_free; work -> escrow']
        future={'clock':[[30]],'leases':tables['leases']+[[n('new'),n('c'),3,0,40]],'work':[[n('a')],[n('b')],[n('c')]]}
        dirty={'escrow':{n('a'):[8,32],n('b'):[0,30]}}
        wrong={'refund_consumed':"UPDATE escrow SET committed=COALESCE((SELECT SUM(issued) FROM leases l CROSS JOIN clock c WHERE l.tenant=escrow.tenant AND l.expires>c.now),0);", 'hold_expired_escrow':"UPDATE escrow SET committed=COALESCE((SELECT SUM(issued) FROM leases l WHERE l.tenant=escrow.tenant),0);"}
    elif case_id == 'H10':
        family='versioned_storage';title='CompactSpan: partial publication counted source and replacement ranges twice'
        schema='''CREATE TABLE slots(dataset TEXT,pos INTEGER,PRIMARY KEY(dataset,pos));
CREATE TABLE segments(id TEXT PRIMARY KEY,dataset TEXT,lo INTEGER,hi INTEGER,generation INTEGER,published INTEGER);
CREATE TABLE coverage(dataset TEXT,pos INTEGER,file TEXT,generation INTEGER,PRIMARY KEY(dataset,pos));'''
        tables={'slots':[[n('a'),i] for i in range(6)]+[[n('b'),0]],
                'segments':[[n('old'),n('a'),0,6,1,1],[n('left'),n('a'),0,3,2,1],[n('right'),n('a'),3,6,2,0],[n('bfile'),n('b'),0,1,1,1]]}
        queries={'coverage':"SELECT s.dataset,s.pos,f.id,f.generation FROM slots s JOIN segments f ON f.dataset=s.dataset AND s.pos>=f.lo AND s.pos<f.hi AND f.published=1 WHERE NOT EXISTS(SELECT 1 FROM segments g WHERE g.dataset=s.dataset AND s.pos>=g.lo AND s.pos<g.hi AND g.published=1 AND g.generation>f.generation)"}
        keys={'coverage':['dataset','pos']}
        spec='slots enumerates logical record positions. coverage maps every slot to exactly one physical segment: highest generation among published segments covering its half-open [lo,hi) range. Same-generation ranges never overlap; every slot has a published covering segment. A partially published compaction supersedes only its published subranges. Staged ranges contribute nothing; retain old coverage elsewhere.'
        evidence=['A compaction index switched the entire source range before the right replacement was published.', 'slots + segments -> coverage; work -> coverage']
        future={'segments':[[i,d,l,h,g,1 if i==n('right') else p] for i,d,l,h,g,p in tables['segments']], 'work':[[n('a')]]}
        dirty={'coverage':{}} # per-position damage below
        wrong={'drop_unreplaced_source':"DELETE FROM coverage WHERE generation=1 AND dataset IN (SELECT dataset FROM segments WHERE generation>1);", 'trust_unpublished':"UPDATE coverage SET file=(SELECT id FROM segments s WHERE s.dataset=coverage.dataset AND coverage.pos>=s.lo AND coverage.pos<s.hi ORDER BY generation DESC LIMIT 1),generation=(SELECT MAX(generation) FROM segments s WHERE s.dataset=coverage.dataset AND coverage.pos>=s.lo AND coverage.pos<s.hi);"}
    elif case_id == 'H11':
        family='versioned_storage';title='EpochDesk: a migration replaced explicit NULL and later operator edits'
        schema='''CREATE TABLE documents(id TEXT PRIMARY KEY,epoch INTEGER,present INTEGER,value TEXT);
CREATE TABLE defaults(epoch INTEGER PRIMARY KEY,value TEXT);
CREATE TABLE edits(id TEXT,seq INTEGER,value TEXT,PRIMARY KEY(id,seq));
CREATE TABLE migrated(id TEXT PRIMARY KEY,value TEXT,source TEXT,revision INTEGER);'''
        tables={'documents':[[n('absent'),1,0,None],[n('null'),1,1,None],[n('edited'),1,0,None],[n('healthy'),2,1,'kept']],
                'defaults':[[1,'legacy'],[2,'modern']], 'edits':[[n('edited'),1,'manual'],[n('edited'),2,None]]}
        queries={'migrated':"SELECT d.id,CASE WHEN EXISTS(SELECT 1 FROM edits e WHERE e.id=d.id) THEN (SELECT value FROM edits e WHERE e.id=d.id ORDER BY seq DESC LIMIT 1) WHEN d.present=1 THEN d.value ELSE f.value END,CASE WHEN EXISTS(SELECT 1 FROM edits e WHERE e.id=d.id) THEN 'operator' WHEN d.present=1 THEN 'stored' ELSE 'default' END,COALESCE((SELECT MAX(seq) FROM edits e WHERE e.id=d.id),0) FROM documents d JOIN defaults f ON f.epoch=d.epoch"}
        keys={'migrated':['id']}
        spec='Apply a default for the document schema epoch only when present=0. present=1 with value NULL is an explicit stored NULL, not absence. Any operator edit supersedes migration; highest seq wins even when its value is NULL. source is operator, stored, or default respectively. revision is highest edit seq or zero. Every document has exactly one matching epoch default.'
        evidence=['COALESCE confused explicit NULL with absent fields and overwrote a later operator-cleared value.', 'documents + defaults + edits -> migrated; work -> migrated']
        future={'edits':tables['edits']+[[n('absent'),1,'late manual']], 'work':[[n('absent')]]}
        dirty={'migrated':{n('null'):['legacy','default',0],n('edited'):['legacy','default',0]}}
        wrong={'null_means_absent':"UPDATE migrated SET value=(SELECT f.value FROM documents d JOIN defaults f ON f.epoch=d.epoch WHERE d.id=migrated.id) WHERE value IS NULL;", 'overwrite_operator':"UPDATE migrated SET value='legacy',source='default',revision=0 WHERE source='operator';"}
    elif case_id == 'H12':
        family='versioned_storage';title='CacheForge: a reused object key inherited its deleted incarnation cache'
        schema='''CREATE TABLE objects(key TEXT PRIMARY KEY,generation INTEGER,active INTEGER);
CREATE TABLE materializations(id TEXT PRIMARY KEY,key TEXT,generation INTEGER,seq INTEGER,value INTEGER,accepted INTEGER);
CREATE TABLE cache(key TEXT PRIMARY KEY,generation INTEGER,value INTEGER,seq INTEGER);'''
        tables={'objects':[[n('reuse'),3,1],[n('healthy'),1,1],[n('gone'),2,0],[n('cold'),1,1]],
                'materializations':[[n('m1'),n('reuse'),2,99,90,1],[n('m2'),n('reuse'),3,1,8+q,1],[n('m3'),n('reuse'),3,2,77,0],[n('m4'),n('healthy'),1,1,6,1],[n('m5'),n('gone'),2,1,4,1]]}
        queries={'cache':"SELECT o.key,o.generation,m.value,m.seq FROM objects o JOIN materializations m ON m.key=o.key AND m.generation=o.generation WHERE o.active=1 AND m.accepted=1 AND NOT EXISTS(SELECT 1 FROM materializations x WHERE x.key=m.key AND x.generation=m.generation AND x.accepted=1 AND x.seq>m.seq)"}
        keys={'cache':['key']}
        spec='Cache only active objects with an accepted materialization for their current generation. Choose its highest seq within that generation. No row for deleted or cold objects. Sequence numbers from an old incarnation cannot be compared against the current generation. Rejected materializations have no effect.'
        evidence=['A key-only upsert revived generation 2 after the key was recreated at generation 3.', 'objects + materializations -> cache; work -> cache']
        future={'materializations':tables['materializations']+[[n('m6'),n('cold'),1,1,11+q,1]],'objects':[[k,g,0 if k==n('healthy') else a] for k,g,a in tables['objects']], 'work':[[n('cold')],[n('healthy')]]}
        dirty={'cache':{n('reuse'):[2,90,99]}}
        wrong={'key_only_latest':"UPDATE cache SET value=(SELECT value FROM materializations m WHERE m.key=cache.key ORDER BY seq DESC LIMIT 1);", 'delete_reused_key_entirely':"DELETE FROM cache WHERE key IN (SELECT key FROM materializations GROUP BY key HAVING COUNT(DISTINCT generation)>1);"}
    else:
        return graph_order_evidence(case_id,seed)
    return finish(locals())


def finish(v):
    """Common projection plumbing; semantic definitions and oracles remain case-specific."""
    d={k:v[k] for k in ('family','title','schema','tables','queries','keys','spec','evidence','future','dirty','wrong')}
    d['id']=v['case_id'];d['schema']+='\nCREATE TABLE work(entity TEXT PRIMARY KEY);';d['tables']['work']=[]
    first=next(iter(d['queries']));key=d['keys'][first][0]
    d['patch']=f'DELETE FROM {first} WHERE {key} IN (SELECT entity FROM work); INSERT INTO {first} SELECT * FROM ({d["queries"][first]}) WHERE {key} IN (SELECT entity FROM work);'
    for table,query in list(d['queries'].items())[1:]:d['patch']+=f'DELETE FROM {table}; INSERT INTO {table} {query};'
    d['spec']+=f' The fixed patch refreshes only {key} IDs in work for {first}, then refreshes any dependent summaries. Historical IDs are absent from work.'
    return d


def graph_order_evidence(case_id,seed):
    n=lambda x:f'{x}_{seed}';q=seed%5
    if case_id=='H14':
        family='authorization_graphs';title='DelegateTree: revocation removed independent grants but retained descendants'
        schema='''CREATE TABLE delegations(id TEXT PRIMARY KEY,parent TEXT,user TEXT,resource TEXT,revoked INTEGER);
CREATE TABLE access(user TEXT,resource TEXT,paths INTEGER,PRIMARY KEY(user,resource));'''
        tables={'delegations':[[n('root'),None,n('owner'),n('read'),1],[n('child'),n('root'),n('ana'),n('read'),0],
                               [n('grand'),n('child'),n('bo'),n('read'),0],[n('independent'),None,n('ana'),n('read'),0],[n('healthy'),None,n('cy'),n('read'),0]]}
        queries={'access':"WITH RECURSIVE live(id,user,resource) AS (SELECT id,user,resource FROM delegations WHERE parent IS NULL AND revoked=0 UNION ALL SELECT d.id,d.user,d.resource FROM delegations d JOIN live l ON d.parent=l.id WHERE d.revoked=0) SELECT user,resource,COUNT(*) FROM live GROUP BY user,resource"}
        keys={'access':['user','resource']}
        spec='Delegations form an acyclic forest with existing parents and unchanged resource along a chain. A grant is effective only if neither it nor any ancestor is revoked. Count effective grant nodes per (user,resource), one access row if count>0. Revocation on one path does not remove an independent root/path. work contains all affected users, including descendants.'
        evidence=['A flat revoke removed all access for one user but missed a grandchild of the revoked root.', 'delegations -> access; work -> access']
        future={'delegations':tables['delegations']+[[n('new'),n('independent'),n('bo'),n('read'),0]],'work':[[n('bo')]]}
        dirty={'access':{n('ana'):[n('read'),2]}}
        wrong={'check_only_leaf':"DELETE FROM access; INSERT INTO access SELECT user,resource,COUNT(*) FROM delegations WHERE revoked=0 GROUP BY user,resource;", 'revoke_user_everywhere':"DELETE FROM access WHERE user IN (SELECT user FROM delegations WHERE parent IS NOT NULL);"}
    elif case_id=='H15':
        family='authorization_graphs';title='GroupFork: a team split erased direct membership provenance'
        schema='''CREATE TABLE assignments(id TEXT PRIMARY KEY,user TEXT,origin TEXT,kind TEXT,active INTEGER);
CREATE TABLE routing(assignment TEXT,target TEXT,accepted INTEGER,PRIMARY KEY(assignment,target));
CREATE TABLE membership(user TEXT,team TEXT,sources INTEGER,PRIMARY KEY(user,team));'''
        tables={'assignments':[[n('a1'),n('ana'),n('legacy'),'inherited',1],[n('a2'),n('ana'),n('red'),'direct',1],[n('a3'),n('bo'),n('legacy'),'inherited',1],[n('a4'),n('cy'),n('blue'),'direct',1],[n('a5'),n('di'),n('legacy'),'inherited',0]],
                'routing':[[n('a1'),n('blue'),1],[n('a1'),n('red'),0],[n('a2'),n('blue'),1],[n('a3'),n('red'),1],[n('a3'),n('blue'),1],[n('a5'),n('red'),1]]}
        queries={'membership':"SELECT user,team,COUNT(*) FROM (SELECT user,origin AS team FROM assignments WHERE kind='direct' AND active=1 UNION ALL SELECT a.user,r.target FROM assignments a JOIN routing r ON r.assignment=a.id WHERE a.kind='inherited' AND a.active=1 AND r.accepted=1) GROUP BY user,team"}
        keys={'membership':['user','team']}
        spec='Active direct assignments retain their origin team and ignore routing. Active inherited assignments contribute only accepted routing targets, never their old origin. A split can route one assignment to multiple targets; a merge can create multiple independent sources for one membership. Store one (user,team) row with the number of contributing assignment IDs. Inactive assignments and rejected routes do not contribute.'
        evidence=['A group split applied routing to direct assignments and retained retired inherited origins.', 'assignments + routing -> membership; work -> membership']
        future={'assignments':tables['assignments']+[[n('a6'),n('ana'),n('blue'),'direct',1]],'work':[[n('ana')]]}
        dirty={'membership':{n('ana'):[n('blue'),2]}}
        wrong={'retain_retired_origin':"INSERT OR REPLACE INTO membership SELECT user,origin,COUNT(*) FROM assignments WHERE active=1 GROUP BY user,origin;", 'discard_direct_assignments':"DELETE FROM membership WHERE (user,team) IN (SELECT user,origin FROM assignments WHERE kind='direct');"}
    elif case_id=='H16':
        family='authorization_graphs';title='CapChain: child scopes widened beyond ancestor limits'
        schema='''CREATE TABLE clock(now INTEGER);
CREATE TABLE capabilities(id TEXT PRIMARY KEY,parent TEXT,mask INTEGER,expires INTEGER);
CREATE TABLE effective(id TEXT PRIMARY KEY,mask INTEGER,expires INTEGER);'''
        tables={'clock':[[20]],'capabilities':[[n('root'),None,3,50],[n('child'),n('root'),6,60],[n('grand'),n('child'),7,70],[n('expired'),None,7,20],[n('under_expired'),n('expired'),7,80],[n('healthy'),None,4,90],[n('zero'),n('root'),4,90]]}
        queries={'effective':"WITH RECURSIVE c(id,mask,expires) AS (SELECT id,mask,expires FROM capabilities WHERE parent IS NULL UNION ALL SELECT a.id,a.mask&c.mask,MIN(a.expires,c.expires) FROM capabilities a JOIN c ON a.parent=c.id) SELECT c.id,c.mask,c.expires FROM c CROSS JOIN clock t WHERE c.mask>0 AND c.expires>t.now"}
        keys={'effective':['id']}
        spec='Capabilities form an acyclic forest. Scopes are integer bit masks (read=1, write=2, export=4). Effective scope is bitwise AND along the entire ancestor path, and expiry is the minimum along that path. Include a capability only if effective mask is nonzero and expiry>clock.now; equality is expired. A longer child expiry never extends its parent. work expands descendants of changed roots and expired paths.'
        evidence=['A delegator unioned scope bits and used the child expiry, extending authority beyond the root.', 'clock + capabilities -> effective; work -> effective']
        future={'clock':[[50]],'work':[[r[0]] for r in tables['capabilities']]}
        dirty={'effective':{n('child'):[7,60],n('grand'):[7,70]}}
        wrong={'leaf_scope_and_expiry':'UPDATE effective SET mask=(SELECT mask FROM capabilities a WHERE a.id=effective.id),expires=(SELECT expires FROM capabilities a WHERE a.id=effective.id);', 'include_expired_ancestors':'INSERT OR REPLACE INTO effective SELECT id,mask,expires FROM capabilities;'}
    elif case_id=='H18':
        family='ordered_state';title='AmendStay: a cancellation for an old version removed a reinstated reservation'
        schema='''CREATE TABLE reservations(id TEXT PRIMARY KEY);
CREATE TABLE versions(reservation TEXT,version INTEGER,qty INTEGER,PRIMARY KEY(reservation,version));
CREATE TABLE actions(id TEXT PRIMARY KEY,reservation TEXT,seq INTEGER,version INTEGER,kind TEXT,UNIQUE(reservation,seq));
CREATE TABLE allocation(reservation TEXT PRIMARY KEY,version INTEGER,qty INTEGER);'''
        tables={'reservations':[[n('a')],[n('b')],[n('c')]],'versions':[[n('a'),1,4],[n('a'),2,7+q],[n('b'),1,3],[n('c'),1,2]],
                'actions':[[n('x1'),n('a'),1,1,'activate'],[n('x2'),n('a'),2,2,'activate'],[n('x3'),n('a'),3,2,'cancel'],[n('x4'),n('a'),4,2,'reinstate'],[n('x5'),n('a'),5,1,'cancel'],[n('x6'),n('b'),1,1,'activate'],[n('x7'),n('c'),1,1,'activate'],[n('x8'),n('c'),2,1,'cancel']]}
        queries={'allocation':"WITH current AS (SELECT r.id,(SELECT version FROM actions a WHERE a.reservation=r.id AND a.kind='activate' ORDER BY seq DESC LIMIT 1) AS v FROM reservations r) SELECT c.id AS reservation,c.v,CASE WHEN (SELECT kind FROM actions a WHERE a.reservation=c.id AND a.version=c.v ORDER BY seq DESC LIMIT 1)='cancel' THEN 0 ELSE v.qty END FROM current c JOIN versions v ON v.reservation=c.id AND v.version=c.v"}
        keys={'allocation':['reservation']}
        spec='Process actions in seq order. activate installs its version and quantity, superseding earlier versions. cancel and reinstate affect only the currently active version; stale-version actions do nothing. Reinstate restores that version quantity. All versions are activated once in increasing version order, every reservation is activated, and later cancellation/reinstatement references existing versions. Store current version even when canceled (qty zero).'
        evidence=['A delayed cancellation for version 1 was applied after version 2 had been reinstated.', 'reservations + versions + actions -> allocation; work -> allocation']
        future={'actions':tables['actions']+[[n('x9'),n('c'),3,1,'reinstate']], 'work':[[n('c')]]}
        dirty={'allocation':{n('a'):[2,0]}}
        wrong={'latest_cancel_any_version':"UPDATE allocation SET qty=0 WHERE reservation IN (SELECT reservation FROM actions WHERE kind='cancel');", 'sum_all_versions':"UPDATE allocation SET qty=(SELECT SUM(qty) FROM versions v WHERE v.reservation=allocation.reservation);"}
    elif case_id=='H19':
        family='ordered_state';title='TierMeter: replay priced every usage event in the first tier'
        schema='''CREATE TABLE accounts(id TEXT PRIMARY KEY,threshold INTEGER,low_rate INTEGER,high_rate INTEGER);
CREATE TABLE usage_events(id TEXT PRIMARY KEY,account TEXT,seq INTEGER,kind TEXT,units INTEGER,arrival INTEGER,UNIQUE(account,seq));
CREATE TABLE charges(account TEXT,event TEXT,low_units INTEGER,high_units INTEGER,cost INTEGER,PRIMARY KEY(account,event));'''
        tables={'accounts':[[n('a'),10+q,2,5],[n('b'),8,1,3]],
                'usage_events':[[n('e1'),n('a'),1,'use',8,1],[n('e2'),n('a'),2,'use',6+q,5],[n('e3'),n('a'),3,'reset',0,2],[n('e4'),n('a'),4,'use',3,3],[n('e5'),n('b'),1,'use',2,1]]}
        queries={'charges':"WITH u AS (SELECT e.*,a.threshold,a.low_rate,a.high_rate,COALESCE((SELECT SUM(p.units) FROM usage_events p WHERE p.account=e.account AND p.kind='use' AND p.seq<e.seq AND p.seq>COALESCE((SELECT MAX(r.seq) FROM usage_events r WHERE r.account=e.account AND r.kind='reset' AND r.seq<e.seq),0)),0) AS prior FROM usage_events e JOIN accounts a ON a.id=e.account WHERE e.kind='use'), v AS (SELECT *,MIN(units,MAX(0,threshold-prior)) AS lo FROM u) SELECT account,id,lo,units-lo,lo*low_rate+(units-lo)*high_rate FROM v"}
        keys={'charges':['account','event']}
        spec='Each use event receives low tier units up to the account threshold minus earlier usage since the latest reset, then high tier units for the remainder. cost=low_units*low_rate+high_units*high_rate. Process authoritative seq, not arrival. Reset starts a new cumulative period and has no charge row. Units and rates are positive; late arrivals can change earlier-period marginal allocation but not cross reset boundaries.'
        evidence=['A late pre-reset event was charged at the low rate and also polluted the next period total.', 'accounts + usage_events -> charges; work -> charges']
        future={'usage_events':tables['usage_events']+[[n('e6'),n('a'),5,'use',10+q,6]],'work':[[n('a')]]}
        dirty={'charges':{}} # composite-key damage below
        wrong={'all_low_tier':"UPDATE charges SET low_units=low_units+high_units,high_units=0,cost=(low_units+high_units)*(SELECT low_rate FROM accounts WHERE id=charges.account);", 'forget_reset':"UPDATE charges SET low_units=0,high_units=(SELECT units FROM usage_events WHERE id=charges.event),cost=(SELECT units FROM usage_events WHERE id=charges.event)*(SELECT high_rate FROM accounts WHERE id=charges.account) WHERE event IN (SELECT id FROM usage_events WHERE seq>3);"}
    elif case_id=='H20':
        family='ordered_state';title='RangeSuture: a retroactive correction overwrote a later explicit interval override'
        schema='''CREATE TABLE days(entity TEXT,day INTEGER,PRIMARY KEY(entity,day));
CREATE TABLE changes(id TEXT PRIMARY KEY,entity TEXT,lo INTEGER,hi INTEGER,seq INTEGER,value INTEGER);
CREATE TABLE intervals(entity TEXT,lo INTEGER,hi INTEGER,value INTEGER,PRIMARY KEY(entity,lo));'''
        tables={'days':[[n('a'),i] for i in range(8)]+[[n('b'),i] for i in range(2)],
                'changes':[[n('base'),n('a'),0,8,1,10+q],[n('retro'),n('a'),2,7,2,20+q],[n('override'),n('a'),4,6,3,30+q],[n('bbase'),n('b'),0,2,1,5]]}
        queries={'intervals':"WITH v AS (SELECT d.entity,d.day,(SELECT value FROM changes c WHERE c.entity=d.entity AND c.lo<=d.day AND d.day<c.hi ORDER BY seq DESC LIMIT 1) AS value FROM days d), g AS (SELECT *,day-ROW_NUMBER() OVER(PARTITION BY entity,value ORDER BY day) AS grp FROM v) SELECT entity,MIN(day),MAX(day)+1,value FROM g GROUP BY entity,value,grp"}
        keys={'intervals':['entity','lo']}
        spec='Days are consecutive integer slots per entity, covered by at least one change. A change applies to half-open [lo,hi). For each day choose the highest-seq covering change; later explicit overrides survive retroactive corrections with lower seq. Materialize maximal contiguous intervals of equal value, coalescing adjacent equal values but never across gaps with another value. Store half-open endpoints. seq is unique per entity.'
        evidence=['A historical correction replaced an entire interval without splitting around a later override.', 'days + changes -> intervals; work -> intervals']
        future={'changes':tables['changes']+[[n('later'),n('a'),4,6,4,20+q]],'work':[[n('a')]]}
        dirty={'intervals':{}}
        wrong={'overwrite_later_override':"UPDATE intervals SET value=(SELECT value FROM changes c WHERE c.entity=intervals.entity AND c.seq=2) WHERE entity IN (SELECT entity FROM changes WHERE seq=2) AND lo>=2 AND hi<=7;", 'merge_disjoint_equal_values':"DELETE FROM intervals; INSERT INTO intervals SELECT entity,MIN(lo),MAX(hi),value FROM changes GROUP BY entity,value;"}
    elif case_id=='H22':
        family='evidence_adjudication';title='EntityVerdict: rejected duplicate candidates bridged distinct customers'
        schema='''CREATE TABLE entities(id TEXT PRIMARY KEY);
CREATE TABLE links(id TEXT PRIMARY KEY,a TEXT,b TEXT,decision TEXT);
CREATE TABLE canonical(entity TEXT PRIMARY KEY,representative TEXT,members INTEGER);'''
        tables={'entities':[[n(x)] for x in ['a','b','c','d','e']],
                'links':[[n('l1'),n('a'),n('b'),'accepted'],[n('l2'),n('b'),n('c'),'accepted'],[n('l3'),n('c'),n('d'),'rejected'],[n('l4'),n('d'),n('e'),'pending']]}
        queries={'canonical':"WITH RECURSIVE edges(a,b) AS (SELECT a,b FROM links WHERE decision='accepted' UNION SELECT b,a FROM links WHERE decision='accepted'), reach(a,b) AS (SELECT id,id FROM entities UNION SELECT r.a,e.b FROM reach r JOIN edges e ON e.a=r.b) SELECT a AS entity,MIN(b),COUNT(*) FROM reach GROUP BY a"}
        keys={'canonical':['entity']}
        spec='Only accepted links establish undirected equivalence. Compute transitive components, with lexicographically smallest entity ID as representative and component size as members. Keep one row for every entity including singletons. Rejected and pending candidate links do not connect components. work expands to every member of components changed by adjudication.'
        evidence=['Candidate generation was mistaken for adjudication and a rejected bridge merged separate identities.', 'entities + links -> canonical; work -> canonical']
        future={'links':[[i,a,b,'accepted' if i==n('l4') else d] for i,a,b,d in tables['links']],'work':[[n('d')],[n('e')]]}
        dirty={'canonical':{n('d'):[n('a'),4]}}
        wrong={'candidates_are_equivalence':"DELETE FROM canonical; INSERT INTO canonical "+queries['canonical'].replace(" WHERE decision='accepted'",'')+';', 'direct_edges_only':"UPDATE canonical SET members=1+(SELECT COUNT(*) FROM links l WHERE l.decision='accepted' AND (l.a=canonical.entity OR l.b=canonical.entity));"}
    elif case_id=='H23':
        family='evidence_adjudication';title='FillMark: a processing cursor falsely certified event-time completeness'
        schema='''CREATE TABLE streams(id TEXT PRIMARY KEY);
CREATE TABLE partitions(stream TEXT,slot INTEGER,expected INTEGER,PRIMARY KEY(stream,slot));
CREATE TABLE events(id TEXT PRIMARY KEY,stream TEXT,slot INTEGER,accepted INTEGER,arrival INTEGER);
CREATE TABLE progress(stream TEXT PRIMARY KEY,processed INTEGER);
CREATE TABLE watermarks(stream TEXT PRIMARY KEY,complete_through INTEGER,accepted_count INTEGER);'''
        tables={'streams':[[n('a')],[n('b')]],'partitions':[[n('a'),1,2],[n('a'),2,1],[n('a'),3,1],[n('b'),1,1]],
                'events':[[n('e1'),n('a'),1,1,1],[n('e2'),n('a'),2,1,2],[n('e3'),n('a'),3,1,9],[n('bad'),n('a'),1,0,10],[n('e4'),n('b'),1,1,1]],
                'progress':[[n('a'),99],[n('b'),1]]}
        queries={'watermarks':"SELECT s.id AS stream,COALESCE((SELECT MIN(p.slot)-1 FROM partitions p WHERE p.stream=s.id AND (SELECT COUNT(*) FROM events e WHERE e.stream=p.stream AND e.slot=p.slot AND e.accepted=1)<>p.expected),(SELECT MAX(slot) FROM partitions p WHERE p.stream=s.id)),(SELECT COUNT(*) FROM events e WHERE e.stream=s.id AND e.accepted=1) FROM streams s"}
        keys={'watermarks':['stream']}
        spec='Partition slots are contiguous positive integers starting at one, with positive expected accepted-event counts. complete_through is the largest contiguous prefix whose slots each have exactly expected accepted events; zero when slot 1 is incomplete. accepted_count includes ALL accepted events, even beyond gaps and late arrivals. Event IDs are unique. progress.processed is processing progress, not evidence of event-time completeness. Rejected events never count.'
        evidence=['A high processing cursor masked a gap in the first event-time partition; accepted late events beyond the gap must survive.', 'streams + partitions + events -> watermarks; work -> watermarks']
        future={'events':tables['events']+[[n('late'),n('a'),1,1,100]],'work':[[n('a')]]}
        dirty={'watermarks':{n('a'):[3,4]}}
        wrong={'cursor_is_completeness':'UPDATE watermarks SET complete_through=(SELECT processed FROM progress WHERE stream=watermarks.stream);', 'drop_beyond_gap':'UPDATE watermarks SET accepted_count=0 WHERE complete_through=0;'}
    elif case_id=='H24':
        family='evidence_adjudication';title='EraseSafe: backup restoration revived erased subjects and dropped safe descendants'
        schema='''CREATE TABLE versions(id TEXT,revision INTEGER,subject TEXT,parent TEXT,payload TEXT,PRIMARY KEY(id,revision));
CREATE TABLE erasures(subject TEXT PRIMARY KEY);
CREATE TABLE restored(id TEXT PRIMARY KEY,revision INTEGER,parent TEXT,payload TEXT);'''
        tables={'versions':[[n('root'),1,n('redacted'),None,'private'],[n('child'),1,n('safe'),n('root'),'usable'],[n('edited'),1,n('safe'),None,'backup'],[n('edited'),2,n('safe'),None,'operator update'],[n('healthy'),1,n('other'),None,'kept']], 'erasures':[[n('redacted')]]}
        queries={'restored':"WITH latest AS (SELECT v.* FROM versions v WHERE NOT EXISTS(SELECT 1 FROM versions x WHERE x.id=v.id AND x.revision>v.revision)), safe AS (SELECT * FROM latest l WHERE NOT EXISTS(SELECT 1 FROM erasures e WHERE e.subject=l.subject)) SELECT s.id,s.revision,CASE WHEN EXISTS(SELECT 1 FROM safe p WHERE p.id=s.parent) THEN s.parent ELSE NULL END,s.payload FROM safe s"}
        keys={'restored':['id']}
        spec='versions combines backup versions and later authoritative edits. Select highest revision per ID, then exclude every record whose subject has an authoritative erasure. Subject is stable across versions. Erasure is by subject, not by subtree. Preserve nonerased descendants but set their parent NULL if that parent is absent after filtering. Retain their payloads and latest edits. This is a synthetic restore projection; immutable backup evidence remains an audit input, not a production erasure implementation.'
        evidence=['A snapshot restore resurrected an erased subject; a subtree delete would also lose a different subject child.', 'versions + erasures -> restored; work -> restored']
        future={'erasures':tables['erasures']+[[n('other')]],'versions':tables['versions']+[[n('child'),2,n('safe'),n('root'),'new child value']], 'work':[[n('healthy')],[n('child')]]}
        dirty={'restored':{n('child'):[1,n('root'),'usable'],n('edited'):[1,None,'backup']}}
        wrong={'restore_earliest_backup':"INSERT OR REPLACE INTO restored SELECT id,revision,parent,payload FROM versions WHERE revision=1;", 'erase_subtree':"DELETE FROM restored WHERE id IN (SELECT v.id FROM versions v JOIN versions p ON p.id=v.parent JOIN erasures e ON e.subject=p.subject);"}
    else:raise NotImplementedError(case_id)
    return finish(locals())


def damage(case_id,tables,d,seed):
    n=lambda x:f'{x}_{seed}';q=seed%5
    for table,changes in d['dirty'].items():
        for row in tables[table]:
            if row[0] in changes:row[1:]=copy.deepcopy(changes[row[0]])
    if case_id=='H10':
        for row in tables['coverage']:
            if row[0]==n('a') and row[1]>=3:row[2:]=[n('right'),2]
    elif case_id=='H14':
        tables['access'].append([n('bo'),n('read'),1])
    elif case_id=='H15':
        # Two membership keys for ana: change only counts, never collapse the key.
        tables['membership']=[r for r in tables['membership'] if r[0]!=n('ana')]+[[n('ana'),n('blue'),2]]
    elif case_id=='H19':
        for row in tables['charges']:
            if row[1]==n('e2'):row[2:]=[6+q,0,(6+q)*2]
    elif case_id=='H20':
        tables['intervals']=[r for r in tables['intervals'] if r[0]!=n('a')]+[[n('a'),0,2,10+q],[n('a'),2,7,20+q],[n('a'),7,8,10+q]]
    elif case_id=='H24':
        tables['restored'].append([n('root'),1,None,'private'])
    # Make coupled summary damage consistent with the damaged base projection.
    if case_id=='H06':
        states={i:(a,b,c) for i,a,b,c in tables['transfer_state']}
        tables['stock']=[[w,o-sum(states[i][0] for i,s,d,_,_ in tables['transfers'] if s==w)+sum(states[i][1] for i,s,d,_,_ in tables['transfers'] if d==w)] for w,o in tables['warehouses']]
    if case_id=='H08':
        committed={t:c for t,c,_ in tables['escrow']}
        tables['pool_free']=[[p,cap-sum(committed[t] for t,pool,_ in tables['tenants'] if pool==p)] for p,cap in tables['pools']]


def oracle(case_id,t):
    """No SQL, reference-query execution, or dependency on damaged projections."""
    if case_id=='H02':
        accepted={e for _,e,o in t['attempts'] if o=='committed'};rows=[]
        for entity,initial in t['entities']:
            ev=sorted((e for e in t['events'] if e[1]==entity and e[0] in accepted),key=lambda e:e[2])
            rows.append([entity,ev[-1][3] if ev else initial,ev[-1][2] if ev else 0])
        return {'applied':rows}
    if case_id=='H03':
        parents=dict(t['parents']);done={s for s,a in t['undo_receipts'] if a};rows=[]
        for s,p,state,cost in t['steps']:
            undo=parents[p]=='canceled' and state=='completed'
            rows.append([s,('done' if s in done else 'pending') if undo else 'none',cost if undo else 0])
        return {'compensation':rows}
    if case_id=='H04':
        rows=[]
        for job,gen,fence,owner in t['leases']:
            valid=sorted((c for c in t['completions'] if c[1:5]==[job,gen,fence,owner]),key=lambda c:c[5])
            rows.append([job,'done' if valid else 'pending',valid[-1][6] if valid else 0])
        return {'job_results':rows}
    if case_id=='H06':
        balances=dict(t['warehouses']);rows=[]
        for ident,source,destination,qty,accepted in t['transfers']:
            debit=qty if accepted else 0;credit=sum(r[2] for r in t['receipts'] if r[1]==ident and r[3]) if accepted else 0
            rows.append([ident,debit,credit,debit-credit]);balances[source]-=debit;balances[destination]+=credit
        return {'transfer_state':rows,'stock':[[w,v] for w,v in balances.items()]}
    if case_id=='H07':
        replacement=dict(t['replacements']);rows=[]
        for line,ordered in t['lines']:
            ships={i:q for i,l,q in t['shipments'] if l==line};returns=[r for r in t['returns'] if r[1] in ships and r[3]]
            rows.append([line,ordered-sum(ships.values()),sum(ships.values())-sum(r[2] for r in returns),sum(r[2]-replacement.get(r[0],0) for r in returns)])
        return {'line_state':rows}
    if case_id=='H08':
        now=t['clock'][0][0];used={tenant:0 for tenant,_,_ in t['tenants']}
        for _,tenant,issued,consumed,expires in t['leases']:used[tenant]+=issued if expires>now else consumed
        return {'escrow':[[tenant,used[tenant],cap-used[tenant]] for tenant,_,cap in t['tenants']],
                'pool_free':[[p,cap-sum(used[tenant] for tenant,pool,_ in t['tenants'] if pool==p)] for p,cap in t['pools']]}
    if case_id=='H10':
        rows=[]
        for ds,pos in t['slots']:
            best=max((f for f in t['segments'] if f[1]==ds and f[2]<=pos<f[3] and f[5]),key=lambda f:f[4])
            rows.append([ds,pos,best[0],best[4]])
        return {'coverage':rows}
    if case_id=='H11':
        defaults=dict(t['defaults']);rows=[]
        for ident,epoch,present,value in t['documents']:
            edits=sorted((e for e in t['edits'] if e[0]==ident),key=lambda e:e[1])
            if edits:rows.append([ident,edits[-1][2],'operator',edits[-1][1]])
            else:rows.append([ident,value if present else defaults[epoch],'stored' if present else 'default',0])
        return {'migrated':rows}
    if case_id=='H12':
        rows=[]
        for key,gen,active in t['objects']:
            valid=sorted((m for m in t['materializations'] if m[1:3]==[key,gen] and m[5]),key=lambda m:m[3])
            if active and valid:rows.append([key,gen,valid[-1][4],valid[-1][3]])
        return {'cache':rows}
    if case_id=='H14':
        nodes={r[0]:r for r in t['delegations']};counts={}
        for ident,parent,user,resource,revoked in t['delegations']:
            cur=ident;valid=True
            while cur is not None:
                row=nodes[cur];valid=valid and not row[4];cur=row[1]
            if valid:counts[user,resource]=counts.get((user,resource),0)+1
        return {'access':[[u,r,c] for (u,r),c in sorted(counts.items())]}
    if case_id=='H15':
        counts={}
        for ident,user,origin,kind,active in t['assignments']:
            if not active:continue
            targets=[origin] if kind=='direct' else [target for a,target,accepted in t['routing'] if a==ident and accepted]
            for target in targets:counts[user,target]=counts.get((user,target),0)+1
        return {'membership':[[u,g,c] for (u,g),c in sorted(counts.items())]}
    if case_id=='H16':
        nodes={r[0]:r for r in t['capabilities']};rows=[]
        for ident,parent,mask,expiry in t['capabilities']:
            while parent is not None:
                _,parent,pm,pe=nodes[parent];mask &= pm;expiry=min(expiry,pe)
            if mask and expiry>t['clock'][0][0]:rows.append([ident,mask,expiry])
        return {'effective':rows}
    if case_id=='H18':
        quantities={(r,v):q for r,v,q in t['versions']};rows=[]
        for (ident,) in t['reservations']:
            current=None;qty=0
            for _,r,seq,version,kind in sorted(t['actions'],key=lambda a:a[2]):
                if r!=ident:continue
                if kind=='activate':current=version;qty=quantities[r,version]
                elif version==current:qty=0 if kind=='cancel' else quantities[r,version]
            rows.append([ident,current,qty])
        return {'allocation':rows}
    if case_id=='H19':
        rows=[]
        for account,threshold,low,high in t['accounts']:
            used=0
            for ident,a,seq,kind,units,_ in sorted(t['usage_events'],key=lambda r:r[2]):
                if a!=account:continue
                if kind=='reset':used=0;continue
                lo=min(units,max(0,threshold-used));rows.append([account,ident,lo,units-lo,lo*low+(units-lo)*high]);used+=units
        return {'charges':rows}
    if case_id=='H20':
        rows=[]
        for entity in sorted({r[0] for r in t['days']}):
            run=None
            for day in sorted(d for e,d in t['days'] if e==entity):
                value=max((c for c in t['changes'] if c[1]==entity and c[2]<=day<c[3]),key=lambda c:c[4])[5]
                if run is not None and run[2]==day and run[3]==value:run[2]=day+1
                else:
                    run=[entity,day,day+1,value];rows.append(run)
        return {'intervals':rows}
    if case_id=='H22':
        adjacency={i:set() for (i,) in t['entities']}
        for _,a,b,decision in t['links']:
            if decision=='accepted':adjacency[a].add(b);adjacency[b].add(a)
        rows=[]
        for entity in adjacency:
            todo=[entity];seen=set()
            while todo:
                i=todo.pop()
                if i in seen:continue
                seen.add(i);todo.extend(adjacency[i]-seen)
            rows.append([entity,min(seen),len(seen)])
        return {'canonical':rows}
    if case_id=='H23':
        rows=[]
        for (stream,) in t['streams']:
            counts={}
            for _,s,slot,accepted,_ in t['events']:
                if s==stream and accepted:counts[slot]=counts.get(slot,0)+1
            through=0
            for _,slot,expected in sorted((p for p in t['partitions'] if p[0]==stream),key=lambda p:p[1]):
                if counts.get(slot,0)!=expected:break
                through=slot
            rows.append([stream,through,sum(counts.values())])
        return {'watermarks':rows}
    if case_id=='H24':
        latest={};erased={s for (s,) in t['erasures']}
        for row in t['versions']:
            if row[0] not in latest or row[1]>latest[row[0]][1]:latest[row[0]]=row
        safe={i:r for i,r in latest.items() if r[2] not in erased}
        return {'restored':[[i,rev,parent if parent in safe else None,payload] for i,rev,_,parent,payload in safe.values()]}
    raise NotImplementedError(case_id)
