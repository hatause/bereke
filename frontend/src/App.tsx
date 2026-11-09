import { useEffect, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Link, NavLink, Route, Routes, useParams } from 'react-router-dom'
import { api, saveProgress, type Dashboard, type Lesson, type LessonSummary, type Term, type Conflict } from './api'
import { Panel, QueryState, SourceCitation, LessonCard } from './components'
import { initialTheme, type Theme } from './theme'
import { CrmCustomerPage, CrmCustomersPage, CrmQueuePage } from './crm'

function DashboardPage() {
  const q=useQuery({queryKey:['dashboard'],queryFn:()=>api<Dashboard>('/dashboard')})
  return <><p className="eyebrow">Ваше обучение</p><h1>Обзор подготовки</h1><p className="lede">Четыре дня обучения. Один последовательный маршрут.</p><QueryState pending={q.isPending} error={q.error} retry={()=>void q.refetch()}/>{q.data && <>
    <div className="stats"><Panel><p>Общий прогресс</p><strong>{q.data.progress_percent}%</strong><p>{q.data.completed_sections} из {q.data.total_sections} разделов</p></Panel><Panel><p>Завершено дней</p><strong>{q.data.completed_lessons} / 4</strong><p>Прогресс хранится на этом компьютере</p></Panel><Panel><p>На проверке</p><strong>{q.data.open_conflicts}</strong><p><Link to="/facts">Открыть вопросы к тренеру</Link></p></Panel></div>
    <h2 className="section-title">Продолжить обучение</h2><div className="lesson-grid">{q.data.lessons.map(l=><LessonCard key={l.id} lesson={l}/>)}</div>
    <Panel><h2>Тесты и слабые темы</h2><p>Локальных попыток: {q.data.exam_attempts}. Оценки появятся после подключения проверенного банка вопросов.</p>{q.data.legacy_practice && <details><summary>История подготовки из чата — отдельно от локальных попыток</summary><p>Отвечено: {q.data.legacy_practice.first_day_quiz.answered}; баллы: {q.data.legacy_practice.first_day_quiz.score}. Слабые темы: {q.data.legacy_practice.first_day_quiz.weak_topics.join(', ')}.</p><p>Исходные вопросы и ответы не переданы. Восстановить эту попытку как тест нельзя.</p></details>}</Panel>
  </>}</>
}
function LessonsPage() {
  const q=useQuery({queryKey:['lessons'],queryFn:()=>api<LessonSummary[]>('/lessons')})
  return <><h1>Обучение</h1><p className="lede">Краткие лекции со ссылками на исходный материал.</p><QueryState pending={q.isPending} error={q.error} retry={()=>void q.refetch()}/><div className="lesson-grid">{q.data?.map(l=><LessonCard key={l.id} lesson={l}/>)}</div></>
}
function LessonPage() {
  const {id}=useParams(); const client=useQueryClient()
  const [message,setMessage]=useState('')
  const q=useQuery({queryKey:['lesson',id],queryFn:()=>api<Lesson>(`/lessons/${id}`)})
  const mutation=useMutation({mutationFn:({sectionId,completed}:{sectionId:number;completed:boolean})=>saveProgress(sectionId,completed),onSuccess:async()=>{
    await Promise.all([client.invalidateQueries({queryKey:['lesson',id]}),client.invalidateQueries({queryKey:['lessons']}),client.invalidateQueries({queryKey:['dashboard']})]);setMessage('Прогресс сохранён в SQLite.')
  }})
  return <><Link to="/lessons">← Все дни</Link><QueryState pending={q.isPending} error={q.error} retry={()=>void q.refetch()}/>{q.data&&<><p className="eyebrow">День {q.data.day}</p><h1>{q.data.title}</h1><p className="lede" data-testid="lesson-progress">Прочитано {q.data.completed_sections} из {q.data.total_sections} разделов</p><p className="notice">Материалы учебные. «Сверено с лекцией» подтверждает содержание источника, а не актуальность банковских условий сегодня.</p><p role="status">{message}</p>{mutation.error&&<p role="alert">{mutation.error.message} Изменение не сохранено.</p>}<div className="reading">{q.data.sections.map(s=><Panel key={s.id}><p className="eyebrow">Раздел {s.position}</p><h2>{s.title}</h2><p className="body-copy">{s.fact.statement}</p><SourceCitation fact={s.fact}/><button disabled={mutation.isPending} aria-pressed={s.completed} onClick={()=>{setMessage('');mutation.mutate({sectionId:s.id,completed:!s.completed})}}>{s.completed?'Снять отметку о прочтении':'Отметить прочитанным'}</button></Panel>)}</div></>}</>
}
function TermsPage() {
  const [search,setSearch]=useState('')
  const q=useQuery({queryKey:['terms',search],queryFn:({signal})=>api<Term[]>(`/terms?${new URLSearchParams({q:search})}`,{signal})})
  return <><h1>Банковский словарь</h1><label className="search">Поиск термина<input value={search} maxLength={100} onChange={e=>setSearch(e.target.value)} placeholder="Например, ГЭСВ"/></label><QueryState pending={q.isPending} error={q.error} retry={()=>void q.refetch()}/>{q.data?.length===0&&<p>Ничего не найдено.</p>}<div className="reading">{q.data?.map(t=><Panel key={t.id}><h2>{t.term}</h2><p className="body-copy">{t.fact.statement}</p><SourceCitation fact={t.fact}/></Panel>)}</div></>
}
function FactsPage() {
  const q=useQuery({queryKey:['conflicts'],queryFn:()=>api<Conflict[]>('/conflicts')})
  return <><h1>Проверка фактов</h1><p className="lede">Обе версии сохранены. До уточнения эти сведения не используются в оцениваемых вопросах.</p><QueryState pending={q.isPending} error={q.error} retry={()=>void q.refetch()}/><div className="reading">{q.data?.map(c=><Panel key={c.id}><p className="warning">Требует ответа тренера</p><h2>{c.title}</h2><p>{c.question}</p>{c.versions.map(f=><blockquote key={f.id}><p>{f.statement}</p><SourceCitation fact={f}/></blockquote>)}</Panel>)}</div></>
}
function SettingsPage({theme,setTheme}:{theme:Theme;setTheme:(t:Theme)=>void}) {
  return <><h1>Настройки</h1><Panel><h2>Оформление</h2><label>Тема<select value={theme} onChange={e=>setTheme(e.target.value as Theme)}><option value="light">Светлая</option><option value="dark">Тёмная</option></select></label></Panel><Panel><h2>Локальные данные</h2><p>Учебный профиль: «Учебный оператор». Прогресс хранится в SQLite на этом компьютере. Тема хранится в браузере.</p><p>Порядок резервного копирования описан в README проекта. Клиенты и операции в демонстрационной базе вымышлены.</p></Panel></>
}
export default function App() {
  const [theme,setTheme]=useState<Theme>(()=>{let stored=null;try{stored=localStorage.getItem('academy-theme')}catch{}return initialTheme(stored,matchMedia('(prefers-color-scheme: dark)').matches)})
  useEffect(()=>{document.documentElement.dataset.theme=theme;try{localStorage.setItem('academy-theme',theme)}catch{}},[theme])
  return <div className="shell">
    <a className="skip" href="#main">К содержанию</a>
    <aside className="sidebar">
      <Link className="brand" to="/">Bereke<span>Operator Academy</span></Link>
      <p className="eyebrow">Учебная платформа</p>
      <nav aria-label="Главная навигация">
        <NavLink to="/" end>Обзор</NavLink>
        <NavLink to="/lessons">Обучение</NavLink>
        <NavLink to="/crm">CRM Simulator</NavLink>
        <NavLink to="/terms">Словарь</NavLink>
        <NavLink to="/facts">Проверка фактов</NavLink>
        <NavLink to="/settings">Настройки</NavLink>
      </nav>
      <div className="roadmap">
        <p className="eyebrow">Следующие этапы</p>
        <p>Тестирование</p><p>Roleplay</p>
      </div>
      <p className="sidebar-note">Локальный учебный симулятор<br />Вымышленные клиенты и операции</p>
    </aside>
    <div className="workspace">
      <header>
        <span>Учебный оператор</span>
        <button aria-label="Переключить тему" onClick={() => setTheme(theme === 'light' ? 'dark' : 'light')}>
          {theme === 'light' ? 'Тёмная тема' : 'Светлая тема'}
        </button>
      </header>
      <main id="main">
        <Routes>
          <Route path="/" element={<DashboardPage />} />
          <Route path="/lessons" element={<LessonsPage />} />
          <Route path="/lessons/:id" element={<LessonPage />} />
          <Route path="/crm" element={<CrmCustomersPage />} />
          <Route path="/crm/customers/:id" element={<CrmCustomerPage />} />
          <Route path="/crm/tickets" element={<CrmQueuePage />} />
          <Route path="/terms" element={<TermsPage />} />
          <Route path="/facts" element={<FactsPage />} />
          <Route path="/settings" element={<SettingsPage theme={theme} setTheme={setTheme} />} />
          <Route path="*" element={<><h1>Страница не найдена</h1><Link to="/">Вернуться к обзору</Link></>} />
        </Routes>
      </main>
    </div>
  </div>
}
