"""Read-only demo products and a local support ticket workflow."""
from datetime import datetime, timezone
from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import AfterValidator, BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from .db import get_session
from .models import Account, Card, Customer, Deposit, Loan, SupportTicket, TicketEvent, Transaction, User, now
from .schemas import DatabaseId
from .services import DEMO_USER_ID

router = APIRouter(prefix='/api/crm', tags=['CRM'])
Database = Annotated[Session, Depends(get_session)]
TicketStatus = Literal['open', 'in_progress', 'resolved']
NEXT_STATUS = {'open': 'in_progress', 'in_progress': 'resolved', 'resolved': 'open'}
TOPICS = {
    'card': 'Карта',
    'deposit': 'Депозит',
    'loan': 'Кредит',
    'transfer': 'Перевод',
    'loyalty': 'Лояльность',
    'app': 'Вход в приложение',
}


def as_utc(value: datetime) -> datetime:
    # The SQLite driver returns stored UTC timestamps without a timezone.
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value


UtcTimestamp = Annotated[datetime, AfterValidator(as_utc)]


class Record(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class CustomerSummary(Record):
    id: int
    demo_code: str
    display_name: str
    fictional: Literal[True]


class CardOut(Record):
    id: int
    demo_code: str
    status: str


class TransactionOut(Record):
    id: int
    amount_minor: int
    status: str
    occurred_at: UtcTimestamp


class DepositOut(Record):
    demo_product: str
    principal_minor: int


class LoanOut(Record):
    demo_product: str
    outstanding_minor: int


class AccountOut(Record):
    id: int
    demo_code: str
    currency: str
    balance_minor: int
    cards: list[CardOut]
    transactions: list[TransactionOut]
    deposit: DepositOut | None
    loan: LoanOut | None


class TicketSummary(Record):
    id: int
    customer_id: int
    subject: str
    status: TicketStatus


class TicketQueueItem(TicketSummary):
    customer: CustomerSummary


class EventOut(Record):
    id: int
    kind: Literal['fixture', 'created', 'status_changed']
    previous_status: TicketStatus | None
    status: TicketStatus
    operator_name: str
    occurred_at: UtcTimestamp | None


class TicketOut(TicketSummary):
    version: int
    next_status: TicketStatus
    events: list[EventOut]


class TicketTopic(BaseModel):
    code: str
    label: str


class CustomerDetail(CustomerSummary):
    loyalty_points: int | None
    accounts: list[AccountOut]
    tickets: list[TicketOut]
    ticket_topics: list[TicketTopic]


class TicketCommand(BaseModel):
    model_config = ConfigDict(extra='forbid')
    request_id: UUID


class CreateTicket(TicketCommand):
    topic: Literal['card', 'deposit', 'loan', 'transfer', 'loyalty', 'app']


class ChangeStatus(TicketCommand):
    status: TicketStatus
    version: int = Field(ge=0, strict=True)


def demo_customer(db: Session, customer_id: int) -> Customer:
    customer = db.get(Customer, customer_id)
    if customer is None or not customer.fictional:
        raise HTTPException(404, 'Учебный клиент не найден')
    return customer


def demo_ticket(db: Session, ticket_id: int) -> SupportTicket:
    ticket = db.get(SupportTicket, ticket_id)
    if ticket is None or ticket.operator_id != DEMO_USER_ID:
        raise HTTPException(404, 'Учебный тикет не найден')
    demo_customer(db, ticket.customer_id)
    return ticket


def ticket_detail(db: Session, ticket: SupportTicket) -> TicketOut:
    events = db.execute(
        select(TicketEvent, User.display_name)
        .join(User, User.id == TicketEvent.operator_id)
        .where(TicketEvent.ticket_id == ticket.id)
        .order_by(TicketEvent.ticket_version)
    )
    return TicketOut(
        **TicketSummary.model_validate(ticket).model_dump(),
        version=ticket.version,
        next_status=NEXT_STATUS[ticket.status],
        events=[
            EventOut(id=event.id, kind=event.kind, previous_status=event.previous_status,
                     status=event.status, operator_name=name, occurred_at=event.occurred_at)
            for event, name in events
        ],
    )


@router.get('/customers', response_model=list[CustomerSummary])
def customers(db: Database, q: str = Query('', max_length=100)):
    term = q.strip().casefold()
    records = db.scalars(select(Customer).where(Customer.fictional.is_(True)).order_by(Customer.demo_code))
    return [record for record in records if term in f'{record.demo_code} {record.display_name}'.casefold()]


@router.get('/customers/{customer_id}', response_model=CustomerDetail)
def customer_detail(customer_id: DatabaseId, db: Database):
    # Pin a read snapshot before loading tickets and their event streams.
    db.connection().exec_driver_sql('BEGIN')
    customer = demo_customer(db, customer_id)
    accounts = db.scalars(select(Account).where(Account.customer_id == customer_id).order_by(Account.id)).all()
    tickets = db.scalars(select(SupportTicket).where(
        SupportTicket.customer_id == customer_id, SupportTicket.operator_id == DEMO_USER_ID,
    ).order_by(SupportTicket.id.desc())).all()

    return CustomerDetail(
        **CustomerSummary.model_validate(customer).model_dump(),
        loyalty_points=customer.loyalty_points,
        accounts=[
            AccountOut(
                id=account.id, demo_code=account.demo_code, currency=account.currency, balance_minor=account.balance_minor,
                cards=list(db.scalars(select(Card).where(Card.account_id == account.id).order_by(Card.id))),
                transactions=list(db.scalars(select(Transaction).where(Transaction.account_id == account.id)
                                             .order_by(Transaction.occurred_at.desc(), Transaction.id.desc()))),
                deposit=db.scalar(select(Deposit).where(Deposit.account_id == account.id)),
                loan=db.scalar(select(Loan).where(Loan.account_id == account.id)),
            )
            for account in accounts
        ],
        tickets=[ticket_detail(db, ticket) for ticket in tickets],
        ticket_topics=[TicketTopic(code=code, label=label) for code, label in TOPICS.items()],
    )


@router.get('/tickets', response_model=list[TicketQueueItem])
def ticket_queue(db: Database, status: TicketStatus | None = None):
    statement = (
        select(SupportTicket, Customer)
        .join(Customer, Customer.id == SupportTicket.customer_id)
        .where(Customer.fictional.is_(True), SupportTicket.operator_id == DEMO_USER_ID)
        .order_by(SupportTicket.id.desc())
    )
    if status is not None:
        statement = statement.where(SupportTicket.status == status)
    return [
        TicketQueueItem(**TicketSummary.model_validate(ticket).model_dump(),
                        customer=CustomerSummary.model_validate(customer))
        for ticket, customer in db.execute(statement)
    ]


def start_ticket_write(db: Session, request_id: UUID) -> TicketEvent | None:
    # Serialize the retry check and the write across concurrent SQLite connections.
    db.connection().exec_driver_sql('BEGIN IMMEDIATE')
    return db.scalar(select(TicketEvent).where(
        TicketEvent.operator_id == DEMO_USER_ID, TicketEvent.request_id == str(request_id),
    ))


@router.post('/customers/{customer_id}/tickets', response_model=TicketOut)
def create_ticket(customer_id: DatabaseId, command: CreateTicket, db: Database):
    previous = start_ticket_write(db, command.request_id)
    demo_customer(db, customer_id)
    subject = TOPICS[command.topic]
    if previous is not None:
        ticket = demo_ticket(db, previous.ticket_id)
        if previous.kind != 'created' or ticket.customer_id != customer_id or ticket.subject != subject:
            raise HTTPException(409, 'Этот ключ запроса уже использован для другого действия')
    else:
        ticket = SupportTicket(customer_id=customer_id, operator_id=DEMO_USER_ID, subject=subject)
        db.add(ticket)
        db.flush()
        db.add(TicketEvent(ticket_id=ticket.id, operator_id=DEMO_USER_ID, kind='created',
                           status=ticket.status, ticket_version=ticket.version,
                           request_id=str(command.request_id), occurred_at=now()))
    result = ticket_detail(db, ticket)
    db.commit()
    return result


@router.put('/tickets/{ticket_id}/status', response_model=TicketOut)
def change_status(ticket_id: DatabaseId, command: ChangeStatus, db: Database):
    previous = start_ticket_write(db, command.request_id)
    ticket = demo_ticket(db, ticket_id)
    if previous is not None:
        if (previous.kind != 'status_changed' or previous.ticket_id != ticket_id
                or previous.status != command.status or previous.ticket_version != command.version + 1):
            raise HTTPException(409, 'Этот ключ запроса уже использован для другого действия')
    else:
        if ticket.version != command.version:
            raise HTTPException(409, 'Тикет уже изменился. Обновите карточку и повторите действие')
        if NEXT_STATUS[ticket.status] != command.status:
            raise HTTPException(409, 'Этот переход статуса недоступен')
        db.add(TicketEvent(ticket_id=ticket.id, operator_id=DEMO_USER_ID, kind='status_changed',
                           previous_status=ticket.status, status=command.status,
                           ticket_version=ticket.version + 1, request_id=str(command.request_id),
                           occurred_at=now()))
        ticket.status = command.status
        ticket.version += 1
    result = ticket_detail(db, ticket)
    db.commit()
    return result
