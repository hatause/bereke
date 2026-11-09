from typing import Annotated
from fastapi import Path
from pydantic import BaseModel, ConfigDict

DatabaseId = Annotated[int, Path(ge=1, le=2**63 - 1)]

class ProgressUpdate(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)
    completed: bool

class FactOut(BaseModel):
    id: int
    topic: str
    statement: str
    source_file: str
    source_page_or_slide: str
    effective_date: str | None
    review_status: str
    needs_trainer_confirmation: bool

class SectionOut(BaseModel):
    id: int
    title: str
    position: int
    completed: bool
    fact: FactOut

class LessonSummary(BaseModel):
    id: int
    day: int
    title: str
    total_sections: int
    completed_sections: int
    progress_percent: int

class LessonOut(LessonSummary):
    sections: list[SectionOut]

class ProgressOut(BaseModel):
    section_id: int
    completed: bool
    lesson_id: int

class DashboardOut(BaseModel):
    lessons: list[LessonSummary]
    completed_sections: int
    total_sections: int
    progress_percent: int
    completed_lessons: int
    open_conflicts: int
    exam_attempts: int
    weak_topics: list[str]
    legacy_practice: dict | None

class TermOut(BaseModel):
    id: int
    term: str
    topic: str
    fact: FactOut

class ConflictOut(BaseModel):
    id: int
    title: str
    question: str
    status: str
    versions: list[FactOut]
