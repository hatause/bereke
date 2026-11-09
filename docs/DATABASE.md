# Схема базы данных

25 таблиц приложения и alembic_version. Все PK — целочисленные surrogate id. Внешние ключи SQLite включены на каждом соединении. По умолчанию связанные записи защищены от удаления. Для будущих удалений пользователя сначала определить политику архивации.

## Расширение CRM

Миграция `a43bdc721e02` добавляет необязательные учебные бонусы `customers.loyalty_points`, версию `support_tickets.version` с начальным значением 0 и таблицу `ticket_events`. Для стартовых тикетов миграция создаёт запись `fixture` с имеющимся статусом и пустой датой.

| Поля ticket_events | Назначение |
|---|---|
| id, ticket_id, operator_id | PK и FK на support_tickets и users |
| kind, previous_status, status | Стартовая запись, создание или переход статуса |
| ticket_version | Порядок событий. Уникален в пределах тикета |
| request_id | UUID команды. Уникален для оператора и может отсутствовать у стартовой записи |
| occurred_at | UTC, NULL у стартовой записи |

Сервер проверяет повтор команды, версию и допустимость перехода внутри одной транзакции записи SQLite. `BEGIN IMMEDIATE` сериализует обработку команд на разных соединениях. [SQLite Transaction Control](https://www.sqlite.org/lang_transaction.html).

## Отношения

- Users 1:N LearningProgress N:1 LessonSections N:1 Lessons. Статус урока и общий процент вычисляются из отметок разделов.
- SourceDocuments 1:N VerifiedFacts. LessonSections и BankingTerms ссылаются на факты; FactConflicts ссылается на одну или две версии факта.
- Lessons 1:N Questions N:1 VerifiedFacts; Questions 1:N QuestionOptions.
- Users 1:N ExamAttempts 1:N AttemptQuestions N:1 Questions. AttemptQuestion хранит неизменяемый JSON-снимок вопроса/ключа/рубрики/источника; ExamAnswers ссылается на конкретный вопрос попытки (не на произвольную пару attempt/question).
- Users 1:N TermProgress N:1 BankingTerms. Освоение словаря независимо от экзаменов.
- Customers 1:N Accounts 1:N Cards и Transactions. Deposit/Loan относятся к одному Account, владелец определяется через счёт. Один вклад/заём на отдельный учебный счёт.
- Customers 1:N SupportTickets N:1 Users; Customers 1:N RoleplayScenarios 1:N RoleplaySessions N:1 Users. Сценарий связан с фактом, если содержит проверяемое банковское правило; черновик может не иметь fact_id.
- ImportRecords хранит SHA256 применённого seed и неполную историю добровольного упражнения из чата. Эта история не создаёт ExamAnswers.

## Инварианты

День 1–4 уникален. Позиция раздела положительна и уникальна внутри урока. Отметка уникальна по user_id + section_id. PUT выполняет UPSERT одной строки; дата updated_at — UTC. Даты банковских правил хранятся отдельной строкой, поскольку источник иногда содержит только «с 1 августа» без года. NULL означает отсутствие даты, а не текущую дату.

Суммы учебных счетов/движений/займов/вкладов — целые minor units (для KZT тиыны), не float. Ставки в демо-продуктах не придуманы и отсутствуют в seed. При добавлении расчётов использовать Decimal/базисные пункты и отдельный тип валюты. Все клиенты fictional=1, идентификаторы начинаются DEMO-. Полей для реальных ИИН, PIN, CVV, кодовых слов, PAN, IBAN нет.

Статусы VerifiedFacts ограничены verified/disputed/historical/unverified. Открытая запись FactConflicts сохраняет вопрос и версии; resolved требует resolution. В этапе 1 API записи решений нет. Для полноценного workflow следующего этапа добавить ревьюера, дату решения и историю изменений, прежде чем разрешать редактирование.

Question.fact_id обязателен даже у черновика. Для open/case rubric обязателен. Триггер второй миграции запрещает published без подтверждённого факта, непустого locator/имени источника, пояснения и непустого ключа. При переводе факта в неподтверждённый статус связанные опубликованные вопросы уходят в retired. Триггер — защита происхождения; он не заменяет проверку содержательной правильности ключа и согласованности вариантов, которая будет частью экзаменационного сервиса.

AttemptQuestions уникальны по (attempt_id, position) и (attempt_id, question_id); ExamAnswer единственный на AttemptQuestion. Оценка ответа — nullable integer 0..10000 (basis points), NULL = ещё не проверен. Рубрика и её разбор хранятся в JSON, структурно валидировать их будет Pydantic-схема экзаменационного модуля. Пока экзаменационные API не реализованы, таблицы пусты.

## Миграции и seed

- 1ac65be8494f: явный снимок всех таблиц, ключей, индексов и ограничений.
- 2e28b5ac0a11: проверка источника опубликованного вопроса и отзыв ключей.
- app.seed: 4 урока, 22 раздела, 108 записей реестра фактов (включая словарь и спорные версии), 64 термина, 15 вопросов тренеру, 6 вымышленных клиентов/счетов/карт/движений/тикетов, 1 вклад, 1 заём, 1 пользователь, 2 записи импорта.

Seed выполняется в одной транзакции. Повтор с тем же хешем — no-op; другой хеш — явная ошибка, без перезаписи прогресса. Приватный reviewed_content.json содержит выбранные обезличенные формулировки, никогда не полные тексты скриншотов. Оригиналы в runtime не открываются.

Проверены upgrade, downgrade на временной БД, повторный upgrade, alembic check и PRAGMA foreign_key_check. Миграции используют SQLite-триггеры; для PostgreSQL нужна отдельная реализация защиты публикации.

## Физический справочник

Сгенерировано из SQLAlchemy metadata этапа 1. Nullable отмечено явно; индекс по FK задаётся там, где ожидаются выборки списков. Unique создаёт уникальный индекс SQLite. JSON используется только для снимков, рубрик, транскрипта и импорта; основные связи реляционные.

### customers

| Поле | Тип | NULL | Связь |
|---|---|---|---|
| demo_code | VARCHAR(50) | нет |  |
| display_name | VARCHAR(100) | нет |  |
| fictional | BOOLEAN | нет |  |
| id | INTEGER | нет | PK |

Check: `demo_code LIKE 'DEMO-%'`.

Unique: demo_code.

Check: `fictional = 1`.

### import_records

| Поле | Тип | NULL | Связь |
|---|---|---|---|
| key | VARCHAR(100) | нет |  |
| payload | JSON | нет |  |
| imported_at | DATETIME | нет |  |
| id | INTEGER | нет | PK |

Unique: key.

### lessons

| Поле | Тип | NULL | Связь |
|---|---|---|---|
| day | INTEGER | нет |  |
| title | VARCHAR(200) | нет |  |
| id | INTEGER | нет | PK |

Check: `day BETWEEN 1 AND 4`.

Unique: day.

### source_documents

| Поле | Тип | NULL | Связь |
|---|---|---|---|
| filename | VARCHAR(250) | нет |  |
| sha256 | VARCHAR(64) | нет |  |
| kind | VARCHAR(10) | нет |  |
| page_count | INTEGER | да |  |
| reviewed_at | VARCHAR(10) | нет |  |
| id | INTEGER | нет | PK |

Unique: filename.

### users

| Поле | Тип | NULL | Связь |
|---|---|---|---|
| display_name | VARCHAR(100) | нет |  |
| demo_key | VARCHAR(40) | нет |  |
| id | INTEGER | нет | PK |

Unique: demo_key.

### accounts

| Поле | Тип | NULL | Связь |
|---|---|---|---|
| customer_id | INTEGER | нет | customers.id |
| demo_code | VARCHAR(50) | нет |  |
| currency | VARCHAR(3) | нет |  |
| balance_minor | INTEGER | нет |  |
| id | INTEGER | нет | PK |

Unique: demo_code.

Check: `demo_code LIKE 'DEMO-%'`.

Check: `currency IN ('KZT','USD','EUR')`.

Индексы: (customer_id).

### exam_attempts

| Поле | Тип | NULL | Связь |
|---|---|---|---|
| user_id | INTEGER | нет | users.id |
| lesson_id | INTEGER | да | lessons.id |
| status | VARCHAR(20) | нет |  |
| current_position | INTEGER | нет |  |
| started_at | DATETIME | нет |  |
| finished_at | DATETIME | да |  |
| id | INTEGER | нет | PK |

Check: `status IN ('in_progress','submitted','reviewed','abandoned')`.

Check: `current_position >= 0`.

Индексы: (status), (user_id).

### support_tickets

| Поле | Тип | NULL | Связь |
|---|---|---|---|
| customer_id | INTEGER | нет | customers.id |
| operator_id | INTEGER | нет | users.id |
| subject | VARCHAR(200) | нет |  |
| status | VARCHAR(20) | нет |  |
| id | INTEGER | нет | PK |

Индексы: (customer_id), (operator_id), (status).

### verified_facts

| Поле | Тип | NULL | Связь |
|---|---|---|---|
| key | VARCHAR(80) | нет |  |
| topic | VARCHAR(150) | нет |  |
| statement | TEXT | нет |  |
| source_id | INTEGER | нет | source_documents.id |
| locator | VARCHAR(200) | нет |  |
| effective_date | VARCHAR(150) | да |  |
| status | VARCHAR(30) | нет |  |
| needs_trainer_confirmation | BOOLEAN | нет |  |
| id | INTEGER | нет | PK |

Unique: key.

Check: `status IN ('verified','disputed','historical','unverified')`.

Индексы: (source_id), (status).

### banking_terms

| Поле | Тип | NULL | Связь |
|---|---|---|---|
| term | VARCHAR(150) | нет |  |
| fact_id | INTEGER | нет | verified_facts.id |
| topic | VARCHAR(100) | нет |  |
| id | INTEGER | нет | PK |

Unique: term.

Unique: fact_id.

Индексы: (topic).

### cards

| Поле | Тип | NULL | Связь |
|---|---|---|---|
| account_id | INTEGER | нет | accounts.id |
| demo_code | VARCHAR(50) | нет |  |
| status | VARCHAR(30) | нет |  |
| id | INTEGER | нет | PK |

Check: `demo_code LIKE 'DEMO-%'`.

Unique: demo_code.

Индексы: (account_id).

### deposits

| Поле | Тип | NULL | Связь |
|---|---|---|---|
| account_id | INTEGER | нет | accounts.id |
| demo_product | VARCHAR(100) | нет |  |
| principal_minor | INTEGER | нет |  |
| id | INTEGER | нет | PK |

Unique: account_id.

Check: `principal_minor >= 0`.

### fact_conflicts

| Поле | Тип | NULL | Связь |
|---|---|---|---|
| title | VARCHAR(200) | нет |  |
| fact_a_id | INTEGER | нет | verified_facts.id |
| fact_b_id | INTEGER | да | verified_facts.id |
| question | TEXT | нет |  |
| status | VARCHAR(20) | нет |  |
| resolution | TEXT | да |  |
| id | INTEGER | нет | PK |

Check: `status IN ('open','resolved')`.

Check: `status != 'resolved' OR resolution IS NOT NULL`.

Индексы: (fact_a_id), (fact_b_id), (status).

### lesson_sections

| Поле | Тип | NULL | Связь |
|---|---|---|---|
| lesson_id | INTEGER | нет | lessons.id |
| position | INTEGER | нет |  |
| title | VARCHAR(200) | нет |  |
| fact_id | INTEGER | нет | verified_facts.id |
| id | INTEGER | нет | PK |

Unique: lesson_id, position.

Check: `position > 0`.

Индексы: (fact_id), (lesson_id).

### loans

| Поле | Тип | NULL | Связь |
|---|---|---|---|
| account_id | INTEGER | нет | accounts.id |
| demo_product | VARCHAR(100) | нет |  |
| outstanding_minor | INTEGER | нет |  |
| id | INTEGER | нет | PK |

Unique: account_id.

Check: `outstanding_minor >= 0`.

### questions

| Поле | Тип | NULL | Связь |
|---|---|---|---|
| lesson_id | INTEGER | нет | lessons.id |
| fact_id | INTEGER | нет | verified_facts.id |
| prompt | TEXT | нет |  |
| kind | VARCHAR(20) | нет |  |
| difficulty | VARCHAR(10) | нет |  |
| review_status | VARCHAR(20) | нет |  |
| correct_answer | JSON | нет |  |
| explanation | TEXT | нет |  |
| rubric | JSON | да |  |
| version | INTEGER | нет |  |
| id | INTEGER | нет | PK |

Check: `kind IN ('single','multiple','boolean','open','case')`.

Check: `kind NOT IN ('open','case') OR rubric IS NOT NULL`.

Check: `review_status IN ('draft','published','retired')`.

Индексы: (fact_id), (lesson_id), (review_status).

### roleplay_scenarios

| Поле | Тип | NULL | Связь |
|---|---|---|---|
| title | VARCHAR(200) | нет |  |
| customer_id | INTEGER | нет | customers.id |
| fact_id | INTEGER | да | verified_facts.id |
| mood | VARCHAR(20) | нет |  |
| rubric | JSON | нет |  |
| review_status | VARCHAR(20) | нет |  |
| id | INTEGER | нет | PK |

### transactions

| Поле | Тип | NULL | Связь |
|---|---|---|---|
| account_id | INTEGER | нет | accounts.id |
| amount_minor | INTEGER | нет |  |
| status | VARCHAR(30) | нет |  |
| occurred_at | DATETIME | нет |  |
| id | INTEGER | нет | PK |

Индексы: (account_id), (occurred_at).

### attempt_questions

| Поле | Тип | NULL | Связь |
|---|---|---|---|
| attempt_id | INTEGER | нет | exam_attempts.id |
| question_id | INTEGER | нет | questions.id |
| position | INTEGER | нет |  |
| snapshot | JSON | нет |  |
| id | INTEGER | нет | PK |

Unique: attempt_id, position.

Unique: attempt_id, question_id.

Индексы: (attempt_id), (question_id).

### learning_progress

| Поле | Тип | NULL | Связь |
|---|---|---|---|
| user_id | INTEGER | нет | users.id |
| section_id | INTEGER | нет | lesson_sections.id |
| completed | BOOLEAN | нет |  |
| updated_at | DATETIME | нет |  |
| id | INTEGER | нет | PK |

Unique: user_id, section_id.

Индексы: (section_id), (user_id).

### question_options

| Поле | Тип | NULL | Связь |
|---|---|---|---|
| question_id | INTEGER | нет | questions.id |
| key | VARCHAR(10) | нет |  |
| text | TEXT | нет |  |
| id | INTEGER | нет | PK |

Unique: question_id, key.

Индексы: (question_id).

### roleplay_sessions

| Поле | Тип | NULL | Связь |
|---|---|---|---|
| user_id | INTEGER | нет | users.id |
| scenario_id | INTEGER | нет | roleplay_scenarios.id |
| transcript | JSON | нет |  |
| rubric_result | JSON | да |  |
| status | VARCHAR(20) | нет |  |
| id | INTEGER | нет | PK |

Индексы: (scenario_id), (user_id).

### term_progress

| Поле | Тип | NULL | Связь |
|---|---|---|---|
| user_id | INTEGER | нет | users.id |
| term_id | INTEGER | нет | banking_terms.id |
| mastery | INTEGER | нет |  |
| next_review | DATETIME | да |  |
| id | INTEGER | нет | PK |

Check: `mastery BETWEEN 0 AND 3`.

Unique: user_id, term_id.

Индексы: (term_id), (user_id).

### exam_answers

| Поле | Тип | NULL | Связь |
|---|---|---|---|
| attempt_question_id | INTEGER | нет | attempt_questions.id |
| answer | JSON | нет |  |
| score_basis_points | INTEGER | да |  |
| grading_status | VARCHAR(20) | нет |  |
| rubric_result | JSON | да |  |
| updated_at | DATETIME | нет |  |
| id | INTEGER | нет | PK |

Unique: attempt_question_id.

Check: `score_basis_points BETWEEN 0 AND 10000`.
