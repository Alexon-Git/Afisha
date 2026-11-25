"""Structured prices, legacy compatibility and exact storage on isolated DBs."""
from decimal import Decimal

from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from app.database import Base
from app.models import Event
from test_event_metadata_migration import upgrade
from test_event_time_contract import time_database, process_zone

CASES = [
    ({'price_kind':'unknown'}, None), ({'price_kind':'free'}, 0),
    ({'price_kind':'by_request'}, None),
    ({'price_kind':'fixed','price_amount':'1500','currency':'RUB'},1500),
    ({'price_kind':'fixed','price_amount':'1500.50','currency':'RUB'},None),
    ({'price_kind':'fixed','price_amount':'20.50','currency':'USD'},None),
    ({'price_kind':'from','price_amount':'1000','currency':'RUB'},None),
    ({'price_kind':'range','price_amount':'1000','price_max':'2500.1234','currency':'RUB'},None),
    ({'price_kind':'fixed','price_amount':'99999999999999.9999','currency':'JPY'},None),
]

@pytest.mark.parametrize('pricing,legacy', CASES)
def test_all_kinds_and_exact_response(event_api, pricing, legacy):
    r=event_api.post('/events/',json={'title':'Pricing','datetime':'2026-11-26T03:00:00Z','location':'NSK',**pricing})
    assert r.status_code==200,r.text
    data=r.json()
    assert data['price']==legacy and data['price_kind']==pricing['price_kind']
    if pricing.get('price_amount'):
        assert isinstance(data['price_amount'],str)
        assert Decimal(data['price_amount'])==Decimal(pricing['price_amount'])
    assert event_api.get('/admin/events/').status_code==200

@pytest.mark.parametrize('pricing', [
    {'price_kind':'fixed'}, {'price_kind':'bogus'}, {'price_kind':None},
    {'price_kind':'free','price_amount':'1'}, {'price_kind':'unknown','currency':'USD'},
    {'price_kind':'by_request','price_max':'1'},
    *[{'price_kind':'fixed','price_amount':x,'currency':'RUB'} for x in ['-1','0','NaN','Infinity','100000000000000','1.12345',1.5]],
    {'price_kind':'fixed','price_amount':'1','currency':'ABC'},
    {'price_kind':'range','price_amount':'10','price_max':'9','currency':'EUR'},
    {'price_kind':'fixed','price_amount':'1','price_max':'2','currency':'RUB'},
    {'price_kind':'free','price':1500}, {'price_kind':'fixed','price_amount':'10','currency':'USD','price':10},
])
def test_bad_post_and_update_are_atomic(event_api,event_sessions,pricing):
    payload={'title':'Invalid','datetime':'2026-11-26T03:00:00Z','location':'NSK',**pricing}
    assert event_api.post('/events/',json=payload).status_code==422
    assert event_api.put('/events/1',json={'title':'Should not change',**pricing}).status_code==422
    with event_sessions() as db:
        assert db.query(Event).count()==1 and db.get(Event,1).title=='Original'


def test_legacy_and_partial_conflicts(event_api):
    payload={'title':'Old client','datetime':'2026-11-26T03:00:00Z','location':'NSK','price':1500}
    r=event_api.post('/events/',json=payload); assert r.status_code==200,r.text
    path='/events/'+str(r.json()['id'])
    assert r.json()['price_kind']=='fixed' and r.json()['currency']=='RUB'
    assert event_api.put(path,json={'price':0}).json()['price_kind']=='free'
    assert event_api.put(path,json={'price':None}).json()['price_kind']=='unknown'
    complex_price={'price_kind':'range','price_amount':'1.2345','price_max':'5.6789','currency':'CHF'}
    assert event_api.put(path,json=complex_price).status_code==200
    # A stale full legacy payload may echo NULL but must not erase the range.
    r=event_api.put(path,json={'description':'Safe','price':None})
    assert r.status_code==200 and r.json()['price_kind']=='range'
    assert event_api.put(path,json={'price':0}).status_code==422
    assert event_api.put(path,json={'price_max':'0.5','title':'Lost'}).status_code==422
    assert event_api.put(path,json={'price_max':'9.9999'}).json()['price_amount']=='1.2345'
    assert event_api.put(path,json={'price_kind':'free','price':0}).json()['price_amount'] is None
    assert event_api.put(path,json={'price_kind':'fixed','price_amount':'3','currency':'USD','price':None}).status_code==200


def test_pricing_migration_and_orm(time_database):
    engine,url=time_database
    upgrade(url,'0007_event_end_at')
    with engine.begin() as c:
        for identifier, price in [(1,None),(2,0),(3,1500)]:
            c.execute(text("INSERT INTO events (id,title,datetime,location,price) VALUES (:id,'Legacy','2026-11-26 03:00:00+00:00','NSK',:price)"),{'id':identifier,'price':price})
    with engine.connect() as c:
        original = [dict(row) for row in c.execute(text('SELECT * FROM events ORDER BY id')).mappings()]
    table_id_sql = "SELECT 'events'::regclass::oid" if engine.dialect.name == 'postgresql' else "SELECT rootpage FROM sqlite_master WHERE name='events' AND type='table'"
    with engine.connect() as c: table_id = c.execute(text(table_id_sql)).scalar()
    upgrade(url,'head'); upgrade(url,'head')
    with engine.connect() as c: assert c.execute(text(table_id_sql)).scalar() == table_id
    with engine.connect() as c:
        rows = [dict(row) for row in c.execute(text('SELECT * FROM events ORDER BY id')).mappings()]
        assert [{k:v for k,v in row.items() if k not in {'price_kind','price_amount','price_max','currency'}} for row in rows] == original
    from sqlalchemy.orm import Session
    with Session(engine) as db:
        assert [(db.get(Event,i).price_kind,db.get(Event,i).price) for i in [1,2,3]]==[('unknown',None),('free',0),('fixed',1500)]
        assert db.get(Event,3).price_amount==Decimal(1500)
        # ORM writers use the same validation/sync as API, and preserve every digit.
        db.add(Event(id=4,title='Exact',datetime=db.get(Event,1).datetime,location='NSK',price_kind='fixed',price_amount=Decimal('99999999999999.9999'),currency='USD'))
        db.commit(); db.expire_all()
        assert db.get(Event,4).price_amount==Decimal('99999999999999.9999')
        db.get(Event,3).price=2000; db.commit()
        assert db.get(Event,3).price_amount==Decimal(2000)
    with engine.connect() as c:
        assert compare_metadata(MigrationContext.configure(c,opts={'compare_type':True,'compare_server_default':True}),Base.metadata)==[]
    for sql in ["UPDATE events SET price=42 WHERE id=2", "UPDATE events SET price_kind='fixed',currency=NULL WHERE id=3",
                "UPDATE events SET price_kind='what' WHERE id=1", "UPDATE events SET currency='ABC' WHERE id=3"]:
        with engine.connect() as c:
            tx=c.begin()
            with pytest.raises(IntegrityError): c.execute(text(sql))
            tx.rollback()


def test_published_pricing_keeps_editorial_contract(event_api,event_sessions):
    from app.models.organizer import Organizer
    with event_sessions.begin() as db:
        db.add(Organizer(id=1,name='Synthetic',public_contact='Synthetic public contact'))
    assert event_api.put('/events/1',json={'organizer_id':1,'event_url':'https://example.invalid/event','source':'https://example.invalid/source'}).status_code==200
    assert event_api.post('/admin/events/1/verify').status_code==200
    published=event_api.patch('/admin/events/1/publication',json={'publication_status':'published'}).json()
    r=event_api.put('/events/1',json={'price_kind':'range','price_amount':'100','price_max':'200','currency':'RUB'})
    assert r.status_code==200,r.text
    assert r.json()['verified_at']==published['verified_at'] and r.json()['publication_status']=='published'
    assert event_api.put('/events/1',json={'title':'Critical'}).status_code==422
    assert event_api.put('/events/1',json={'price':0}).status_code==422


def test_invalid_legacy_price_aborts_before_ddl(tmp_path):
    from sqlalchemy import create_engine, inspect
    import os, subprocess, sys
    url=f"sqlite:///{tmp_path/'legacy.db'}"
    upgrade(url,'0007_event_end_at')
    engine=create_engine(url)
    with engine.begin() as c:
        c.execute(text("INSERT INTO events (id,title,datetime,location,price) VALUES (1,'Bad','2026-11-26 03:00:00','NSK',-1)"))
    from test_event_metadata_migration import BACKEND
    result=subprocess.run([sys.executable,'-m','alembic','upgrade','head'],cwd=BACKEND,env=dict(os.environ,DATABASE_URL=url),capture_output=True,text=True)
    assert result.returncode!=0 and 'Invalid legacy prices' in result.stderr
    with engine.connect() as c:
        assert 'price_kind' not in {col['name'] for col in inspect(c).get_columns('events')}
        assert c.execute(text('SELECT price FROM events')).scalar()==-1
    engine.dispose()
