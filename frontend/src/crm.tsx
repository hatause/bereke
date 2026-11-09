import { useEffect, useState, type FormEvent } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Link, useLocation, useParams, useSearchParams } from 'react-router-dom'
import { api, ApiError } from './api'
import { Panel, QueryState } from './components'
import './crm.css'

type TicketStatus = 'open' | 'in_progress' | 'resolved'
type Customer = { id: number; demo_code: string; display_name: string; fictional: true }
type TicketSummary = { id: number; customer_id: number; subject: string; status: TicketStatus }
type TicketEvent = {
  id: number
  kind: 'fixture' | 'created' | 'status_changed'
  previous_status: TicketStatus | null
  status: TicketStatus
  operator_name: string
  occurred_at: string | null
}
type Ticket = TicketSummary & { version: number; next_status: TicketStatus; events: TicketEvent[] }
type Account = {
  id: number
  demo_code: string
  currency: string
  balance_minor: number
  cards: { id: number; demo_code: string; status: string }[]
  transactions: { id: number; amount_minor: number; status: string; occurred_at: string }[]
  deposit: { demo_product: string; principal_minor: number } | null
  loan: { demo_product: string; outstanding_minor: number } | null
}
type CustomerDetail = Customer & {
  loyalty_points: number | null
  accounts: Account[]
  tickets: Ticket[]
  ticket_topics: { code: string; label: string }[]
}
type QueueItem = TicketSummary & { customer: Customer }
type CreateCommand = { request_id: string; topic: string }
type StatusCommand = { request_id: string; version: number; status: TicketStatus }

const statusLabels: Record<TicketStatus, string> = {
  open: 'Открыт',
  in_progress: 'В работе',
  resolved: 'Решён',
}
const actionLabels: Record<TicketStatus, string> = {
  open: 'Открыть повторно',
  in_progress: 'Взять в работу',
  resolved: 'Отметить решённым',
}
const productStatuses: Record<string, string> = {
  demo_active: 'Активна',
  demo_completed: 'Выполнено',
}
const dateFormat = new Intl.DateTimeFormat('ru-KZ', {
  dateStyle: 'medium', timeStyle: 'short', timeZone: 'Asia/Qyzylorda',
})

function amount(value: number, currency: string) {
  return new Intl.NumberFormat('ru-KZ', { style: 'currency', currency }).format(value / 100)
}

function ticketWrite(path: string, method: 'POST' | 'PUT', command: CreateCommand | StatusCommand) {
  return api<Ticket>(path, {
    method,
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(command),
  })
}

function CrmNav() {
  return <nav className="crm-nav" aria-label="Навигация CRM">
    <Link to="/crm">Клиенты</Link>
    <Link to="/crm/tickets">Очередь тикетов</Link>
  </nav>
}

export function CrmCustomersPage() {
  const [params, setParams] = useSearchParams()
  const search = (params.get('q') ?? '').slice(0, 100)
  const customers = useQuery({
    queryKey: ['crm', 'customers', search],
    queryFn: ({ signal }) => api<Customer[]>(`/crm/customers?${new URLSearchParams({ q: search })}`, { signal }),
  })
  return <div className="crm">
    <p className="eyebrow">Вымышленные данные</p>
    <h1>CRM Simulator</h1>
    <CrmNav />
    <Panel>
      <h2>Учебные клиенты</h2>
      <label className="search">Поиск по имени или учебному ID
        <input value={search} maxLength={100} placeholder="Например, DEMO-CUSTOMER-002"
          onChange={event => setParams(event.target.value ? { q: event.target.value } : {}, { replace: true })} />
      </label>
      <QueryState pending={customers.isPending} error={customers.error} retry={() => void customers.refetch()} />
      {customers.data?.length === 0 && <p>Клиенты не найдены. Проверьте имя или учебный ID.</p>}
      {!!customers.data?.length && <div className="crm-table-wrap">
        <table className="crm-table">
          <caption className="sr-only">Список вымышленных клиентов</caption>
          <thead><tr><th scope="col">Клиент</th><th scope="col">Учебный ID</th></tr></thead>
          <tbody>{customers.data.map(customer => <tr key={customer.id}>
            <td><Link to={`/crm/customers/${customer.id}`}>{customer.display_name}</Link></td>
            <td><code>{customer.demo_code}</code></td>
          </tr>)}</tbody>
        </table>
      </div>}
    </Panel>
  </div>
}

export function CrmQueuePage() {
  const [status, setStatus] = useState('')
  const tickets = useQuery({
    queryKey: ['crm', 'tickets', status],
    queryFn: ({ signal }) => api<QueueItem[]>(`/crm/tickets${status ? `?status=${status}` : ''}`, { signal }),
  })
  return <div className="crm">
    <p className="eyebrow">Вымышленные данные</p>
    <h1>Очередь тикетов</h1>
    <CrmNav />
    <Panel>
      <label className="crm-field">Статус тикета
        <select value={status} onChange={event => setStatus(event.target.value)}>
          <option value="">Все статусы</option>
          {Object.entries(statusLabels).map(([value, label]) => <option key={value} value={value}>{label}</option>)}
        </select>
      </label>
      <QueryState pending={tickets.isPending} error={tickets.error} retry={() => void tickets.refetch()} />
      {tickets.data?.length === 0 && <p>Тикетов с таким статусом пока нет.</p>}
      {!!tickets.data?.length && <div className="crm-table-wrap">
        <table className="crm-table">
          <caption className="sr-only">Учебные тикеты</caption>
          <thead><tr><th scope="col">Тикет</th><th scope="col">Клиент</th><th scope="col">Статус</th></tr></thead>
          <tbody>{tickets.data.map(ticket => <tr key={ticket.id}>
            <td><Link to={`/crm/customers/${ticket.customer_id}#ticket-${ticket.id}`}>#{ticket.id} · {ticket.subject}</Link></td>
            <td>{ticket.customer.display_name}</td>
            <td><TicketBadge status={ticket.status} /></td>
          </tr>)}</tbody>
        </table>
      </div>}
    </Panel>
  </div>
}

function TicketBadge({ status }: { status: TicketStatus }) {
  return <span className={`crm-badge crm-badge-${status}`}>{statusLabels[status]}</span>
}

function AccountPanel({ account }: { account: Account }) {
  const money = (value: number) => amount(value, account.currency)
  return <Panel>
    <h3>Счёт <code>{account.demo_code}</code></h3>
    <p>Учебный остаток · <strong>{money(account.balance_minor)}</strong></p>
    <dl className="crm-products">
      <div><dt>Карты</dt><dd>{account.cards.length ? account.cards.map(card =>
        <p key={card.id}><code>{card.demo_code}</code> · {productStatuses[card.status] ?? 'Статус не задан'}</p>,
      ) : 'Нет учебных карт'}</dd></div>
      <div><dt>Депозит</dt><dd>{account.deposit
        ? <>{account.deposit.demo_product}<br />Сумма · {money(account.deposit.principal_minor)}</>
        : 'Нет учебного депозита'}</dd></div>
      <div><dt>Кредит</dt><dd>{account.loan
        ? <>{account.loan.demo_product}<br />Остаток · {money(account.loan.outstanding_minor)}</>
        : 'Нет учебного кредита'}</dd></div>
    </dl>
    <h4>Движения по счёту</h4>
    {account.transactions.length === 0 ? <p>Нет учебных движений.</p> : <div className="crm-table-wrap">
      <table className="crm-table">
        <thead><tr><th scope="col">Дата</th><th scope="col">Учебная сумма</th><th scope="col">Статус</th></tr></thead>
        <tbody>{account.transactions.map(transaction => <tr key={transaction.id}>
          <td>{dateFormat.format(new Date(transaction.occurred_at))}</td>
          <td>{money(transaction.amount_minor)}</td>
          <td>{productStatuses[transaction.status] ?? 'Статус не задан'}</td>
        </tr>)}</tbody>
      </table>
    </div>}
  </Panel>
}

function useTicketCache(customerId: number) {
  const cache = useQueryClient()
  const key = ['crm', 'customer', customerId]
  return {
    saved: async (ticket: Ticket) => {
      await cache.cancelQueries({ queryKey: key, exact: true })
      cache.setQueryData<CustomerDetail>(key, customer => {
        const current = customer?.tickets.find(item => item.id === ticket.id)
        if (!customer || (current && current.version > ticket.version)) return customer
        return {
          ...customer,
          tickets: [ticket, ...customer.tickets.filter(item => item.id !== ticket.id)].sort((a, b) => b.id - a.id),
        }
      })
      void cache.invalidateQueries({ queryKey: key, exact: true })
      void cache.invalidateQueries({ queryKey: ['crm', 'tickets'] })
    },
    failed: (error: Error) => {
      if (error instanceof ApiError && error.status === 409) {
        void cache.invalidateQueries({ queryKey: key })
        void cache.invalidateQueries({ queryKey: ['crm', 'tickets'] })
      }
    },
  }
}

function readPendingTicket(key: string): CreateCommand | null {
  try {
    const command = JSON.parse(sessionStorage.getItem(key) ?? 'null')
    if (typeof command?.request_id === 'string' && typeof command?.topic === 'string') return command
  } catch {
    // A blocked or malformed storage entry should not prevent ticket creation.
  }
  return null
}

function NewTicket({ customer }: { customer: CustomerDetail }) {
  const storageKey = `academy-crm-pending-ticket-${customer.id}`
  const [pending, setPending] = useState(() => readPendingTicket(storageKey))
  const [topic, setTopic] = useState(pending?.topic ?? '')
  const [createdId, setCreatedId] = useState<number>()
  const ticketCache = useTicketCache(customer.id)
  function remember(command: CreateCommand | null) {
    setPending(command)
    try {
      if (command) sessionStorage.setItem(storageKey, JSON.stringify(command))
      else sessionStorage.removeItem(storageKey)
    } catch {
      // The current form can still retry when storage is blocked.
    }
  }
  const mutation = useMutation({
    mutationFn: (command: CreateCommand) => ticketWrite(`/crm/customers/${customer.id}/tickets`, 'POST', command),
    onSuccess: async ticket => {
      remember(null)
      setCreatedId(ticket.id)
      setTopic('')
      await ticketCache.saved(ticket)
    },
    onError: error => {
      if (error instanceof ApiError && error.status >= 400 && error.status < 500) remember(null)
      ticketCache.failed(error)
    },
  })
  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (!topic || mutation.isPending) return
    setCreatedId(undefined)
    const command = pending ?? { topic, request_id: crypto.randomUUID() }
    remember(command)
    mutation.mutate(command)
  }
  return <Panel>
    <h3>Новый тикет</h3>
    <form className="crm-form" onSubmit={submit}>
      <label>Тема обращения
        <select required value={topic} disabled={pending !== null || mutation.isPending}
          onChange={event => { setTopic(event.target.value); mutation.reset() }}>
          <option value="">Выберите тему</option>
          {customer.ticket_topics.map(item => <option key={item.code} value={item.code}>{item.label}</option>)}
        </select>
      </label>
      <button type="submit" disabled={!topic || mutation.isPending}>
        {mutation.isPending ? 'Сохраняем…' : pending ? 'Повторить создание' : 'Создать тикет'}
      </button>
    </form>
    {pending && !mutation.isPending && <p>Ответ на предыдущий запрос не получен. Повторите создание, чтобы получить результат.</p>}
    {createdId !== undefined && <p role="status">Тикет #{createdId} создан.</p>}
    {mutation.error && <p role="alert">{mutation.error.message}</p>}
  </Panel>
}

function TicketCard({ ticket, selected }: { ticket: Ticket; selected: boolean }) {
  const ticketCache = useTicketCache(ticket.customer_id)
  const mutation = useMutation({
    mutationFn: (command: StatusCommand) => ticketWrite(`/crm/tickets/${ticket.id}/status`, 'PUT', command),
    onSuccess: ticketCache.saved,
    onError: ticketCache.failed,
  })
  function advance() {
    if (mutation.isPending) return
    const previous = mutation.isError ? mutation.variables : undefined
    const command = previous?.version === ticket.version
      ? previous
      : { status: ticket.next_status, version: ticket.version, request_id: crypto.randomUUID() }
    mutation.mutate(command)
  }
  return <article id={`ticket-${ticket.id}`} className="crm-ticket panel">
    <div className="crm-ticket-heading"><h3>#{ticket.id} · {ticket.subject}</h3><TicketBadge status={ticket.status} /></div>
    <button onClick={advance} disabled={mutation.isPending}>{actionLabels[ticket.next_status]}</button>
    {mutation.error && <p role="alert">{mutation.error.message}</p>}
    <details open={selected || undefined}>
      <summary>Журнал действий ({ticket.events.length})</summary>
      <ol className="crm-journal">{ticket.events.map(event => <li key={event.id}>
        <strong>{event.kind === 'fixture' ? 'Стартовый учебный тикет' : event.kind === 'created'
          ? 'Тикет создан' : `${statusLabels[event.previous_status!]} → ${statusLabels[event.status]}`}</strong>
        <span>{event.operator_name} · {event.occurred_at ? dateFormat.format(new Date(event.occurred_at)) : 'Без даты'}</span>
      </li>)}</ol>
    </details>
  </article>
}

export function CrmCustomerPage() {
  const { id } = useParams()
  const customerId = Number(id)
  const validId = /^\d+$/.test(id ?? '') && Number.isSafeInteger(customerId) && customerId > 0
  const { hash } = useLocation()
  const customerQuery = useQuery({
    queryKey: ['crm', 'customer', customerId],
    queryFn: ({ signal }) => api<CustomerDetail>(`/crm/customers/${customerId}`, { signal }),
    enabled: validId,
  })
  const customer = customerQuery.data
  useEffect(() => {
    if (validId && customer && hash) document.getElementById(hash.slice(1))?.scrollIntoView()
  }, [validId, customer?.id, hash])

  return <div className="crm">
    <CrmNav />
    {!validId && <h1>Учебный клиент не найден</h1>}
    {validId && <QueryState pending={customerQuery.isPending} error={customerQuery.error} retry={() => void customerQuery.refetch()} />}
    {validId && customer && <>
      <p className="eyebrow">Вымышленные данные</p>
      <h1>{customer.display_name}</h1>
      <p className="lede">Учебный ID · <code>{customer.demo_code}</code></p>
      <h2>Продукты и операции</h2>
      {customer.accounts.length === 0 && <p>Нет учебных счетов.</p>}
      {customer.accounts.map(account => <AccountPanel key={account.id} account={account} />)}
      <Panel>
        <h3>Лояльность</h3>
        <p>{customer.loyalty_points === null ? 'Нет учебных данных о бонусах.'
          : `Учебный баланс · ${customer.loyalty_points.toLocaleString('ru-KZ')} баллов`}</p>
      </Panel>
      <h2>Обращения клиента</h2>
      <NewTicket key={customer.id} customer={customer} />
      {customer.tickets.length === 0 && <p>Тикетов пока нет.</p>}
      {customer.tickets.map(ticket => <TicketCard key={ticket.id} ticket={ticket} selected={hash === `#ticket-${ticket.id}`} />)}
    </>}
  </div>
}
