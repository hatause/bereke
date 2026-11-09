export type Fact = { id:number; topic:string; statement:string; source_file:string; source_page_or_slide:string; effective_date:string|null; review_status:string; needs_trainer_confirmation:boolean }
export type LessonSummary = { id:number; day:number; title:string; total_sections:number; completed_sections:number; progress_percent:number }
export type Section = { id:number; title:string; position:number; completed:boolean; fact:Fact }
export type Lesson = LessonSummary & { sections:Section[] }
export type Dashboard = { lessons:LessonSummary[]; completed_sections:number; total_sections:number; progress_percent:number; completed_lessons:number; open_conflicts:number; exam_attempts:number; weak_topics:string[]; legacy_practice:{first_day_quiz:{answered:number; score:number; weak_topics:string[]}}|null }
export type Term = {id:number; term:string; topic:string; fact:Fact}
export type Conflict = {id:number; title:string; question:string; status:string; versions:Fact[]}

export class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message)
  }
}

export async function api<T>(path:string, options?:RequestInit):Promise<T> {
  const response = await fetch(`/api${path}`, options)
  if (!response.ok) {
    const body = await response.json().catch(() => null)
    const message = typeof body?.detail === 'string'
      ? body.detail
      : `Не удалось выполнить запрос (${response.status}).`
    throw new ApiError(response.status, message)
  }
  return response.json() as Promise<T>
}

export function saveProgress(sectionId:number, completed:boolean) {
  return api<{section_id:number;completed:boolean;lesson_id:number}>(`/sections/${sectionId}/progress`, {
    method:'PUT', headers:{'Content-Type':'application/json'}, body:JSON.stringify({completed}),
  })
}
