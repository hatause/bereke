from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload
from .models import Lesson, LessonSection, LearningProgress, VerifiedFact

DEMO_USER_ID = 1

def fact_out(fact):
    return dict(id=fact.id, topic=fact.topic, statement=fact.statement,
                source_file=fact.source.filename, source_page_or_slide=fact.locator,
                effective_date=fact.effective_date, review_status=fact.status,
                needs_trainer_confirmation=fact.needs_trainer_confirmation)

def list_lessons(session: Session, detail=False):
    lessons = session.scalars(select(Lesson).options(selectinload(Lesson.sections).selectinload(LessonSection.fact).selectinload(VerifiedFact.source)).order_by(Lesson.day)).all()
    done = set(session.scalars(select(LearningProgress.section_id).where(LearningProgress.user_id == DEMO_USER_ID, LearningProgress.completed.is_(True))))
    result = []
    for lesson in lessons:
        total = len(lesson.sections)
        completed = sum(s.id in done for s in lesson.sections)
        item = dict(id=lesson.id, day=lesson.day, title=lesson.title, total_sections=total,
                    completed_sections=completed, progress_percent=round(100*completed/total) if total else 0)
        if detail:
            item['sections'] = [dict(id=s.id, title=s.title, position=s.position, completed=s.id in done, fact=fact_out(s.fact)) for s in lesson.sections]
        result.append(item)
    return result
