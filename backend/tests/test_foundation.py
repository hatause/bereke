import os
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import subprocess
import sys
from uuid import uuid4
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import event, func, inspect, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker
from app.db import get_session, make_engine
from app.main import app
from app.models import Customer, LearningProgress, VerifiedFact, Question
from app.seed import seed

@pytest.fixture
def database(tmp_path):
    url = 'sqlite:///' + (tmp_path/'test.sqlite3').as_posix()
    env = dict(os.environ, DATABASE_URL=url)
    subprocess.run([sys.executable,'-m','alembic','upgrade','head'],check=True,env=env,cwd=Path(__file__).parents[1],capture_output=True)
    engine=make_engine(url)
    factory=sessionmaker(engine,expire_on_commit=False)
    with factory.begin() as s:
        seed(s)
    yield engine,factory,url
    engine.dispose()

@pytest.fixture
def client(database):
    _,factory,_=database
    def session_override():
        with factory() as s:
            yield s
    app.dependency_overrides[get_session]=session_override
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()

def test_complete_lesson_persists_and_seed_is_idempotent(client,database):
    assert client.get('/api/health').status_code==200
    lessons=client.get('/api/lessons').json()
    assert len(lessons)==4
    lesson=client.get('/api/lessons/1').json()
    for section in lesson['sections']:
        assert section['fact']['source_page_or_slide']
        assert section['fact']['review_status']=='verified'
        for _ in range(2):
            assert client.put(f"/api/sections/{section['id']}/progress",json={'completed':True}).status_code==200
    assert client.get('/api/lessons/1').json()['progress_percent']==100
    assert client.get('/api/dashboard').json()['completed_lessons']==1
    engine,factory,url=database
    with factory.begin() as s:
        seed(s)
        assert s.scalar(select(func.count()).select_from(LearningProgress))==len(lesson['sections'])
    engine.dispose()
    reopened=make_engine(url)
    with sessionmaker(reopened)() as s:
        assert s.scalar(select(func.count()).select_from(LearningProgress).where(LearningProgress.completed.is_(True)))==len(lesson['sections'])
    reopened.dispose()
    first=lesson['sections'][0]['id']
    assert client.put(f'/api/sections/{first}/progress',json={'completed':False}).status_code==200
    assert client.get('/api/lessons/1').json()['completed_sections']==len(lesson['sections'])-1

def test_validation_and_missing_resources(client):
    assert client.get('/api/lessons/9999').status_code==404
    assert client.put('/api/sections/9999/progress',json={'completed':True}).status_code==404
    for payload in [{'completed':'true'},{'completed':True,'user_id':9},{}]:
        assert client.put('/api/sections/1/progress',json=payload).status_code==422
    assert client.put('/api/sections/1/progress',json={'completed':True},headers={'Origin':'https://untrusted.example'}).status_code==403


def test_out_of_range_ids_are_rejected(client):
    oversized = 2 ** 63
    assert client.get(f'/api/crm/customers/{oversized}').status_code == 422
    assert client.put(f'/api/sections/{oversized}/progress', json={'completed': True}).status_code == 422
    assert client.put(f'/api/crm/tickets/{oversized}/status', json={
        'status': 'in_progress', 'version': 0, 'request_id': str(uuid4()),
    }).status_code == 422

def test_sources_and_privacy(client,database):
    assert len(client.get('/api/terms').json())==64
    assert client.get('/api/terms?q=гэсв').json()[0]['term']=='ГЭСВ'
    conflicts=client.get('/api/conflicts').json()
    assert len(conflicts)==15
    assert all(f['needs_trainer_confirmation'] for c in conflicts for f in c['versions'])
    for path in ['/sources/private/test.pdf','/data/reviewed_content.json','/.env','/.local/academy.sqlite3']:
        assert client.get(path).status_code==404
    dash=client.get('/api/dashboard').json()
    assert dash['exam_attempts']==0
    assert dash['legacy_practice']['first_day_quiz']['answered']==9
    assert dash['weak_topics']==[]
    engine,factory,_=database
    required={'users','lessons','lesson_sections','learning_progress','banking_terms','questions','question_options','exam_attempts','exam_answers','customers','accounts','cards','transactions','deposits','loans','support_tickets','roleplay_scenarios','roleplay_sessions','source_documents','verified_facts','fact_conflicts'}
    assert required <= set(inspect(engine).get_table_names())
    with factory() as s:
        assert s.execute(text('PRAGMA foreign_key_check')).all()==[]
        assert s.scalar(select(func.count()).select_from(Customer))==6
        with pytest.raises(IntegrityError):
            s.add(Customer(demo_code='REAL-123',display_name='Not allowed'))
            s.flush()
        s.rollback()
        with pytest.raises(IntegrityError):
            s.add(LearningProgress(user_id=9999,section_id=1,completed=True))
            s.flush()

def test_migration_downgrade_upgrade(client, database):
    engine,factory,url=database
    engine.dispose()
    env=dict(os.environ,DATABASE_URL=url)
    for command,target in [('downgrade','base'),('upgrade','2e28b5ac0a11'),('upgrade','head')]:
        subprocess.run([sys.executable,'-m','alembic',command,target],env=env,check=True,cwd=Path(__file__).parents[1],capture_output=True)
        assert client.get('/api/health').status_code == 503
    with factory.begin() as session:
        seed(session)
    assert client.get('/api/health').status_code == 200
    with engine.connect() as c:
        assert c.execute(text('PRAGMA foreign_key_check')).all()==[]

def test_unverified_answer_keys_cannot_be_published(database):
    _,factory,_=database
    with factory() as s:
        disputed=s.scalar(select(VerifiedFact).where(VerifiedFact.status=='disputed'))
        q=Question(lesson_id=4,fact_id=disputed.id,prompt='Test fixture',kind='single',difficulty='easy',review_status='published',correct_answer={'key':'a'},explanation='Test fixture')
        s.add(q)
        with pytest.raises(IntegrityError):
            s.flush()
        s.rollback()
        verified=s.scalar(select(VerifiedFact).where(VerifiedFact.key=='d1-1'))
        q=Question(lesson_id=1,fact_id=verified.id,prompt='Test fixture',kind='single',difficulty='easy',review_status='published',correct_answer={'key':'a'},explanation='Test fixture')
        s.add(q)
        s.flush()
        verified.status='disputed'
        s.flush()
        s.expire(q)
        assert q.review_status=='retired'


def test_crm_search_and_products(client):
    assert len(client.get('/api/crm/customers').json()) == 6
    assert [row['id'] for row in client.get('/api/crm/customers?q=demo-customer-002').json()] == [2]
    assert len(client.get('/api/crm/customers', params={'q': 'ВЫМЫШЛЕННЫЙ'}).json()) == 6
    assert client.get('/api/crm/customers/999').status_code == 404
    customer = client.get('/api/crm/customers/2').json()
    account = customer['accounts'][0]
    assert customer['fictional'] is True
    assert account['cards'][0]['demo_code'] == 'DEMO-CARD-002'
    assert account['transactions'][0]['amount_minor'] == -2000
    assert account['deposit']['principal_minor'] == 200000
    assert account['loan'] is None
    assert client.get('/api/crm/customers/3').json()['accounts'][0]['loan']['outstanding_minor'] == 300000
    assert client.get('/api/crm/customers/5').json()['loyalty_points'] == 1250


def test_crm_card_reads_ticket_and_journal_from_same_snapshot(client, database):
    engine, _, _ = database
    concurrent_write = False

    def write_before_journal_read(conn, cursor, statement, parameters, context, executemany):
        nonlocal concurrent_write
        if concurrent_write or 'FROM ticket_events JOIN users' not in statement:
            return
        concurrent_write = True
        with engine.begin() as writer:
            writer.exec_driver_sql("UPDATE support_tickets SET status = 'in_progress', version = 1 WHERE id = 2")
            writer.exec_driver_sql("""
                INSERT INTO ticket_events (ticket_id, operator_id, kind, previous_status, status, ticket_version)
                VALUES (2, 1, 'status_changed', 'open', 'in_progress', 1)
            """)

    event.listen(engine, 'before_cursor_execute', write_before_journal_read)
    try:
        original = client.get('/api/crm/customers/2').json()['tickets'][0]
    finally:
        event.remove(engine, 'before_cursor_execute', write_before_journal_read)
    assert concurrent_write
    assert original['status'] == original['events'][-1]['status'] == 'open'
    updated = client.get('/api/crm/customers/2').json()['tickets'][0]
    assert updated['status'] == updated['events'][-1]['status'] == 'in_progress'


def test_crm_ticket_commands_are_atomic_and_idempotent(client, database):
    path = '/api/crm/customers/2/tickets'
    command = {'topic': 'deposit', 'request_id': str(uuid4())}
    assert client.post(path, json={**command, 'topic': 'произвольный ввод'}).status_code == 422
    assert client.post('/api/crm/customers/999/tickets', json=command).status_code == 404
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _: client.post(path, json=command), range(2)))
    assert [response.status_code for response in results] == [200, 200]
    created, replay = [response.json() for response in results]
    assert created == replay
    assert client.post(path, json={**command, 'topic': 'loan'}).status_code == 409
    assert client.post('/api/crm/customers/3/tickets', json=command).status_code == 409
    assert len(created['events']) == 1

    ticket_id = created['id']
    status_path = f'/api/crm/tickets/{ticket_id}/status'
    change = {'status': 'in_progress', 'version': 0, 'request_id': str(uuid4())}
    assert client.put(status_path, json={**change, 'status': 'resolved'}).status_code == 409
    updated = client.put(status_path, json=change).json()
    assert updated['status'] == 'in_progress'
    assert client.put(status_path, json=change).json() == updated
    assert client.put(status_path, json={**change, 'request_id': str(uuid4())}).status_code == 409
    assert client.put(status_path, json={**change, 'version': 1}).status_code == 409
    for version, state in [(1, 'resolved'), (2, 'open')]:
        response = client.put(status_path, json={'status': state, 'version': version, 'request_id': str(uuid4())})
        assert response.status_code == 200
        assert response.json()['status'] == state

    database[0].dispose()
    tickets = client.get('/api/crm/customers/2').json()['tickets']
    assert len(tickets) == 2
    saved = next(ticket for ticket in tickets if ticket['id'] == ticket_id)
    assert [event['status'] for event in saved['events']] == ['open', 'in_progress', 'resolved', 'open']
    assert saved['version'] == 3
    queue = client.get('/api/crm/tickets?status=open').json()
    assert sum(item['id'] == ticket_id for item in queue) == 1
