"""Private case construction and independent Python oracles. Never exposed as tools."""
import datetime as dt
import sqlite3


def rows(db, table):
    return sorted([list(r) for r in db.execute(f'SELECT * FROM "{table}"')], key=repr)


def build(kind, seed=0, healthy=False):
    """Seeds perturb values/identifiers; they are NOT independent research scenarios."""
    db = sqlite3.connect(':memory:')
    suffix = f'-{seed}' if seed else ''
    n = seed * 37
    def put(table, values):
        if values:
            db.executemany(f'INSERT INTO {table} VALUES ({",".join("?" for _ in values[0])})', values)

    if kind == 'billing':
        title = 'HarborDesk: webhook retries after a payment-worker deployment'
        schema = '''CREATE TABLE deliveries(id TEXT PRIMARY KEY, request_id TEXT, account TEXT, cents INTEGER, received_at TEXT);
CREATE TABLE refunds(id TEXT PRIMARY KEY, account TEXT, cents INTEGER, reason TEXT);
CREATE TABLE charges(delivery_id TEXT PRIMARY KEY, request_id TEXT, account TEXT, cents INTEGER);
CREATE TABLE balances(account TEXT PRIMARY KEY, cents INTEGER);'''
        db.executescript(schema)
        ds = [('d01'+suffix,'order-A','north',10000+n,'2026-10-01T10:00:00'),
              ('d02'+suffix,'order-A','north',10000+n,'2026-10-01T10:01:00'),
              ('d03'+suffix,'order-B','north',10000+n,'2026-10-01T10:02:00'),
              ('d04'+suffix,'order-C','south',7000+n,'2026-10-01T10:03:00'),
              ('d05'+suffix,'order-C','south',7000+n,'2026-10-01T10:04:00'),
              ('d06'+suffix,'order-D','west',4200+n,'2026-10-02T09:00:00')]
        rf = [('r01','north',-2000,'approved partial refund at 11:00'),('r02','south',-1000,'approved refund next day')]
        put('deliveries',ds); put('refunds',rf)
        tail = '''DELETE FROM balances;
INSERT INTO balances SELECT account,SUM(cents) FROM
(SELECT account,cents FROM charges UNION ALL SELECT account,cents FROM refunds) GROUP BY account;'''
        good = '''INSERT OR IGNORE INTO charges SELECT id,request_id,account,cents FROM deliveries d
WHERE NOT EXISTS(SELECT 1 FROM deliveries e WHERE e.request_id=d.request_id AND
(e.received_at<d.received_at OR (e.received_at=d.received_at AND e.id<d.id)));
''' + tail
        bad = 'INSERT OR IGNORE INTO charges SELECT id,request_id,account,cents FROM deliveries;\n' + tail
        recovery = 'DELETE FROM charges;\n' + good
        chosen = {}
        for d in sorted(ds,key=lambda x:(x[4],x[0])): chosen.setdefault(d[1],d)
        ec = [[d[0],d[1],d[2],d[3]] for d in chosen.values()]
        totals = {}
        for d in ec: totals[d[2]]=totals.get(d[2],0)+d[3]
        for r in rf: totals[r[1]]=totals.get(r[1],0)+r[2]
        expected={'charges':ec,'balances':[[a,v] for a,v in totals.items()]}
        writable=['charges','balances']; immutable=['deliveries','refunds']
        spec = ('One canonical charge per request_id: earliest received_at, then smallest id. Distinct request_ids are '
                'distinct purchases even if amounts/accounts match. Charges and balances are rebuildable projections; '
                'deliveries and refunds are immutable. Balances equal canonical charges plus signed refunds. '
                'Refunds were approved after the faulty interval and must survive. Source processing must be repeatable.')
        evidence = ['worker v1 keyed by request; v2 keyed by delivery; historical retries appear twice',
                    'deliveries -> charges -> balances; refunds -> balances',
                    'request order-B is a separate legitimate purchase, not a retry of order-A']
    elif kind == 'rounding':
        title='MeterLake: usage accrual drift at half-cent boundaries'
        schema='''CREATE TABLE usage(id TEXT PRIMARY KEY,account TEXT,amount_micros INTEGER,run_id TEXT);
CREATE TABLE credits(id TEXT PRIMARY KEY,account TEXT,cents INTEGER,reason TEXT);
CREATE TABLE accruals(id TEXT PRIMARY KEY,account TEXT,cents INTEGER);
CREATE TABLE balances(account TEXT PRIMARY KEY,cents INTEGER);'''
        db.executescript(schema)
        us=[('u1'+suffix,'alpha',125000+seed*10000,'before'),('u2'+suffix,'alpha',15000+seed*10000,'deploy-42'),
            ('u3'+suffix,'beta',9999+seed*10000,'deploy-42'),('u4'+suffix,'beta',20000+seed*10000,'after'),
            ('u5'+suffix,'gamma',4999+seed*10000,'deploy-42'),('u6'+suffix,'gamma',5000+seed*10000,'deploy-42')]
        cr=[('c1','alpha',-3,'later SLA credit'),('c2','beta',-1,'later service credit')]
        put('usage',us);put('credits',cr)
        tail='''DELETE FROM balances;
INSERT INTO balances SELECT account,SUM(cents) FROM
(SELECT account,cents FROM accruals UNION ALL SELECT account,cents FROM credits) GROUP BY account;'''
        good='INSERT OR REPLACE INTO accruals SELECT id,account,(amount_micros+5000)/10000 FROM usage;\n'+tail
        bad='INSERT OR REPLACE INTO accruals SELECT id,account,amount_micros/10000 FROM usage;\n'+tail
        recovery=good
        ec=[[u[0],u[1],divmod(u[2],10000)[0]+int(divmod(u[2],10000)[1]>=5000)] for u in us]
        totals={}
        for _,a,v in ec: totals[a]=totals.get(a,0)+v
        for _,a,v,_ in cr: totals[a]=totals.get(a,0)+v
        expected={'accruals':ec,'balances':[[a,v] for a,v in totals.items()]}
        writable=['accruals','balances'];immutable=['usage','credits']
        spec=('All usage amounts are nonnegative integer microdollars; 10,000 microdollars equal one cent. '
              'Round each usage record independently to the nearest cent, with exact half cents rounding upward. '
              'Accruals are rebuildable; balances are rounded accruals plus signed approved credits. '
              'The credits were approved after deployment and are immutable. Never round only the account aggregate.')
        evidence=['deploy-42 replaced decimal HALF_UP with integer truncation',
                  'usage -> accruals -> balances; credits -> balances','u4 is an exact-cent healthy control']
    elif kind == 'ownership':
        title='FieldRoute: commissions attributed to the current owner instead of the sale-time owner'
        schema='''CREATE TABLE ownership(account TEXT,valid_from TEXT,valid_to TEXT,owner TEXT,bps INTEGER,PRIMARY KEY(account,valid_from));
CREATE TABLE sales(id TEXT PRIMARY KEY,account TEXT,sold_at TEXT,cents INTEGER);
CREATE TABLE commissions(sale_id TEXT PRIMARY KEY,owner TEXT,cents INTEGER);
CREATE TABLE owner_totals(owner TEXT PRIMARY KEY,cents INTEGER);'''
        db.executescript(schema)
        hs=[('acme','2026-01-01','2026-10-05','Ira',500),('acme','2026-10-05','2027-01-01','Noor',700),
            ('beacon','2026-01-01','2027-01-01','Ira',400)]
        ss=[('s1'+suffix,'acme','2026-10-04',10000+n),('s2'+suffix,'acme','2026-10-05',20000+n),
            ('s3'+suffix,'beacon','2026-10-06',15000+n),('s4'+suffix,'acme','2026-09-30',5000+n)]
        put('ownership',hs);put('sales',ss)
        tail='DELETE FROM owner_totals; INSERT INTO owner_totals SELECT owner,SUM(cents) FROM commissions GROUP BY owner;'
        good='''INSERT OR REPLACE INTO commissions SELECT s.id,h.owner,s.cents*h.bps/10000 FROM sales s
JOIN ownership h ON s.account=h.account AND s.sold_at>=h.valid_from AND s.sold_at<h.valid_to;
'''+tail
        bad='''INSERT OR REPLACE INTO commissions SELECT s.id,h.owner,s.cents*h.bps/10000 FROM sales s
JOIN ownership h ON s.account=h.account WHERE h.valid_from=(SELECT MAX(valid_from) FROM ownership WHERE account=s.account);
'''+tail
        recovery=good
        ec=[]
        for sid,a,when,amount in ss:
            h=next(x for x in hs if x[0]==a and x[1]<=when<x[2]);ec.append([sid,h[3],amount*h[4]//10000])
        totals={}
        for _,a,v in ec:totals[a]=totals.get(a,0)+v
        expected={'commissions':ec,'owner_totals':[[a,v] for a,v in totals.items()]}
        writable=['commissions','owner_totals'];immutable=['ownership','sales']
        spec=('Ownership intervals never overlap and cover every sale. Use sale-time ownership with valid_from inclusive '
              'and valid_to exclusive; commission cents are floor(sale cents * basis points / 10000). '
              'Rebuild owner totals from commissions. Later account transfers must not rewrite historical attribution. '
              'Sales and ownership history are immutable; commissions and totals are rebuildable projections.')
        evidence=['a later account transfer triggered a rebuild using the latest owner dimension',
                  'sales + ownership intervals -> commissions -> owner_totals',
                  'sale s2 is exactly on a transfer boundary']
    elif kind == 'cdc':
        title='ShelfSearch: deleted products resurrected by a CDC replay'
        schema='''CREATE TABLE changes(tenant TEXT,sku TEXT,seq INTEGER,op TEXT,title TEXT,PRIMARY KEY(tenant,sku,seq));
CREATE TABLE holds(id TEXT PRIMARY KEY,tenant TEXT,sku TEXT,reason TEXT);
CREATE TABLE catalog(tenant TEXT,sku TEXT,title TEXT,PRIMARY KEY(tenant,sku));'''
        db.executescript(schema)
        cs=[('north','A',1,'UPSERT','Lamp'),('north','A',2,'DELETE',None),
            ('north','B',1,'UPSERT','Desk'),('north','B',2,'DELETE',None),('north','B',3,'UPSERT','Desk restored'+suffix),
            ('south','A',1,'UPSERT','Chair'+suffix),('south','C',1,'UPSERT','Shelf'),('south','C',2,'UPSERT','Shelf XL')]
        put('changes',cs);put('holds',[('h1','north','A','retain fulfillment history after delisting')])
        good='''DELETE FROM catalog;
INSERT INTO catalog SELECT c.tenant,c.sku,c.title FROM changes c WHERE c.seq=
(SELECT MAX(e.seq) FROM changes e WHERE e.tenant=c.tenant AND e.sku=c.sku) AND c.op='UPSERT';'''
        bad='''DELETE FROM catalog;
INSERT INTO catalog SELECT c.tenant,c.sku,c.title FROM changes c WHERE c.seq=
(SELECT MAX(e.seq) FROM changes e WHERE e.tenant=c.tenant AND e.sku=c.sku AND e.op='UPSERT') AND c.op='UPSERT';'''
        recovery=good
        last={}
        for c in sorted(cs,key=lambda x:x[2]):last[(c[0],c[1])]=c
        expected={'catalog':[[c[0],c[1],c[4]] for c in last.values() if c[3]=='UPSERT']}
        writable=['catalog'];immutable=['changes','holds']
        spec=('The latest seq per (tenant,sku) determines current state. DELETE means absent from catalog; a later UPSERT '
              'recreates the item. Tenants have independent SKU namespaces. Catalog is a rebuildable projection. '
              'Changes and fulfillment holds are immutable; deleting a catalog item must not remove its hold.')
        evidence=['replay code discarded tombstones before ranking events','changes -> catalog; holds retained separately',
                  'north/B was intentionally recreated after deletion; south/A is unrelated to north/A']
    elif kind == 'timezone':
        title='DayLedger: midnight revenue assigned to the wrong business day'
        schema='''CREATE TABLE events(id TEXT PRIMARY KEY,occurred_at TEXT,cents INTEGER);
CREATE TABLE adjustments(id TEXT PRIMARY KEY,business_day TEXT,cents INTEGER,reason TEXT);
CREATE TABLE daily_totals(day TEXT PRIMARY KEY,cents INTEGER);'''
        db.executescript(schema)
        es=[('e1'+suffix,'2026-10-01T18:29:59Z',1000+n),('e2'+suffix,'2026-10-01T18:30:00Z',2000+n),
            ('e3'+suffix,'2026-10-01T23:59:59Z',3000+n),('e4'+suffix,'2026-10-02T00:00:00Z',-500),
            ('e5'+suffix,'2026-10-03T12:00:00Z',4000+n)]
        adj=[('a1','2026-10-02',-125,'later approved reconciliation'),('a2','2026-10-04',50,'adjustment-only day')]
        put('events',es);put('adjustments',adj)
        tail=" UNION ALL SELECT business_day,cents FROM adjustments) GROUP BY d;"
        good="DELETE FROM daily_totals; INSERT INTO daily_totals SELECT d,SUM(cents) FROM (SELECT date(occurred_at,'+330 minutes') d,cents FROM events"+tail
        bad="DELETE FROM daily_totals; INSERT INTO daily_totals SELECT d,SUM(cents) FROM (SELECT date(occurred_at) d,cents FROM events"+tail
        recovery=good
        totals={}
        for _,when,amount in es:
            day=(dt.datetime.fromisoformat(when.replace('Z','+00:00'))+dt.timedelta(minutes=330)).date().isoformat()
            totals[day]=totals.get(day,0)+amount
        for _,day,amount,_ in adj:totals[day]=totals.get(day,0)+amount
        expected={'daily_totals':[[day,v] for day,v in totals.items()]}
        writable=['daily_totals'];immutable=['events','adjustments']
        spec=('Business timezone is fixed UTC+05:30 (no DST). Assign every signed event to its local calendar day, '
              'then add adjustments already labeled by business_day. Include adjustment-only days. Events and '
              'adjustments are immutable; daily_totals is a rebuildable projection. Refund events are signed negative values.')
        evidence=['UTC grouping introduced in daily rebuild; local midnight is 18:30 UTC',
                  'events -> local day -> daily_totals; adjustments -> daily_totals','later adjustments must remain applied exactly once']
    elif kind == 'inventory':
        title='ParcelStock: interrupted inventory posting after a shipment commit'
        schema='''CREATE TABLE opening(warehouse TEXT,sku TEXT,qty INTEGER,PRIMARY KEY(warehouse,sku));
CREATE TABLE movements(id TEXT PRIMARY KEY,warehouse TEXT,sku TEXT,delta INTEGER,status TEXT,reason TEXT);
CREATE TABLE stock(warehouse TEXT,sku TEXT,qty INTEGER,PRIMARY KEY(warehouse,sku));
CREATE TABLE applied(movement_id TEXT PRIMARY KEY);'''
        db.executescript(schema)
        op=[('east','A',100+seed),('west','A',40+seed),('east','B',30+seed)]
        ms=[('m1'+suffix,'east','A',-10,'committed','shipment before crash'),
            ('m2'+suffix,'east','A',3,'committed','legitimate later return'),
            ('m3'+suffix,'east','A',20,'committed','later replenishment'),
            ('m4'+suffix,'east','A',-5,'pending','uncommitted reservation'),
            ('m5'+suffix,'west','A',-4,'committed','different warehouse shipment'),
            ('m6'+suffix,'east','B',-2,'cancelled','cancelled request')]
        put('opening',op);put('movements',ms);put('stock',op)
        good='''INSERT OR REPLACE INTO stock SELECT o.warehouse,o.sku,o.qty+COALESCE((SELECT SUM(delta) FROM movements m
WHERE m.warehouse=o.warehouse AND m.sku=o.sku AND m.status='committed'),0) FROM opening o;
DELETE FROM applied; INSERT INTO applied SELECT id FROM movements WHERE status='committed';'''
        bad='''INSERT OR IGNORE INTO applied SELECT id FROM movements WHERE status='committed';
UPDATE stock SET qty=qty+COALESCE((SELECT SUM(delta) FROM movements m WHERE m.warehouse=stock.warehouse
AND m.sku=stock.sku AND m.status='committed' AND m.id NOT IN (SELECT movement_id FROM applied)),0);'''
        recovery=good
        ec=[]
        for w,sku,qty in op:ec.append([w,sku,qty+sum(m[3] for m in ms if m[1:3]==(w,sku) and m[4]=='committed')])
        expected={'stock':ec,'applied':[[m[0]] for m in ms if m[4]=='committed']}
        writable=['stock','applied'];immutable=['opening','movements']
        spec=('Opening is the authoritative start-of-window stock. Stock must equal opening plus all committed signed '
              'movements per warehouse and SKU. Pending/cancelled movements do not affect stock. Applied must contain '
              'exactly committed movement IDs. Opening/movements are immutable; stock/applied can be rebuilt. '
              'Later returns and replenishments must survive recovery. Processing and recovery must be repeatable.')
        evidence=['interruption occurred after applied marker insertion but before stock update',
                  'opening + committed movements -> stock; committed movements -> applied',
                  'return m2 and replenishment m3 posted after the missed shipment']
    else:
        raise ValueError(kind)
    db.executescript(good if healthy else bad)
    # Simulate legitimate post-incident activity already reflected in stock.
    if kind=='inventory' and not healthy:
        db.execute("UPDATE stock SET qty=qty+23 WHERE warehouse='east' AND sku='A'")
        db.execute("UPDATE stock SET qty=qty-4 WHERE warehouse='west' AND sku='A'")
    # Before/after rows were written by healthy versions; only the middle deployment was defective.
    if kind=='rounding' and not healthy:
        db.execute("UPDATE accruals SET cents=(SELECT (amount_micros+5000)/10000 FROM usage WHERE usage.id=accruals.id) WHERE id IN (SELECT id FROM usage WHERE run_id IN ('before','after'))")
        db.executescript(tail)
    db.commit()
    names=immutable+writable
    public={'id':kind,'title':title,'specification':spec,'schema':schema,'application_sql':bad,
            'writable_tables':writable,'immutable_tables':immutable,
            'tables':{t:rows(db,t) for t in names},'evidence':evidence}
    # Independently computed oracle is never included in public task material.
    private={'expected':expected,'reference_application':good,'reference_recovery':recovery}
    db.close()
    return public, private


KINDS=['billing','rounding','ownership','cdc','timezone','inventory']
