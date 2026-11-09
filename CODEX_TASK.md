# Project brief: Bereke Operator Academy (учебная CRM)

## Objective
Create a complete local educational web application that looks and behaves like an operator's bank CRM workspace, **not a copy of the real bank system**. It is for one student preparing for a test on 13 November 2026. Product information is for learning and may be historical, not for serving actual bank customers.

## Core screens and workflows

1. **Dashboard**. Training progress by day, completion percentages, attempts and scores, weak topics; sample KPI cards (FCR, AHT, CSI, %Quality, Happy Clients), clearly labeled simulated.
2. **Learning / courses**. Four distinct days with short, digestible lectures (3–7 sections per day), key facts, term definitions, step-by-step algorithms and source provenance. Provide 'Кратко', 'Проще' and 'Повторение'. Questions and lecture content should be separately editable in JSON or an admin view.
3. **Exam center**. Exactly 15 validated questions per day, mixed single choice, multiple choice, true/false, open-ended where validated and case studies. Render one question at a time, save answers and show contextual feedback. Every 5 questions summarize scores. Provide one final mixed exam (40 questions, 10 per day), timed mode optional, weak-topic recommendations and retry wrong answers. Open answers graded against clear rubric, never by invented rules.
4. **Terms**. Searchable Excel-driven bank glossary, filter by topic, flashcards, and 14 terms per day where available. Do not silently alter original definitions. Track term mastery separately from exams.
5. **Demo CRM**. Synthetic client lookup (fictional client IDs), client cards, account balances, mock payment cards, deposits, loans, support tickets, transaction status. Implement read-only virtual widgets for training flows (identity verification demonstration, card activation, error troubleshooting, loyalty/balance lookup). All operations act on synthetic data only.
6. **Call center trainer**. One-message-at-a-time roleplay. Client moods: calm, in a hurry, upset, confused. Scenarios: failed card payment, app login error, card issuance and delivery, transfer delay, uncredited bonus, deposit questions, loan payment and overdue balance. Operator selects or types response. Grade on greeting, understanding request, appropriate identification, source-grounded accuracy, empathy, compliant closure. Do not invent internal verification rules.
7. **Teacher / content review**. A page showing unresolved source conflicts, content marked 'not in lectures', and questions waiting for verification.

## Materials already provided
- Day 1 Welcome Day: operator role, 3 values, customer expectations, conversation stages, communication standards, KPI glossary, bank timeline, benefits.
- Day 2 Mobile app & ALL IN: login/onboarding, troubleshooting, ALL IN card types, 18+ threshold, 4-card limit, issuance, delivery, documents and restrictions.
- Day 3 Deposits / transfers: types of deposits, nominal/effective/fixed/floating rates, internal / domestic / international transfers, SWIFT and other transfer channels.
- Day 4 Loans: borrower/co-borrower/guarantor, credit products, repayment, rates, delinquency, collections, limits and channels.
- Supplemental source files: Loyalty and Solar, Contact center KPIs, Peon/BisPC-New, Excel banking glossary.

## Verified source-backed examples
- Day 1: values 'Клиент в сердце', 'Я создаю будущее', 'Вместе сильнее'; FCR=first-contact resolution; AHT=average handle time; %Quality=call quality evaluation; 3 stages: greeting, managing dialogue, closing.
- Day 2: ALL IN plastic / digital, currencies KZT/USD/EUR (not multicurrency); digital Mastercard only; up to 4 cards; 18+; in the presentation plastic ~10 min at branch and digital ~2 min in app; free courier delivery available in Almaty/Astana/Shymkent.
- Day 3: deposits savings/non-savings/fixed-term; SWIFT 1–3 business days; app SWIFT fee 0.3%, minimum 4,000 KZT, maximum 60,000 KZT, for Mass/Premier/VIP as of source material.
- Day 4: basic loan types and repayment terms, minimum applicant age 21, minimum work experience 4 months, loan repayment through app/ATM/cash desk/interbank transfer/Kazpost. Review contradictions before using any upper-age or past-due-day thresholds.

## Important ambiguities requiring trainer verification
- Day 4: women's maximum lending age is displayed as 61 in one slide and 60 in subsequent slides.
- Day 4: soft collection delinquency range differs between slides ('<90 days' and '30–90 days').
- Day 4: spouse consent for 3.5 million KZT uses inconsistent threshold language ('from' vs 'above').
- Day 3: early termination of a term deposit mentions 'ставка 1/2' with undefined meaning.
- Loyalty: automatic enrollment / per-card activation should be resolved by source date, product and scope before presenting as universal.
- Exact exam questions from the trainer were not provided. Generate realistic practice questions, never claim these are official or guaranteed exam questions.

## Data model
Users (demo only), CourseDays, Lessons, Terms, SourceDocuments, QuestionBank, Answers, ExamAttempts, StudyProgress, DemoClients, DemoAccounts, DemoCards, DemoTransactions, DemoLoans, DemoDeposits, DemoLoyalty, MockTickets, RoleplaySessions, TrainerReviewFlags.
Store source reference and last-verified source date on bank policy/terms/questions. All amounts/statuses in client demo should be explicitly marked 'вымышленные данные'.

## Expected files and checks
- Deliver a fully running app, not a design mockup alone.
- Seed four days from `data/lessons_seed.json` but extract richer factual content from the attached source files, including slide images when text parsing fails.
- Load glossary from `data/terms_from_excel.json` (pre-extracted from the user's original Excel workbook).
- At least 15 source-backed practice questions for each day; avoid unsupported values. If 15 distinct grounded questions cannot be produced for a day, mark remaining as pending review instead of inventing answers.
- 6 or more synthetic client scenarios spanning cards, deposits, loans, transfers and loyalty.
- Fully working navigation, forms, search, attempt persistence and test summary.
- Unit tests and an end-to-end smoke test. Include a clear RUN.md / README startup guide.

## Implementation plan
1. Audit reference files, source citations and disputes; present a content inventory.
2. Scaffold and run the MVP with courses, glossary, exam engine, CRM demo and roleplay.
3. Load validated lesson and question data; add synthetic test fixtures.
4. Check source accuracy, usability and test suite; document what remains unanswered.
Proceed with implementation. Ask for user approval only if a required external service or destructive operation is needed.
