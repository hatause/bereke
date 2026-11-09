from alembic.migration import MigrationContext
from alembic.script import ScriptDirectory
from fastapi import Depends, FastAPI, HTTPException, Query, Request
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from sqlalchemy import func, select
from sqlalchemy.dialects.sqlite import insert
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, selectinload
from .config import ROOT
from .db import get_session
from .crm import router as crm_router
from .models import BankingTerm, ExamAttempt, FactConflict, ImportRecord, LearningProgress, LessonSection, User, VerifiedFact, now
from .schemas import ConflictOut, DashboardOut, DatabaseId, FactOut, LessonOut, LessonSummary, ProgressOut, ProgressUpdate, TermOut
from .services import DEMO_USER_ID, fact_out, list_lessons

app = FastAPI(title='Bereke Operator Academy — local learning', version='0.1.0')
app.include_router(crm_router)
app.add_middleware(TrustedHostMiddleware, allowed_hosts=['127.0.0.1', 'localhost', 'testserver'])
EXPECTED_REVISION = ScriptDirectory(str(ROOT / 'migrations')).get_current_head()

@app.middleware('http')
async def local_origin(request: Request, call_next):
    origin = request.headers.get('origin')
    if request.method not in ('GET', 'HEAD', 'OPTIONS') and origin and origin not in {
        'http://127.0.0.1:5173', 'http://localhost:5173', 'http://127.0.0.1:8000', 'http://localhost:8000',
        'http://127.0.0.1:4173', 'http://localhost:4173',
    }:
        from fastapi.responses import JSONResponse
        return JSONResponse({'detail': 'Only local application origins are allowed'}, status_code=403)
    response = await call_next(request)
    response.headers['Cache-Control'] = 'no-store'
    response.headers['X-Content-Type-Options'] = 'nosniff'
    return response

@app.get('/api/health')
def health(db: Session = Depends(get_session)):
    try:
        revisions = MigrationContext.configure(db.connection()).get_current_heads()
        if revisions != (EXPECTED_REVISION,) or db.get(User, DEMO_USER_ID) is None:
            raise HTTPException(503, 'База не готова. Выполните setup перед запуском приложения')
    except SQLAlchemyError as error:
        raise HTTPException(503, 'Локальная база недоступна') from error
    return {'status': 'ok', 'migration': EXPECTED_REVISION}

@app.get('/api/lessons', response_model=list[LessonSummary])
def lessons(db: Session = Depends(get_session)):
    return list_lessons(db)

@app.get('/api/lessons/{lesson_id}', response_model=LessonOut)
def lesson(lesson_id: DatabaseId, db: Session = Depends(get_session)):
    for item in list_lessons(db, detail=True):
        if item['id'] == lesson_id:
            return item
    raise HTTPException(404, 'Урок не найден')

@app.put('/api/sections/{section_id}/progress', response_model=ProgressOut)
def progress(section_id: DatabaseId, update: ProgressUpdate, db: Session = Depends(get_session)):
    section = db.get(LessonSection, section_id)
    if not section:
        raise HTTPException(404, 'Раздел не найден')
    statement = insert(LearningProgress).values(user_id=DEMO_USER_ID, section_id=section_id, completed=update.completed, updated_at=now())
    db.execute(statement.on_conflict_do_update(index_elements=['user_id', 'section_id'], set_={'completed': update.completed, 'updated_at': now()}))
    db.commit()
    return dict(section_id=section_id, completed=update.completed, lesson_id=section.lesson_id)

@app.get('/api/dashboard', response_model=DashboardOut)
def dashboard(db: Session = Depends(get_session)):
    items = list_lessons(db)
    total = sum(x['total_sections'] for x in items)
    done = sum(x['completed_sections'] for x in items)
    legacy = db.scalar(select(ImportRecord).where(ImportRecord.key == 'legacy_chat_practice'))
    return dict(lessons=items, total_sections=total, completed_sections=done,
                progress_percent=round(100*done/total) if total else 0,
                completed_lessons=sum(x['total_sections'] > 0 and x['completed_sections'] == x['total_sections'] for x in items),
                open_conflicts=db.scalar(select(func.count()).select_from(FactConflict).where(FactConflict.status == 'open')),
                exam_attempts=db.scalar(select(func.count()).select_from(ExamAttempt).where(ExamAttempt.user_id == DEMO_USER_ID)),
                weak_topics=[], legacy_practice=legacy.payload if legacy else None)

@app.get('/api/terms', response_model=list[TermOut])
def terms(q: str = Query('', max_length=100), db: Session = Depends(get_session)):
    rows = db.scalars(select(BankingTerm).options(selectinload(BankingTerm.fact).selectinload(VerifiedFact.source)).order_by(BankingTerm.id)).all()
    # casefold handles Cyrillic; SQLite's built-in LOWER does not.
    return [dict(id=t.id, term=t.term, topic=t.topic, fact=fact_out(t.fact)) for t in rows if q.casefold() in (t.term+' '+t.fact.statement).casefold()]

@app.get('/api/facts', response_model=list[FactOut])
def facts(db: Session = Depends(get_session)):
    return [fact_out(f) for f in db.scalars(select(VerifiedFact).options(selectinload(VerifiedFact.source)).order_by(VerifiedFact.id))]

@app.get('/api/conflicts', response_model=list[ConflictOut])
def conflicts(db: Session = Depends(get_session)):
    return [dict(id=c.id, title=c.title, question=c.question, status=c.status,
                 versions=[fact_out(db.get(VerifiedFact, i)) for i in [c.fact_a_id, c.fact_b_id] if i])
            for c in db.scalars(select(FactConflict).order_by(FactConflict.id))]
