import type { ReactNode } from 'react'
import { Link } from 'react-router-dom'
import type { Fact, LessonSummary } from './api'

export function Panel({children}:{children:ReactNode}) { return <section className="panel">{children}</section> }
export function QueryState({pending,error,retry}:{pending:boolean;error:Error|null;retry:()=>void}) {
  if (pending) return <p role="status">Загрузка из локальной базы…</p>
  if (error) return <div role="alert" className="notice"><p>{error.message}</p><button onClick={retry}>Повторить загрузку</button></div>
  return null
}
const statuses:Record<string,string> = {verified:'Сверено с лекцией',disputed:'Есть противоречие',historical:'Исторические условия',unverified:'Нужно уточнение'}
export function SourceCitation({fact}:{fact:Fact}) {
  return <footer className="citation"><span className={fact.needs_trainer_confirmation?'warning':'status'}>{statuses[fact.review_status] ?? fact.review_status}</span><p>{fact.source_file} · {fact.source_page_or_slide}</p><p>Дата действия: {fact.effective_date ?? 'в источнике не указана'}</p></footer>
}
export function LessonCard({lesson}:{lesson:LessonSummary}) {
  return <Panel><p className="eyebrow">День {lesson.day.toString().padStart(2,'0')}</p><h2>{lesson.title}</h2><p>{lesson.completed_sections} из {lesson.total_sections} разделов прочитано</p><progress aria-label={`Прогресс дня ${lesson.day}`} value={lesson.progress_percent} max={100}/><Link className="action" to={`/lessons/${lesson.id}`}>{lesson.completed_sections?'Продолжить':'Открыть урок'}</Link></Panel>
}
