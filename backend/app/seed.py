"""Explicit, transactional, repeatable local seed. Never reads source document bodies."""
import hashlib
import json
from sqlalchemy import select
from .config import PROJECT
from .db import SessionLocal
from .models import Account, BankingTerm, Card, Customer, Deposit, FactConflict, ImportRecord, Lesson, LessonSection, Loan, SourceDocument, SupportTicket, TicketEvent, Transaction, User, VerifiedFact

def seed(session):
    path = PROJECT / 'data/reviewed_content.json'
    if not path.exists():
        raise RuntimeError('Нет data/reviewed_content.json. Восстановите приватный локальный пакет данных; импорт непроверенных лекций запрещён.')
    content = json.loads(path.read_text(encoding='utf-8'))
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    previous = session.scalar(select(ImportRecord).where(ImportRecord.key == 'stage1_seed'))
    if previous:
        if previous.payload['sha256'] != digest:
            raise RuntimeError('Seed изменён. Нужна отдельная миграция контента; прогресс не перезаписан.')
        return
    session.add(User(id=1, demo_key='local-student', display_name='Учебный оператор'))
    session.flush()
    sources = {}
    for row in content['sources']:
        obj = SourceDocument(**row)
        session.add(obj)
        session.flush()
        sources[obj.filename] = obj.id
    facts = {}
    for row in content['facts']:
        row = dict(row)
        filename = row.pop('source_file')
        obj = VerifiedFact(**row, source_id=sources[filename])
        session.add(obj)
        session.flush()
        facts[obj.key] = obj.id
    for row in content['lessons']:
        lesson = Lesson(id=row['day'], day=row['day'], title=row['title'])
        session.add(lesson)
        session.flush()
        for position, section in enumerate(row['sections'], 1):
            session.add(LessonSection(lesson_id=lesson.id, position=position, title=section['title'], fact_id=facts[section['fact_key']]))
    for row in content['terms']:
        session.add(BankingTerm(term=row['term'], topic=row['topic'], fact_id=facts[row['fact_key']]))
    for row in content['conflicts']:
        session.add(FactConflict(title=row['title'], question=row['question'], fact_a_id=facts[row['a']], fact_b_id=facts[row['b']] if row.get('b') else None))
    # Synthetic identifiers intentionally cannot be used as IIN, IBAN, PAN, or credentials.
    for i, topic in enumerate(['карта','депозит','кредит','перевод','лояльность','вход в приложение'], 1):
        session.add(Customer(id=i, demo_code=f'DEMO-CUSTOMER-{i:03}', display_name=f'Вымышленный клиент {i:03}',
                             loyalty_points=1250 if i == 5 else None))
        session.flush()
        session.add(Account(id=i, customer_id=i, demo_code=f'DEMO-ACCOUNT-{i:03}', currency='KZT', balance_minor=100000*i))
        session.flush()
        session.add(Card(account_id=i, demo_code=f'DEMO-CARD-{i:03}', status='demo_active'))
        session.add(Transaction(account_id=i, amount_minor=-1000*i, status='demo_completed'))
        ticket = SupportTicket(customer_id=i, operator_id=1, subject=f'Вымышленный сценарий: {topic}')
        session.add(ticket)
        session.flush()
        session.add(TicketEvent(ticket_id=ticket.id, operator_id=1, kind='fixture', status=ticket.status,
                                ticket_version=ticket.version))
    session.add(Deposit(account_id=2, demo_product='Учебный депозит, условия вымышлены', principal_minor=200000))
    session.add(Loan(account_id=3, demo_product='Учебный заём, условия вымышлены', outstanding_minor=300000))
    session.add(ImportRecord(key='legacy_chat_practice', payload=content['legacy_practice']))
    session.add(ImportRecord(key='stage1_seed', payload={'sha256': digest, 'version': 1}))
    session.flush()

if __name__ == '__main__':
    with SessionLocal.begin() as session:
        seed(session)
    print('Seed готов; существующий прогресс сохранён.')
