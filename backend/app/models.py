"""Stage 1 schema. Future modules have tables, but no pretend workflows."""
from datetime import datetime, timezone
from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, Integer, JSON, String, Text, UniqueConstraint, Index
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

def now():
    return datetime.now(timezone.utc)

class Base(DeclarativeBase):
    pass

class Identity:
    id: Mapped[int] = mapped_column(primary_key=True)

class User(Identity, Base):
    __tablename__ = 'users'
    display_name: Mapped[str] = mapped_column(String(100))
    demo_key: Mapped[str] = mapped_column(String(40), unique=True)

class SourceDocument(Identity, Base):
    __tablename__ = 'source_documents'
    filename: Mapped[str] = mapped_column(String(250), unique=True)
    sha256: Mapped[str] = mapped_column(String(64))
    kind: Mapped[str] = mapped_column(String(10))
    page_count: Mapped[int | None]
    reviewed_at: Mapped[str] = mapped_column(String(10))
    # No absolute paths, binary content, or screenshot data in this table.

class VerifiedFact(Identity, Base):
    __tablename__ = 'verified_facts'
    key: Mapped[str] = mapped_column(String(80), unique=True)
    topic: Mapped[str] = mapped_column(String(150))
    statement: Mapped[str] = mapped_column(Text)
    source_id: Mapped[int] = mapped_column(ForeignKey('source_documents.id'), index=True)
    locator: Mapped[str] = mapped_column(String(200))
    effective_date: Mapped[str | None] = mapped_column(String(150))
    status: Mapped[str] = mapped_column(String(30), index=True)
    needs_trainer_confirmation: Mapped[bool] = mapped_column(Boolean, default=False)
    source: Mapped[SourceDocument] = relationship()
    __table_args__ = (CheckConstraint("status IN ('verified','disputed','historical','unverified')", name='fact_status'),)

class FactConflict(Identity, Base):
    __tablename__ = 'fact_conflicts'
    title: Mapped[str] = mapped_column(String(200))
    fact_a_id: Mapped[int] = mapped_column(ForeignKey('verified_facts.id'), index=True)
    fact_b_id: Mapped[int | None] = mapped_column(ForeignKey('verified_facts.id'), index=True)
    question: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(20), default='open', index=True)
    resolution: Mapped[str | None] = mapped_column(Text)
    __table_args__ = (CheckConstraint("status IN ('open','resolved')", name='conflict_status'), CheckConstraint("status != 'resolved' OR resolution IS NOT NULL", name='resolution_required'))

class Lesson(Identity, Base):
    __tablename__ = 'lessons'
    day: Mapped[int] = mapped_column(unique=True)
    title: Mapped[str] = mapped_column(String(200))
    sections: Mapped[list['LessonSection']] = relationship(order_by='LessonSection.position')
    __table_args__ = (CheckConstraint('day BETWEEN 1 AND 4', name='lesson_day'),)

class LessonSection(Identity, Base):
    __tablename__ = 'lesson_sections'
    lesson_id: Mapped[int] = mapped_column(ForeignKey('lessons.id'), index=True)
    position: Mapped[int]
    title: Mapped[str] = mapped_column(String(200))
    # Each short section is a sourced fact; add a join table if multi-fact sections become necessary.
    fact_id: Mapped[int] = mapped_column(ForeignKey('verified_facts.id'), index=True)
    fact: Mapped[VerifiedFact] = relationship()
    __table_args__ = (UniqueConstraint('lesson_id', 'position'), CheckConstraint('position > 0', name='section_position'))

class LearningProgress(Identity, Base):
    __tablename__ = 'learning_progress'
    user_id: Mapped[int] = mapped_column(ForeignKey('users.id'), index=True)
    section_id: Mapped[int] = mapped_column(ForeignKey('lesson_sections.id'), index=True)
    completed: Mapped[bool] = mapped_column(Boolean, default=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    __table_args__ = (UniqueConstraint('user_id', 'section_id'),)

class BankingTerm(Identity, Base):
    __tablename__ = 'banking_terms'
    term: Mapped[str] = mapped_column(String(150), unique=True)
    fact_id: Mapped[int] = mapped_column(ForeignKey('verified_facts.id'), unique=True)
    topic: Mapped[str] = mapped_column(String(100), index=True)
    fact: Mapped[VerifiedFact] = relationship()

class TermProgress(Identity, Base):
    __tablename__ = 'term_progress'
    user_id: Mapped[int] = mapped_column(ForeignKey('users.id'), index=True)
    term_id: Mapped[int] = mapped_column(ForeignKey('banking_terms.id'), index=True)
    mastery: Mapped[int] = mapped_column(default=0)
    next_review: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    __table_args__ = (UniqueConstraint('user_id', 'term_id'), CheckConstraint('mastery BETWEEN 0 AND 3', name='mastery_range'))

class Question(Identity, Base):
    __tablename__ = 'questions'
    lesson_id: Mapped[int] = mapped_column(ForeignKey('lessons.id'), index=True)
    fact_id: Mapped[int] = mapped_column(ForeignKey('verified_facts.id'), index=True)
    prompt: Mapped[str] = mapped_column(Text)
    kind: Mapped[str] = mapped_column(String(20))
    difficulty: Mapped[str] = mapped_column(String(10))
    review_status: Mapped[str] = mapped_column(String(20), default='draft', index=True)
    correct_answer: Mapped[dict] = mapped_column(JSON)
    explanation: Mapped[str] = mapped_column(Text)
    rubric: Mapped[dict | None] = mapped_column(JSON)
    version: Mapped[int] = mapped_column(default=1)
    __table_args__ = (CheckConstraint("kind IN ('single','multiple','boolean','open','case')", name='question_kind'), CheckConstraint("review_status IN ('draft','published','retired')", name='question_status'), CheckConstraint("kind NOT IN ('open','case') OR rubric IS NOT NULL", name='rubric_required'))

class QuestionOption(Identity, Base):
    __tablename__ = 'question_options'
    question_id: Mapped[int] = mapped_column(ForeignKey('questions.id'), index=True)
    key: Mapped[str] = mapped_column(String(10))
    text: Mapped[str] = mapped_column(Text)
    __table_args__ = (UniqueConstraint('question_id', 'key'),)

class ExamAttempt(Identity, Base):
    __tablename__ = 'exam_attempts'
    user_id: Mapped[int] = mapped_column(ForeignKey('users.id'), index=True)
    lesson_id: Mapped[int | None] = mapped_column(ForeignKey('lessons.id'))
    status: Mapped[str] = mapped_column(String(20), default='in_progress', index=True)
    current_position: Mapped[int] = mapped_column(default=0)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    __table_args__ = (CheckConstraint("status IN ('in_progress','submitted','reviewed','abandoned')", name='attempt_status'), CheckConstraint('current_position >= 0', name='attempt_position'))

class AttemptQuestion(Identity, Base):
    __tablename__ = 'attempt_questions'
    attempt_id: Mapped[int] = mapped_column(ForeignKey('exam_attempts.id'), index=True)
    question_id: Mapped[int] = mapped_column(ForeignKey('questions.id'), index=True)
    position: Mapped[int]
    snapshot: Mapped[dict] = mapped_column(JSON)
    __table_args__ = (UniqueConstraint('attempt_id','position'), UniqueConstraint('attempt_id','question_id'))

class ExamAnswer(Identity, Base):
    __tablename__ = 'exam_answers'
    attempt_question_id: Mapped[int] = mapped_column(ForeignKey('attempt_questions.id'), unique=True)
    answer: Mapped[dict] = mapped_column(JSON)
    score_basis_points: Mapped[int | None]
    grading_status: Mapped[str] = mapped_column(String(20), default='pending')
    rubric_result: Mapped[dict | None] = mapped_column(JSON)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    __table_args__ = (CheckConstraint('score_basis_points BETWEEN 0 AND 10000', name='answer_score'),)

class Customer(Identity, Base):
    __tablename__ = 'customers'
    demo_code: Mapped[str] = mapped_column(String(50), unique=True)
    display_name: Mapped[str] = mapped_column(String(100))
    fictional: Mapped[bool] = mapped_column(Boolean, default=True)
    loyalty_points: Mapped[int | None]
    __table_args__ = (CheckConstraint("demo_code LIKE 'DEMO-%'", name='synthetic_customer'), CheckConstraint('fictional = 1', name='fictional_only'))

class Account(Identity, Base):
    __tablename__ = 'accounts'
    customer_id: Mapped[int] = mapped_column(ForeignKey('customers.id'), index=True)
    demo_code: Mapped[str] = mapped_column(String(50), unique=True)
    currency: Mapped[str] = mapped_column(String(3))
    balance_minor: Mapped[int] = mapped_column(Integer, default=0)
    __table_args__ = (CheckConstraint("demo_code LIKE 'DEMO-%'", name='synthetic_account'), CheckConstraint("currency IN ('KZT','USD','EUR')", name='account_currency'))

class Card(Identity, Base):
    __tablename__ = 'cards'
    account_id: Mapped[int] = mapped_column(ForeignKey('accounts.id'), index=True)
    demo_code: Mapped[str] = mapped_column(String(50), unique=True)
    status: Mapped[str] = mapped_column(String(30))
    __table_args__ = (CheckConstraint("demo_code LIKE 'DEMO-%'", name='synthetic_card'),)

class Transaction(Identity, Base):
    __tablename__ = 'transactions'
    account_id: Mapped[int] = mapped_column(ForeignKey('accounts.id'), index=True)
    amount_minor: Mapped[int]
    status: Mapped[str] = mapped_column(String(30))
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, index=True)

class Deposit(Identity, Base):
    __tablename__ = 'deposits'
    account_id: Mapped[int] = mapped_column(ForeignKey('accounts.id'), unique=True)
    demo_product: Mapped[str] = mapped_column(String(100))
    principal_minor: Mapped[int]
    __table_args__ = (CheckConstraint('principal_minor >= 0', name='deposit_principal'),)

class Loan(Identity, Base):
    __tablename__ = 'loans'
    account_id: Mapped[int] = mapped_column(ForeignKey('accounts.id'), unique=True)
    demo_product: Mapped[str] = mapped_column(String(100))
    outstanding_minor: Mapped[int]
    __table_args__ = (CheckConstraint('outstanding_minor >= 0', name='loan_outstanding'),)

class SupportTicket(Identity, Base):
    __tablename__ = 'support_tickets'
    customer_id: Mapped[int] = mapped_column(ForeignKey('customers.id'), index=True)
    operator_id: Mapped[int] = mapped_column(ForeignKey('users.id'), index=True)
    subject: Mapped[str] = mapped_column(String(200))
    status: Mapped[str] = mapped_column(String(20), default='open', index=True)
    version: Mapped[int] = mapped_column(default=0, server_default='0')

class TicketEvent(Identity, Base):
    __tablename__ = 'ticket_events'
    ticket_id: Mapped[int] = mapped_column(ForeignKey('support_tickets.id'))
    operator_id: Mapped[int] = mapped_column(ForeignKey('users.id'))
    kind: Mapped[str] = mapped_column(String(20))
    previous_status: Mapped[str | None] = mapped_column(String(20))
    status: Mapped[str] = mapped_column(String(20))
    ticket_version: Mapped[int]
    request_id: Mapped[str | None] = mapped_column(String(36))
    occurred_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    __table_args__ = (
        UniqueConstraint('operator_id', 'request_id', name='ticket_event_request'),
        UniqueConstraint('ticket_id', 'ticket_version', name='ticket_event_version'),
    )

class RoleplayScenario(Identity, Base):
    __tablename__ = 'roleplay_scenarios'
    title: Mapped[str] = mapped_column(String(200))
    customer_id: Mapped[int] = mapped_column(ForeignKey('customers.id'))
    fact_id: Mapped[int | None] = mapped_column(ForeignKey('verified_facts.id'))
    mood: Mapped[str] = mapped_column(String(20))
    rubric: Mapped[dict] = mapped_column(JSON)
    review_status: Mapped[str] = mapped_column(String(20), default='draft')

class RoleplaySession(Identity, Base):
    __tablename__ = 'roleplay_sessions'
    user_id: Mapped[int] = mapped_column(ForeignKey('users.id'), index=True)
    scenario_id: Mapped[int] = mapped_column(ForeignKey('roleplay_scenarios.id'), index=True)
    transcript: Mapped[list] = mapped_column(JSON, default=list)
    rubric_result: Mapped[dict | None] = mapped_column(JSON)
    status: Mapped[str] = mapped_column(String(20), default='in_progress')

class ImportRecord(Identity, Base):
    __tablename__ = 'import_records'
    key: Mapped[str] = mapped_column(String(100), unique=True)
    payload: Mapped[dict] = mapped_column(JSON)
    imported_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
