"""Synthetic API tests, with opt-in isolated PostgreSQL17 row-lock races."""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from threading import Barrier, Event as ThreadEvent

from fastapi.testclient import TestClient
import pytest
from sqlalchemy import delete, event, select, update
from sqlalchemy.orm import sessionmaker

from app.auth.auth import create_access_token
from app.database import get_db
from app.main import app
from app.models import CandidateMatch, Event, EventCandidate, ImportRun, ImportSource
from app.models.organizer import Organizer
from app.models.user import User
from test_import_schema import import_database

BASE = '/admin/import/candidates'
APPROVE = dict(expected_revision=1, time_decision='accept',
               organizer_decision='unresolved', match_decisions=[])
REJECT = dict(expected_revision=1, review_note='Outside editorial scope')


@pytest.fixture
def review_api(import_database):
    sessions = sessionmaker(bind=import_database)
    with sessions.begin() as db:
        db.add_all([User(id=2, username='reviewer', password_hash='synthetic', is_admin=True),
                    User(id=3, username='ordinary', password_hash='synthetic', is_admin=False),
                    Organizer(id=2, name='Synthetic organizer')])
        db.flush()
        for sid in (101, 102):
            db.add(ImportSource(id=sid, name='Synthetic', base_url=f'https://example.invalid/{sid}',
                base_origin='https://example.invalid', base_path=f'/{sid}',
                source_type='official_site', adapter_key='jsonld_html'))
        db.flush()
        runs = []
        for sid in (101,102):
            run = ImportRun(source_id=sid,requested_by=1,requested_url='https://example.invalid/',
                policy_version=1,adapter_version='test',idempotency_key=str(sid),request_fingerprint='a'*64)
            db.add(run)
            db.flush()
            runs.append(run.id)
        for cid,sid,runid,status in [(101,101,runs[0],'pending'),(102,101,runs[0],'needs_review'),(103,102,runs[1],'rejected')]:
            db.add(EventCandidate(id=cid,source_id=sid,first_run_id=runid,last_run_id=runid,
                source_url='https://example.invalid/event',canonical_source_url='https://example.invalid/event',
                source_item_key=str(cid),content_fingerprint='b'*64,title=f'Synthetic {cid}',
                start_at=datetime(2026,11,23,11,tzinfo=timezone.utc),time_resolution='explicit_offset',
                normalized_city='новосибирск' if cid != 103 else 'unknown',review_status=status,
                warnings=['test'],field_provenance={'title':'/name'},observed_payload={'title':str(cid)}))
    previous = app.dependency_overrides.copy()
    def session():
        with sessions() as db:
            yield db
    app.dependency_overrides[get_db] = session
    token = create_access_token({'sub':'synthetic'})
    try:
        with TestClient(app,headers={'Authorization':f'Bearer {token}'}) as client:
            yield client,sessions,runs
    finally:
        app.dependency_overrides.clear()
        app.dependency_overrides.update(previous)
        with sessions.begin() as db:
            for model in [CandidateMatch,EventCandidate,ImportRun,ImportSource]:
                db.execute(delete(model))
            db.execute(delete(Organizer).where(Organizer.id == 2))
            db.execute(delete(User).where(User.id.in_([2,3])))


@pytest.mark.parametrize('method,path', [('get',''),('get','/101'),('post','/101/approve'),('post','/101/reject')])
@pytest.mark.parametrize('identity,expected', [(None,403),('bad',401),('ordinary',403),('missing',401),('expired',401)])
def test_auth_every_endpoint(review_api,method,path,identity,expected):
    client,_,_ = review_api
    if identity is None:
        header = ''
    elif identity == 'bad':
        header = 'Bearer invalid'
    else:
        token = create_access_token({'sub':'synthetic' if identity == 'expired' else identity},
            timedelta(seconds=-10) if identity == 'expired' else None)
        header = f'Bearer {token}'
    kwargs = {'json':APPROVE if path.endswith('approve') else REJECT} if method == 'post' else {}
    assert client.request(method,BASE+path,headers={'Authorization':header},**kwargs).status_code == expected


def test_pagination_filters_full_detail(review_api):
    client,sessions,runs = review_api
    first = client.get(BASE,params={'page':1,'limit':2}).json()
    second = client.get(BASE,params={'page':2,'limit':2}).json()
    assert (first['total_items'],first['total_pages']) == (3,2)
    assert len(first['items']) == 2 and len(second['items']) == 1
    assert {x['id'] for x in first['items']}.isdisjoint(x['id'] for x in second['items'])
    for filters,ids in [({'source_id':101},{101,102}),({'run_id':str(runs[1])},{103}),
        ({'review_status':'needs_review'},{102}),
        ({'normalized_city':'новосибирск','source_id':101,'review_status':'pending'},{101})]:
        r = client.get(BASE,params=filters)
        assert r.status_code == 200 and {x['id'] for x in r.json()['items']} == ids
    assert client.get(BASE,params={'source_id':999}).json()['total_pages'] == 0
    assert client.get(BASE,params={'page':99}).json()['items'] == []
    with sessions.begin() as db:
        db.add(CandidateMatch(id=101,candidate_id=101,event_id=1,historical_event_id=1,
            score=Decimal('0.75'),reason_codes=['same_time'],candidate_revision=1,compared_event_fingerprint='c'*64))
    data = client.get(BASE+'/101').json()
    assert data['warnings'] == ['test'] and data['field_provenance'] == {'title':'/name'}
    assert data['observed_payload'] == {'title':'101'} and data['matches'][0]['score'] == '0.750000'
    assert client.get(BASE+'/999').status_code == 404
    for action,body in [('approve',APPROVE),('reject',REJECT)]:
        assert client.post(BASE+'/999/'+action,json=body).status_code == 404


@pytest.mark.parametrize('params',[{'page':0},{'limit':101},{'source_id':0},{'review_status':'published'},
    {'run_id':'bad'},{'normalized_city':'x'*256}])
def test_query_limits(review_api,params):
    assert review_api[0].get(BASE,params=params).status_code == 422


@pytest.mark.parametrize('action,body,status',[('approve',APPROVE,'approved'),('reject',REJECT,'rejected')])
@pytest.mark.parametrize('cid',[101,102])
def test_decisions_audit_repeats_no_event_changes(review_api,action,body,status,cid):
    client,sessions,_ = review_api
    with sessions() as db:
        before = [dict(x) for x in db.execute(select(Event.__table__)).mappings()]
    now = datetime.now(timezone.utc)
    r = client.post(f'{BASE}/{cid}/{action}',json=body)
    assert r.status_code == 200,r.text
    data = r.json()
    assert (data['review_status'],data['reviewed_by'],data['reviewed_revision'],data['revision']) == (status,1,1,1)
    assert datetime.fromisoformat(data['reviewed_at'].replace('Z','+00:00')) >= now
    with sessions() as db:
        c = db.get(EventCandidate,cid)
        assert c.review_status == status and c.linked_event_id is None
        assert c.review_note == body.get('review_note')
        assert [dict(x) for x in db.execute(select(Event.__table__)).mappings()] == before
        if action == 'approve':
            assert c.reviewed_payload['revision'] == 1 and c.reviewed_payload['time_decision'] == 'accept'
    for repeat,payload in [('approve',APPROVE),('reject',REJECT)]:
        assert client.post(f'{BASE}/{cid}/{repeat}',json=payload).status_code == 409
    assert client.get(f'{BASE}/{cid}').json() == data


@pytest.mark.parametrize('status',['approved','rejected','converted','linked'])
def test_terminal_statuses(review_api,status):
    client,sessions,_ = review_api
    with sessions.begin() as db:
        db.get(EventCandidate,101).review_status = status
    for action,body in [('approve',APPROVE),('reject',REJECT)]:
        assert client.post(BASE+'/101/'+action,json=body).status_code == 409


@pytest.mark.parametrize('action,body',[('approve',APPROVE),('reject',REJECT)])
def test_stale_revision_and_run_source_mismatch(review_api,action,body):
    client,sessions,runs = review_api
    with sessions.begin() as db:
        db.get(EventCandidate,101).revision = 2
    assert client.post(BASE+'/101/'+action,json=body).status_code == 409
    for field in ['first_run_id','last_run_id']:
        with sessions.begin() as db:
            db.get(EventCandidate,101).revision = 1
            setattr(db.get(EventCandidate,101),field,runs[1])
        assert client.post(BASE+'/101/'+action,json=body).status_code == 409
        with sessions.begin() as db:
            c = db.get(EventCandidate,101)
            assert c.review_status == 'pending' and c.reviewed_at is None
            setattr(c,field,runs[0])


@pytest.mark.parametrize('field,value',[('reviewed_by',2),('reviewed_at','2026-01-01T00:00:00Z'),
    ('reviewed_revision',1),('review_status','approved'),('source_id',102),('last_run_id','fake'),
    ('verified_at','2026-01-01T00:00:00Z'),('publication_status','published'),
    ('linked_event_id',1),('reviewed_payload',{'anything':True})])
def test_controlled_fields_forbidden(review_api,field,value):
    for action,body in [('approve',APPROVE),('reject',REJECT)]:
        assert review_api[0].post(BASE+'/101/'+action,json={**body,field:value}).status_code == 422


def test_explicit_decisions_and_rejection_reason(review_api):
    client,sessions,_ = review_api
    for body in [{},{**APPROVE,'expected_revision':True},{**APPROVE,'time_decision':'unresolved'},
        {**APPROVE,'organizer_decision':'accept_proposed'}]:
        assert client.post(BASE+'/101/approve',json=body).status_code == 422
    for note in ['', '  ', 'x'*2049]:
        assert client.post(BASE+'/101/reject',json={**REJECT,'review_note':note}).status_code == 422
    with sessions.begin() as db:
        c = db.get(EventCandidate,101)
        c.start_at = datetime(2026,11,23,11,tzinfo=timezone.utc)
        c.time_resolution = 'explicit_offset'
        c.proposed_organizer_id = 2
        db.add(CandidateMatch(id=101,candidate_id=101,event_id=1,historical_event_id=1,
            score=Decimal('0.7'),reason_codes=['test'],candidate_revision=1,compared_event_fingerprint='c'*64))
    assert client.post(BASE+'/101/approve',json=APPROVE).status_code == 409
    body = {**APPROVE,'time_decision':'accept','organizer_decision':'accept_proposed',
            'match_decisions':[{'match_id':101,'decision':'defer'}]}
    assert client.post(BASE+'/101/approve',json={**body,'match_decisions':[{'match_id':999,'decision':'defer'}]}).status_code == 409
    with sessions.begin() as db:
        db.get(CandidateMatch,101).candidate_revision = 2
    assert client.post(BASE+'/101/approve',json=body).status_code == 409
    with sessions.begin() as db:
        db.get(CandidateMatch,101).candidate_revision = 1
    r = client.post(BASE+'/101/approve',json=body)
    assert r.status_code == 200,r.text
    assert r.json()['matches'][0]['decision'] == 'suggested'


@pytest.mark.parametrize('actions',[('approve','approve'),('approve','reject'),('reject','reject')])
def test_postgresql_parallel_editors(review_api,import_database,actions):
    if import_database.dialect.name != 'postgresql':
        pytest.skip('PostgreSQL row-lock concurrency only')
    client,sessions,_ = review_api
    barrier = Barrier(2)
    def rendezvous(conn,cursor,statement,parameters,context,many):
        if 'FROM event_candidates' in statement and 'FOR UPDATE' in statement:
            barrier.wait(timeout=10)
    event.listen(import_database,'before_cursor_execute',rendezvous)
    def decide(item):
        i,action = item
        token = create_access_token({'sub':'synthetic' if i == 0 else 'reviewer'})
        return client.post(BASE+'/101/'+action,json=APPROVE if action == 'approve' else REJECT,
            headers={'Authorization':f'Bearer {token}'})
    try:
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(decide,enumerate(actions)))
    finally:
        event.remove(import_database,'before_cursor_execute',rendezvous)
    assert sorted(r.status_code for r in results) == [200,409]
    winner = next(i for i,r in enumerate(results) if r.status_code == 200)
    with sessions() as db:
        c = db.get(EventCandidate,101)
        assert c.reviewed_by == (1 if winner == 0 else 2)
        assert c.review_status == ('approved' if actions[winner] == 'approve' else 'rejected')
        assert c.reviewed_revision == 1 and db.query(Event).count() == 1


def test_postgresql_revision_change_while_waiting(review_api,import_database):
    if import_database.dialect.name != 'postgresql':
        pytest.skip('PostgreSQL row-lock concurrency only')
    client,sessions,_ = review_api
    attempting = ThreadEvent()
    def signal(conn,cursor,statement,parameters,context,many):
        if 'FROM event_candidates' in statement and 'FOR UPDATE' in statement:
            attempting.set()
    with sessions() as writer:
        writer.execute(update(EventCandidate).where(EventCandidate.id == 101).values(revision=2))
        event.listen(import_database,'before_cursor_execute',signal)
        try:
            with ThreadPoolExecutor(max_workers=1) as pool:
                future = pool.submit(client.post,BASE+'/101/approve',json=APPROVE)
                assert attempting.wait(timeout=10)
                writer.commit()
                response = future.result(timeout=10)
        finally:
            event.remove(import_database,'before_cursor_execute',signal)
    assert response.status_code == 409
    with sessions() as db:
        c = db.get(EventCandidate,101)
        assert c.revision == 2 and c.reviewed_at is None and c.review_status == 'pending'


def test_unresolved_time_linked_candidate_and_forged_admin_claim(review_api):
    client,sessions,_ = review_api
    token = create_access_token({'sub':'ordinary','is_admin':True})
    assert client.get(BASE,headers={'Authorization':f'Bearer {token}'}).status_code == 403
    with sessions.begin() as db:
        db.get(EventCandidate,101).time_resolution = 'ambiguous'
    assert client.post(BASE+'/101/approve',json=APPROVE).status_code == 422
    with sessions.begin() as db:
        c = db.get(EventCandidate,101)
        c.time_resolution = 'explicit_offset'
        c.linked_event_id = 1
        c.link_kind = 'existing'
    for action,body in [('approve',APPROVE),('reject',REJECT)]:
        assert client.post(BASE+'/101/'+action,json=body).status_code == 409


def test_commit_failure_rolls_back_entire_decision(review_api,monkeypatch):
    from sqlalchemy.exc import OperationalError
    from sqlalchemy.orm import Session
    client,sessions,_ = review_api
    with sessions() as db:
        before = [dict(x) for x in db.execute(select(Event.__table__)).mappings()]
    def fail_commit(self):
        raise OperationalError('synthetic secret SQL',{},Exception('synthetic credentials'))
    with monkeypatch.context() as patch:
        patch.setattr(Session,'commit',fail_commit)
        response = client.post(BASE+'/101/approve',json=APPROVE)
    assert response.status_code == 503
    assert 'secret' not in response.text and 'credentials' not in response.text
    with sessions() as db:
        c = db.get(EventCandidate,101)
        assert c.review_status == 'pending' and c.reviewed_at is None and c.reviewed_payload == {}
        assert [dict(x) for x in db.execute(select(Event.__table__)).mappings()] == before
